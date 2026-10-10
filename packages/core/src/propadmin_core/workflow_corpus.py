"""Ingest full historical cases, with immutable revisions and exact event provenance."""

import base64
import copy
import hashlib

from .embeddings import EmbeddingService
from .financial_parsers import prepare_source
from .graph import add_edge, create_in_state
from .ingestion import split_chunks
from .media import store_original
from .registry import default_types
from .store import identifier, now, publish
from .workflow_parser import PARSER_VERSION, parse_case

RUBRIC_VERSION = "workflow-next-step-v1"


def source_document(state, source, filename, embedder):
    identity = source["text"] + "\0" + source["sha256"]
    digest = hashlib.sha256(identity.encode()).hexdigest()
    document_id = f"source_file:{digest[:24]}"
    if document_id in state["documents"]:
        return document_id
    job_id = identifier("job")
    document = {
        "id": document_id, "filename": filename, "title": filename,
        "mime": source["mime"], "origin": "workflow_history", "text": source["text"],
        "sha256": digest, "raw_sha256": source["sha256"], "size": len(source["text"].encode()),
        "raw_size": source.get("raw_size"), "raw_content_base64": source.get("content_base64"),
        "gcs_uri": source.get("gcs_uri"), "multimodal": source.get("multimodal"),
        "parser": source.get("parser", PARSER_VERSION), "status": "completed",
        "created_at": now(), "received_at": now(), "extractor_version": PARSER_VERSION,
        "chunks": [], "mentions": [], "facts": [], "entities": [], "job_id": job_id,
    }
    state["documents"][document_id] = document
    embedder.upsert(state, document_id, "title", filename)
    previous = None
    for chunk in split_chunks(source["text"]):
        key = f"chunk:{digest[:24]}-{chunk['ordinal']}"
        state["chunks"][key] = {**chunk, "id": key, "document_id": document_id}
        document["chunks"].append(key)
        embedder.upsert(state, key, "text", chunk["text"])
        add_edge(state, document_id, key, "contains")
        if previous:
            add_edge(state, previous, key, "next")
        previous = key
    state["jobs"][job_id] = {
        "id": job_id, "document_id": document_id, "filename": filename,
        "status": "completed", "created_at": now(), "completed_at": now(),
        "entities": [], "chunks": len(document["chunks"]),
        "extraction_provider": "lossless-history-parser", "extractor_version": PARSER_VERSION,
        "embedding_provider": embedder.model,
    }
    return document_id


def evidence(state, document_id, start, end):
    document = state["documents"][document_id]
    chunk_id = next((key for key in document["chunks"]
                     if state["chunks"][key]["char_start"] <= start < state["chunks"][key]["char_end"]), None)
    return {"document_id": document_id, "chunk_id": chunk_id, "confidence": 1.0,
            "span": {"start": start, "end": end, "text": document["text"][start:end]}}


