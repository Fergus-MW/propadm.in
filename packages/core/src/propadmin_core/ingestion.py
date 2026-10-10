"""Idempotent, provenance-preserving ingestion of text, EML, CRM and transcripts."""

import copy
import hashlib
import json
import os
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

from .embeddings import EmbeddingService
from .financial_ingestion import (
    candidate_evidence,
    claim_candidates,
    link_candidate_relations,
    resolve_financial,
    tenancy_candidates,
)
from .graph import add_edge, create_in_state, update_in_state
from .graph_relationships import ENDPOINTS
from .providers import ClaudeProvider
from .registry import hard_keys, primary_types, validate_fields
from .rules import recompute_enabled
from .store import ConflictError, identifier, now, publish


def split_chunks(text, max_chars=3200, overlap=400):
    """Prefer paragraph/turn boundaries; retain exact character positions."""
    result, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + max_chars // 2, end)
            if boundary != -1:
                end = boundary + 1
            else:
                boundary = text.rfind(" ", start + max_chars // 2, end)
                if boundary != -1:
                    end = boundary + 1
        result.append(
            {
                "ordinal": len(result),
                "text": text[start:end],
                "char_start": start,
                "char_end": end,
                "page": None,
                "token_count": len(text[start:end].split()),
                "chunker_version": "paragraph-offset-v1",
            }
        )
        if end == len(text):
            break
        next_start = max(start + 1, end - overlap)
        boundary = text.find("\n", next_start, end)
        start = boundary + 1 if boundary != -1 and boundary + 1 < end else next_start
    return result


def email_records(text):
    message = BytesParser(policy=policy.default).parsebytes(text.encode("utf-8"))
    addresses = getaddresses(
        message.get_all("From", []) + message.get_all("To", []) + message.get_all("Cc", [])
    )
    sender = getaddresses(message.get_all("From", []))
    body_part = message.get_body(preferencelist=("plain",)) if message.is_multipart() else message
    body = body_part.get_content() if body_part else ""
    if not isinstance(body, str):
        raise ValueError("Email body must decode to text")
    fields = {
        "message_id": message.get("Message-ID")
        or f"<sha256-{hashlib.sha256(text.encode()).hexdigest()}@local>",
        "subject": str(message.get("Subject", "Untitled email")),
        "from_address": sender[0][1] if sender else "",
        "from_name": sender[0][0] if sender else "",
        "to_addresses": [address for _, address in getaddresses(message.get_all("To", []))],
        "cc_addresses": [address for _, address in getaddresses(message.get_all("Cc", []))],
        "body_text": body,
        "body_full": body,
        "direction": "inbound",
        "status": "received",
        "channel": "synthetic_env",
        "references": str(message.get("References", "")).split(),
    }
    if message.get("In-Reply-To"):
        fields["in_reply_to"] = str(message["In-Reply-To"])
    if message.get("Date"):
        try:
            fields["sent_at"] = parsedate_to_datetime(message["Date"]).isoformat()
        except (ValueError, TypeError):
            pass
    records = [
        {"type": "email", "name": fields["subject"], "description": body[:500], "fields": fields}
    ]
    records.extend(
        {"type": "person", "name": name or address, "fields": {"emails": [address]}}
        for name, address in addresses
        if address
    )
    return records


def local_candidates(state, text, payload):
    """Offline recogniser: structured records and exact known identity mentions only."""
    records = copy.deepcopy(payload.get("records") or [])
    if payload.get("origin") == "generated_statement":
        return records
    records += tenancy_candidates(state, text, payload)
    if payload.get("mime") in ("message/rfc822", "application/eml") or payload.get(
        "filename", ""
    ).endswith(".eml"):
        records = email_records(text) + records
    if payload.get("mime") == "application/json" and not records:
        parsed = json.loads(text)
        records = parsed if isinstance(parsed, list) else parsed.get("records", [parsed])
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise ValueError("records must be an array of entity objects")
    for entity in state["entities"].values():
        if entity.get("merged_into"):
            continue
        if payload.get("origin") == "generated_statement" and entity["type"] == "transaction":
            # A report is derived from ledger evidence, not fresh evidence for that entry.
            continue
        terms = [entity["name"]] + entity["aliases"]
        terms += [value for _, value in hard_keys(state, entity)]
        for term in terms:
            if len(term) < 3:
                continue
            match = re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I)
            if match:
                records.append(
                    {
                        "id": entity["id"],
                        "type": entity["type"],
                        "name": entity["name"],
                        "fields": {},
                        "mentions": [
                            {
                                "start": match.start(),
                                "end": match.end(),
                                "text": match.group(),
                                "confidence": 1.0,
                            }
                        ],
                    }
                )
                break
    return records


