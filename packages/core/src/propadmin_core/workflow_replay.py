"""Prepare replay state without future events, end-of-case summaries or answer keys."""

import copy
import hashlib
import json
import re

from .embeddings import EmbeddingService
from .graph import add_edge, create_in_state
from .ingestion import split_chunks
from .store import initial_state
from .workflow_triplets import retrieve_examples


def prepare_replay(state, transition_id):
    transition = state["entities"][transition_id]
    if transition["type"] != "workflow_transition" or not transition["fields"]["evaluable"]:
        raise ValueError("Evaluate agent actions; external observations are replay inputs")
    case = state["entities"][transition["fields"]["case_id"]]
    cutoff = transition["fields"]["after_step"]
    events = sorted((e for e in state["entities"].values() if e["type"] == "workflow_event"
                     and e["fields"]["case_id"] == case["id"]
                     and e["fields"]["ordinal"] <= cutoff), key=lambda e: e["fields"]["ordinal"])
    sandbox = initial_state()
    embedder = EmbeddingService()
    sandbox["entity_types"] = copy.deepcopy(state["entity_types"])
    sandbox["skills"] = copy.deepcopy(state["skills"])
    skill_versions = {s["id"]: s["current_version"] for s in sandbox["skills"].values()}
    skill_ids = set(skill_versions)
    skill_ids |= {f"skill_version:{s['slug']}-v{s['current_version']}" for s in sandbox["skills"].values()}
    for key in skill_ids:
        if key in state["entities"]:
            entity = copy.deepcopy(state["entities"][key])
            entity["evidence"] = []
            sandbox["entities"][key] = entity
            embedder.entity(sandbox, entity)
    context = ("Historical prefix replay v2. ticket:replay-case is a synthetic evidence container, "
               "not a real case reference. Do not put its identifier in communications. "
               "Current ticket status is not reconstructed; use the ordered history to identify "
               "the workflow phase and next outstanding dependency.\n\n"
               + case["fields"]["initial_context"] + "\n\nHistory available now:\n")
    context += "\n\n".join(e["fields"]["raw_text"].strip() for e in events)
    for event in events:
        entity = copy.deepcopy(event)
        entity["evidence"] = []
        entity["fields"].update(case_id="replay", source_document="replay-history")
        sandbox["entities"][entity["id"]] = entity
        embedder.entity(sandbox, entity)
    # Attachments become visible at their first explicit reference, never from index.md.
    available = []
    for attachment in case["fields"]["attachment_manifest"]:
        step = attachment["available_after_step"]
        if step is None or step > cutoff:
            continue
        document = copy.deepcopy(state["documents"][attachment["document_id"]])
        # Supplied synthetic PDFs append Observations/Findings/Conclusions written
        # with hindsight. Keep the primary document in replay, retaining full originals
        # only in the main graph. Re-chunk to prevent overlap from leaking the appendix.
        if document.get("mime") == "application/pdf" and document.get("origin") == "workflow_history":
            document["text"] = re.split(
                r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*)?Observations(?:\*\*)?\s*:?\s*$",
                document["text"], maxsplit=1,
            )[0].strip()
        document.update(entities=[], mentions=[], facts=[], raw_content_base64=None,
                        gcs_uri=None, multimodal=None, chunks=[])
        sandbox["documents"][document["id"]] = document
        for chunk in split_chunks(document["text"]):
            key = f"chunk:replay-{document['id'].split(':', 1)[1]}-{chunk['ordinal']}"
            document["chunks"].append(key)
            sandbox["chunks"][key] = {**chunk, "id": key, "document_id": document["id"]}
            embedder.upsert(sandbox, key, "text", chunk["text"])
        available.append({"path": attachment["path"], "document_id": document["id"]})
        context += f"\n\nAvailable attachment {attachment['path']}:\n{document['text']}"
    ticket_id = "ticket:replay-case"
    ticket = create_in_state(sandbox, {"id": ticket_id, "type": "ticket",
        "name": case["name"], "description": case["fields"]["initial_request"],
        "fields": {"title": case["name"],
                   "location_detail": case["fields"]["property_address"],
                   "notes": [context]},
    }, "replay", "Historical prefix only", embedder)
    for event in events:
        add_edge(sandbox, ticket_id, event["id"], "has_event")
    initial_property = {key: case["fields"][key] for key in ("property_address", "source_role")}
    context += "\n\nAvailable attachments: " + json.dumps(available)
    if any(e["type"] == "workflow_triplet" for e in state["entities"].values()):
        query = "\n\n".join(e["fields"]["raw_text"] for e in events[-2:])
        examples = retrieve_examples(state, query, exclude_case_id=case["id"])
        context += "\n\nPrior training-case examples (historical patterns, not facts about this case):\n"
        context += json.dumps(examples, ensure_ascii=False)
        example_ids = {row["id"] for row in examples["items"]}
        for key in example_ids:
            entity = copy.deepcopy(state["entities"][key])
            entity["evidence"] = []
            sandbox["entities"][key] = entity
        for key, entry in state["embeddings"].items():
            if entry["owner"] in example_ids:
                sandbox["embeddings"][key] = copy.deepcopy(entry)
    context_hash = hashlib.sha256(json.dumps({
        "replay_version": "historical-prefix-v2", "context": context,
        "skill_versions": skill_versions, "ticket_fields": ticket["fields"],
    }, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"state": sandbox, "context": context, "context_hash": context_hash,
            "skill_versions": skill_versions, "initial_property": initial_property,
            "expected": state["entities"][transition["fields"]["to_event"]]["fields"]["raw_text"]}