class WorkflowCorpus:
    def __init__(self, store):
        self.store, self.embedder = store, EmbeddingService()

    def ingest(self, dataset, case_ref, sources):
        prepared = []
        for source in sources:
            item = copy.deepcopy(source)
            raw = base64.b64decode(item["content_base64"], validate=True)
            if len(raw) > 5_000_000:
                raise ValueError("A source exceeds the 5 MB limit")
            digest = hashlib.sha256(raw).hexdigest()
            if item.get("sha256") != digest:
                raise ValueError("Source checksum mismatch")
            item.update(prepare_source({**item, "filename": item["path"]}))
            item["sha256"] = digest
            prepared.append(item)
        case = parse_case(dataset, case_ref, prepared)
        case_id = f"workflow_case:{dataset}-{case_ref}-{case['revision'][:12]}"
        if case_id in self.store.snapshot()["entities"]:
            return {"case_id": case_id, "deduplicated": True}
        # Original files are saved separately before the atomic graph mutation.
        case["sources"] = [store_original(source, self.store) for source in prepared]
        return self.store.mutate(lambda state: self._write(state, case_id, case))

    def _write(self, state, case_id, case):
        if case_id in state["entities"]:
            return {"case_id": case_id, "deduplicated": True}
        for key, spec in default_types().items():
            if key.startswith("workflow_"):
                state["entity_types"].setdefault(key, spec)
        reason = f"Import {case['dataset']} case {case['case_ref']} ({case['revision'][:12]})"
        documents = {
            source["path"]: source_document(
                state, source, f"{case['dataset']}/{case['case_ref']}/{source['path']}", self.embedder
            ) for source in case["sources"]
        }
        manifest = []
        for path, document_id in documents.items():
            if path in {"index.md", "history.md"}:
                continue
            first = next((e["ordinal"] for e in case["events"] if path in e["attachments"]), None)
            manifest.append({"path": path, "document_id": document_id, "available_after_step": first})
        fields = {key: case[key] for key in (
            "dataset", "case_ref", "revision", "split", "initial_context", "initial_request",
            "property_address", "source_role", "overview", "outcome", "skills",
        )}
        fields.update(source_paths=list(documents), source_documents=list(documents.values()),
                      attachment_manifest=manifest, event_count=len(case["events"]),
                      parser_version=PARSER_VERSION)
        create_in_state(state, {"id": case_id, "type": "workflow_case",
            "name": f"{case['dataset']} {case['case_ref']}: {case['name']}",
            "description": case["overview"], "fields": fields,
            "evidence": [evidence(state, documents["index.md"], 0,
                                  len(state["documents"][documents["index.md"]]["text"]))],
        }, "admin", reason, self.embedder)
        for document_id in documents.values():
            add_edge(state, case_id, document_id, "derived_from")
            state["documents"][document_id]["entities"].append(case_id)
        # Match properties by their actual address, never by the case number.
        address = case["property_address"]
        prop = next((e for e in state["entities"].values() if e["type"] == "property"
                     and e["fields"].get("address_text", "").casefold() == address.casefold()), None)
        if not prop:
            import re

            postcode = re.search(r"([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})$", address)
            if postcode:
                ref = "HIST-" + hashlib.sha256(address.casefold().encode()).hexdigest()[:12]
                prop = create_in_state(state, {"id": f"property:{ref.lower()}",
                    "type": "property", "name": address, "fields": {
                        "ref": ref, "address_line1": address, "address_text": address,
                        "postcode": postcode[1],
                    }}, "admin", reason, self.embedder)
        if prop:
            add_edge(state, case_id, prop["id"], "concerns")
        event_ids = []
        for event in case["events"]:
            event_id = f"workflow_event:{case_id.split(':', 1)[1]}-{event['ordinal']:03}"
            event_ids.append(event_id)
            source = documents["history.md"]
            create_in_state(state, {"id": event_id, "type": "workflow_event",
                "name": f"{case['case_ref']} step {event['ordinal']}: {event['channel']}",
                "description": event["body"],
                "fields": {**event, "case_id": case_id, "source_document": source,
                           "attachments": [documents[path] for path in event["attachments"]]},
                "evidence": [evidence(state, source, event["char_start"], event["char_end"])],
            }, "admin", reason, self.embedder)
            add_edge(state, case_id, event_id, "has_event")
            add_edge(state, event_id, source, "derived_from")
            for path in event["attachments"]:
                add_edge(state, event_id, documents[path], "has_attachment")
        for index, (before, after) in enumerate(zip(event_ids, event_ids[1:]), 1):
            target = case["events"][index]
            transition_id = f"workflow_transition:{case_id.split(':', 1)[1]}-{index:03}"
            evaluable = target["kind"] == "agent_action"
            create_in_state(state, {"id": transition_id, "type": "workflow_transition",
                "name": f"{case['case_ref']}: step {index} → {index + 1}", "fields": {
                    "case_id": case_id, "from_event": before, "to_event": after,
                    "after_step": index, "target_step": index + 1, "evaluable": evaluable,
                    "reason": "" if evaluable else "Next event is an external observation, supplied on replay",
                    "rubric_version": RUBRIC_VERSION,
                }}, "admin", reason, self.embedder)
            add_edge(state, before, after, "next_event")
            add_edge(state, case_id, transition_id, "has_transition")
            add_edge(state, transition_id, before, "from_step")
            add_edge(state, transition_id, after, "to_step")
        publish(state, "workflow_case.ingested", {"id": case_id, "events": len(event_ids)})
        return {"case_id": case_id, "revision": case["revision"], "split": case["split"],
                "events": len(event_ids), "transitions": max(0, len(event_ids) - 1),
                "documents": documents, "deduplicated": False}