def primary_registry(state):
    primary = primary_types(state)
    return {key: value for key, value in state["entity_types"].items() if key in primary}


def resolve(state, candidate, embedder, extractor):
    requested = state["entities"].get(candidate.get("id"))
    if requested and not candidate.get("fields"):
        if requested["type"] != candidate.get("type"):
            raise ValueError("Mention type differs from canonical entity")
        return state["entities"].get(requested.get("merged_into"), requested), "record_id"
    schema = state["entity_types"].get(candidate.get("type"), {}).get("fields", {})
    incoming = candidate.get("fields", {})
    if requested:
        incoming = {**{k: v for k, v in requested["fields"].items()
                        if not schema.get(k, {}).get("read_only")}, **incoming}
    fields = validate_fields(state, candidate.get("type", ""), incoming)
    candidate = {**candidate, "fields": fields}
    keys = hard_keys(state, candidate)
    entities = [
        item
        for item in state["entities"].values()
        if item["type"] == candidate["type"] and not item.get("merged_into")
    ]
    hard_matches = [item for item in entities if keys & hard_keys(state, item)]
    if len(hard_matches) > 1:
        raise ConflictError(
            "Candidate hard keys identify multiple canonical entities; merge is required"
        )
    method = "hard_key" if hard_matches else None
    existing = hard_matches[0] if hard_matches else None
    if candidate.get("id") and candidate["id"] in state["entities"]:
        requested = state["entities"][candidate["id"]]
        if requested.get("merged_into"):
            requested = state["entities"][requested["merged_into"]]
        if requested["type"] != candidate["type"] or (
            existing and existing["id"] != requested["id"]
        ):
            raise ConflictError("Candidate id conflicts with its typed identity keys")
        existing, method = requested, method or "record_id"
    if not existing and candidate.get("name"):
        name = re.sub(r"[^\w]", "", candidate["name"].casefold())
        named = [
            item
            for item in entities
            if name
            in [re.sub(r"[^\w]", "", term.casefold()) for term in [item["name"]] + item["aliases"]]
        ]
        # Distinct hard keys + a common name are insufficient to claim identity.
        named = [item for item in named if not keys or not hard_keys(state, item)]
        if len(named) == 1:
            existing, method = named[0], "exact_name"
    if not existing and extractor == "claude" and candidate.get("description"):
        from .embeddings import cosine

        vector = embedder.vector(candidate["description"])
        scored = []
        for entity in entities:
            entry = next(
                (
                    item
                    for item in state["embeddings"].values()
                    if item["owner"] == entity["id"] and item["field"] == "description"
                ),
                None,
            )
            if entry:
                score = cosine(vector, entry["vector"])
                if score >= 0.75:
                    scored.append((score, entity))
        if scored:
            adjudication = ClaudeProvider().json(
                "Resolve entity identity. Return {entity_id: string or null, reason: string}. "
                "Hard key conflicts mean different identities. Match only confident same real-world entity.",
                {
                    "candidate": candidate,
                    "candidates": [entity for _, entity in sorted(scored, key=lambda p: -p[0])[:5]],
                },
            )
            key = adjudication.get("entity_id")
            if key is not None:
                if key not in {entity["id"] for _, entity in scored}:
                    raise ValueError("Claude resolved to an entity outside the candidate set")
                existing, method = state["entities"][key], "embedding_claude_adjudication"
    if existing:
        updated_fields = copy.deepcopy(existing["fields"])
        for key, value in fields.items():
            if isinstance(value, list) and isinstance(updated_fields.get(key), list):
                updated_fields[key] = list(
                    {repr(v): v for v in updated_fields[key] + value}.values()
                )
            elif value not in (None, "", []):
                updated_fields[key] = value
        aliases = list(
            dict.fromkeys(
                existing["aliases"]
                + candidate.get("aliases", [])
                + ([candidate["name"]] if candidate["name"] != existing["name"] else [])
            )
        )
        changes = {
            "version": existing["version"],
            "fields": updated_fields,
            "aliases": aliases,
            "external_ids": {**existing["external_ids"], **candidate.get("external_ids", {})},
        }
        if candidate.get("description") and not existing.get("description_pinned"):
            changes["description"] = candidate["description"]
        if any(existing.get(key) != value for key, value in changes.items() if key != "version"):
            changes["fields"] = {k: v for k, v in changes["fields"].items()
                                 if not schema.get(k, {}).get("read_only")}
            entity = update_in_state(
                state, existing["id"], changes, "ingestion", "Source evidence update", embedder
            )
        else:
            entity = existing
    else:
        entity = create_in_state(
            state, candidate, "ingestion", "New canonical identity from source", embedder
        )
        method = "created"
    return entity, method


def mention_spans(candidate, text):
    mentions = candidate.get("mentions", [])
    if not mentions:
        terms = [candidate.get("name", "")]
        for value in candidate.get("fields", {}).values():
            terms.extend(value if isinstance(value, list) else [value])
        for term in terms:
            if not isinstance(term, str) or len(term) < 3:
                continue
            match = re.search(re.escape(term), text, re.I)
            if match:
                mentions = [
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(),
                        "confidence": 1.0,
                    }
                ]
                break
    if not mentions:
        # Structured source record is still source-backed; use its whole body span.
        mentions = [
            {
                "start": 0,
                "end": len(text),
                "text": text,
                "confidence": 1.0,
                "method": "structured_record",
            }
        ]
    result = []
    for mention in mentions:
        start, end = mention.get("start"), mention.get("end")
        confidence = mention.get("confidence", 1.0)
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("Mention span is outside source text")
        if mention.get("text", text[start:end]) != text[start:end]:
            raise ValueError("Mention span text does not match source text")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            raise ValueError("Mention confidence must be between zero and one")
        result.append({**mention, "text": text[start:end], "confidence": confidence})
    return result


def ground_claude_spans(extracted, text):
    """Compute offsets from exact quotes; never accept invented or ambiguous evidence."""
    warnings = []

    def ground(span):
        quote = span.get("text")
        if not isinstance(quote, str) or not quote:
            return False
        start, end = span.get("start"), span.get("end")
        if (type(start) is int and type(end) is int
                and 0 <= start < end <= len(text) and text[start:end] == quote):
            return True
        start = text.find(quote)
        if start < 0 or text.find(quote, start + 1) >= 0:
            return False
        span.update(start=start, end=start + len(quote))
        return True

    entities = []
    for index, entity in enumerate(extracted.get("entities") or []):
        mentions = [span for span in entity.get("mentions") or [] if ground(span)]
        if len(mentions) != len(entity.get("mentions") or []) or not mentions:
            warnings.append(f"Discarded unsupported entity evidence at index {index}")
        if mentions:
            entities.append({**entity, "mentions": mentions})
    names = {entity["name"] for entity in entities}
    facts = []
    for index, fact in enumerate(extracted.get("facts") or []):
        if ground(fact) and (not fact.get("entity_name") or fact["entity_name"] in names):
            facts.append(fact)
        else:
            warnings.append(f"Discarded unsupported fact evidence at index {index}")
    if extracted.get("entities") and not entities:
        raise ValueError("Claude evidence quotes are missing or ambiguous in source text")
    types = {entity["name"]: entity["type"] for entity in entities}
    relationships = []
    for index, relation in enumerate(extracted.get("relationships") or []):
        source, target = types.get(relation.get("source")), types.get(relation.get("target"))
        expected = ENDPOINTS.get(relation.get("relation"))
        allowed = relation.get("relation") in {
            "offers", "at", "about", "mentions", "contact", "registered_as",
            "tenant_of", "owns", "manages",
        }
        if (allowed and source and target and "transaction" not in {source, target}
                and (not expected or source in expected[0] and target in expected[1])):
            relationships.append(relation)
        else:
            warnings.append(f"Discarded unsupported relationship at index {index}")
    extracted.update(entities=entities, facts=facts, relationships=relationships, warnings=warnings)
    return extracted


class IngestionService:
    def __init__(self, store, *, extraction_provider=None):
        self.store = store
        self.embedder = EmbeddingService()
        self.extraction_provider = extraction_provider

    def ingest(self, payload):
        from .financial_parsers import prepare_source

        payload = prepare_source(payload)
        text = payload.get("text")
        if text is None and payload.get("records"):
            text = json.dumps(payload["records"], ensure_ascii=False, indent=2)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Nonempty parsed text or structured records are required")
        if len(text.encode()) > 5_000_000:
            raise ValueError("Parsed source exceeds the 5 MB ingestion limit")
        mime = payload.get("mime", "text/plain")
        if mime.startswith(("audio/", "image/")) or mime in (
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            if not payload.get("parsed", False):
                raise ValueError(
                    "Binary files require an external parser/transcriber; supply parsed text with parsed=true"
                )
        extractor = ("local" if payload.get("origin") == "generated_statement"
                     else self.extraction_provider or os.getenv("EXTRACTION_PROVIDER", "local"))
        if extractor not in ("local", "claude"):
            raise ValueError(f"Unknown extraction provider {extractor}")
        provider = ClaudeProvider() if extractor == "claude" else None
        version = payload.get("extractor_version") or (
            provider.model if provider else "local-structured-exact-v1"
        )
        digest = hashlib.sha256(text.encode()).hexdigest()
        document_id = f"source_file:{digest[:24]}"
        existing = self.store.snapshot()["documents"].get(document_id)
        if (
            existing
            and existing.get("extractor_version") == version
            and existing["status"] == "completed"
        ):
            previous = self.store.snapshot()["jobs"][existing["job_id"]]
            return {**previous, "deduplicated": True}
        job_id = identifier("job")
        job = {
            "id": job_id,
            "document_id": document_id,
            "filename": payload.get("filename", "upload.txt"),
            "status": "processing",
            "created_at": now(),
            "chunks": 0,
            "entities": [],
            "extraction_provider": "claude" if provider else "local-structured-exact",
            "embedding_provider": self.embedder.model,
            "extractor_version": version,
        }

        def start(state):
            state["jobs"][job_id] = job
            publish(state, "ingestion.started", {"id": job_id, "document_id": document_id})

        self.store.mutate(start)
        # Remote extraction happens outside the file lock; writes remain one transaction.
        extracted = None
        try:
            if provider:
                extracted = provider.json(
                    "Extract typed entities and facts. Return {entities:[{type,name,description,fields,mentions:"
                    "[{text,confidence}]}],facts:[{key,value,text,entity_name,confidence}]}. "
                    "Return source quotes only; the application computes character offsets. "
                    "Every mention and fact text MUST be a nonempty "
                    "verbatim substring of the source, never a paraphrase or an abbreviated quote with ellipses. "
                    "Omit unsupported facts. Use only registry fields; never invent facts. "
                    "Return optional relationships:[{source:entity name,relation,target:entity name,attributes:{}}]. "
                    "owns attributes include share_pct; tenant_of includes from,to,is_lead_tenant; contact includes role. "
                    "Property is one lettable unit; ticket has location_detail and an at property relationship. "
                    "Extract service_provider, service_offering and quote with provider_id/ticket_id references. "
                    "Extract financial transactions with property_id, paid_by, paid_to or ticket_id references; "
                    "money amounts are positive GBP pence; bank lines cleared confidence1, email/call claims "
                    "pending low confidence, invoices expense kind charge expected. Never invent bank details. "
                    "Offerings include price_source and last_confirmed_at; provenance must name the source.",
                    {
                        "text": text,
                        "filename": job["filename"],
                        "relationship_endpoints": {
                            key: {"source_types": sorted(value[0]), "target_types": sorted(value[1])}
                            for key, value in ENDPOINTS.items()
                        },
                        "registry": {
                            key: value for key, value in primary_registry(self.store.snapshot()).items()
                            if key not in {r.get("type") for r in payload.get("records") or []
                                           if r.get("type") in {"email", "call"}}
                        },
                    },
                )
                extracted = ground_claude_spans(extracted, text)
                job["extraction_warnings"] = extracted["warnings"]
            result = self.store.mutate(
                lambda state: self._write(state, payload, text, digest, job, extracted, extractor)
            )
            return result
        except Exception as error:
            error_message = str(error)

            def fail(state):
                state["jobs"][job_id].update(
                    status="failed", error=error_message, completed_at=now()
                )
                publish(state, "ingestion.failed", {"id": job_id, "error": error_message})

            self.store.mutate(fail)
            raise

    def _write(self, state, payload, text, digest, job, extracted, extractor):
        document_id, version = job["document_id"], job["extractor_version"]
        prior = state["documents"].get(document_id)
        if prior and prior.get("extractor_version") == version and prior["status"] == "completed":
            state["jobs"][job["id"]].update(
                status="completed",
                deduplicated=True,
                chunks=len(prior["chunks"]),
                entities=prior.get("entities", []),
            )
            return state["jobs"][job["id"]]
        if prior:
            old_chunks = set(prior["chunks"])
            old_owners = old_chunks | set(prior.get("facts", []))
            for edge_id, edge in list(state["edges"].items()):
                if any(state["entities"].get(key, {}).get("type") == "transaction"
                       for key in (edge["source"], edge["target"])):
                    continue
                if (
                    edge["source"] in old_owners
                    or edge["target"] in old_owners
                    or (edge["target"] == document_id and edge["relation"] == "derived_from")
                ):
                    del state["edges"][edge_id]
            for entity in state["entities"].values():
                if entity["type"] == "transaction":
                    continue
                entity["evidence"] = [
                    e for e in entity.get("evidence", []) if e.get("document_id") != document_id
                ]
            for key in prior.get("facts", []):
                state["facts"].pop(key, None)
            owners = old_chunks | set(prior.get("facts", []))
            for key in [
                key
                for key, embedding in state["embeddings"].items()
                if embedding["owner"] in owners
            ]:
                del state["embeddings"][key]
            for key in old_chunks:
                state["chunks"].pop(key, None)
        chunks = split_chunks(text)
        document = {
            "id": document_id,
            "filename": job["filename"],
            "title": payload.get("title", job["filename"]),
            "mime": payload.get("mime", "text/plain"),
            "origin": payload.get("origin", "upload"),
            "text": text,
            "sha256": digest,
            "size": len(text.encode()),
            "status": "processing",
            "created_at": prior["created_at"] if prior else now(),
            "received_at": now(),
            "gcs_uri": payload.get("gcs_uri"),
            "parser": payload.get("parser", "supplied-text"),
            "source_type": payload.get("source_type"),
            "raw_sha256": payload.get("raw_sha256"),
            "raw_content_base64": payload.get("content_base64"),
            "chunks": [],
            "mentions": [],
            "facts": [],
            "entities": [],
            "extractor_version": version,
            "job_id": job["id"],
        }
        state["documents"][document_id] = document
        self.embedder.upsert(state, document_id, "title", document["title"])
        previous = None
        for chunk in chunks:
            chunk_id = f"chunk:{digest[:20]}-{chunk['ordinal']}"
            chunk.update(id=chunk_id, document_id=document_id)
            state["chunks"][chunk_id] = chunk
            document["chunks"].append(chunk_id)
            self.embedder.upsert(state, chunk_id, "text", chunk["text"])
            add_edge(state, document_id, chunk_id, "contains")
            if previous:
                add_edge(state, previous, chunk_id, "next")
            previous = chunk_id
        records = (
            extracted.get("entities", [])
            if extracted is not None
            else local_candidates(state, text, payload)
        )
        if extracted is not None:
            records += copy.deepcopy(payload.get("records") or [])
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise ValueError("Extracted entities must be objects")
        records += claim_candidates(state, text, payload, records)
        # Only admin-configured primary types are ingested; drop the rest and their relations.
        primary = primary_types(state)
        skipped = [r for r in records if r.get("type") not in primary]
        records = [r for r in records if r.get("type") in primary]
        skipped_names = {r.get("name") for r in skipped}
        relationships = [
            r for r in (extracted or {}).get("relationships") or []
            if not {r.get("source"), r.get("target")} & skipped_names
        ]
        job["skipped_types"] = sorted({str(r.get("type")) for r in skipped})
        records.sort(key=lambda candidate: candidate.get("type") == "transaction")
        resolved_names = {}
        financial_started = False
        for candidate in records:
            if not isinstance(candidate, dict):
                raise ValueError("Extracted entities must be objects")
            spans = mention_spans(candidate, text)
            evidence_rows = candidate_evidence(candidate, spans, chunks, text, document)
            if candidate.get("type") == "transaction":
                if not financial_started:
                    link_candidate_relations(state, records, resolved_names, relationships)
                    financial_started = True
                entity, method = resolve_financial(state, candidate, evidence_rows, document)
                if entity.get("status") == "unallocated":
                    document.setdefault("unallocated", []).append(entity["id"])
                    continue
            else:
                entity, method = resolve(state, candidate, self.embedder, extractor)
            document["entities"].append(entity["id"])
            resolved_names[candidate["name"]] = entity["id"]
            decision_id = identifier("resolution")
            state["resolutions"][decision_id] = {
                "id": decision_id,
                "document_id": document_id,
                "name": candidate["name"],
                "entity_id": entity["id"],
                "method": method,
                "extractor_version": version,
                "created_at": now(),
            }
            for evidence in evidence_rows:
                document["mentions"].append({**evidence, "entity_id": entity["id"]})
                if evidence not in entity["evidence"]:
                    entity["evidence"].append(evidence)
                add_edge(state, evidence["chunk_id"], entity["id"], "mentions", evidence=[evidence])
                add_edge(state, entity["id"], evidence["chunk_id"], "evidenced_by", evidence=[evidence])
            if entity["type"] in ("email", "call"):
                add_edge(state, entity["id"], document_id, "derived_from")
        if not financial_started:
            link_candidate_relations(state, records, resolved_names, relationships)
        document["entities"] = list(dict.fromkeys(document["entities"]))
        for fact in (extracted or {}).get("facts", []) + payload.get("facts", []):
            self._fact(state, document, chunks, fact, text, resolved_names)
        self._communications(state, document)
        document.update(status="completed", completed_at=now())
        state["jobs"][job["id"]].update(
            status="completed",
            chunks=len(chunks),
            entities=document["entities"],
            unallocated=document.get("unallocated", []),
            skipped_types=job["skipped_types"],
            extraction_warnings=job.get("extraction_warnings", []),
            completed_at=now(),
        )
        recompute_enabled(state)
        publish(
            state,
            "ingestion.completed",
            {"id": job["id"], "document_id": document_id, "entities": document["entities"]},
        )
        return state["jobs"][job["id"]]

    def _fact(self, state, document, chunks, fact, text, resolved_names):
        spans = mention_spans({"mentions": [fact], "name": fact.get("text", "")}, text)
        span = spans[0]
        chunk = next(
            item for item in chunks if item["char_start"] <= span["start"] < item["char_end"]
        )
        entity_id = fact.get("entity_id") or resolved_names.get(fact.get("entity_name"))
        if entity_id and entity_id not in state["entities"]:
            raise ValueError("Extracted fact references an unknown entity")
        key = identifier("fact")
        record = {
            "id": key,
            "document_id": document["id"],
            "chunk_id": chunk["id"],
            "entity_id": entity_id,
            "key": fact["key"],
            "value": fact.get("value"),
            "text": fact.get("text", span["text"]),
            "span": {"start": span["start"], "end": span["end"]},
            "confidence": span["confidence"],
            "extractor_version": document["extractor_version"],
        }
        state["facts"][key] = record
        document["facts"].append(key)
        self.embedder.upsert(state, key, "text", record["text"])
        if entity_id:
            add_edge(
                state,
                key,
                entity_id,
                "about",
                evidence=[{"document_id": document["id"], "chunk_id": chunk["id"]}],
            )

    def _communications(self, state, document):
        entities = [state["entities"][key] for key in document["entities"]]
        for entity in entities:
            fields = entity["fields"]
            if entity["type"] == "email":
                for person in entities:
                    if person["type"] != "person":
                        continue
                    emails = set(person["fields"].get("emails", []))
                    if fields.get("from_address", "").lower() in emails:
                        add_edge(state, entity["id"], person["id"], "sent_by")
                    if emails & set(
                        fields.get("to_addresses", []) + fields.get("cc_addresses", [])
                    ):
                        add_edge(state, entity["id"], person["id"], "sent_to")
                parent = fields.get("in_reply_to")
                for other in state["entities"].values():
                    if (
                        parent
                        and other["type"] == "email"
                        and other["fields"].get("message_id") == parent
                    ):
                        add_edge(state, entity["id"], other["id"], "reply_to")
            elif entity["type"] == "call":
                numbers = {fields.get("from_number"), fields.get("to_number")}
                for person in entities:
                    if person["type"] == "person" and numbers & set(
                        person["fields"].get("phones", [])
                    ):
                        add_edge(state, entity["id"], person["id"], "with")
            else:
                continue
            for other in entities:
                if other["type"] in ("ticket", "company", "property", "service_provider"):
                    add_edge(
                        state,
                        entity["id"],
                        other["id"],
                        "about",
                        evidence=[{"document_id": document["id"]}],
                    )
