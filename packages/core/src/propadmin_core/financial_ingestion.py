"""Financial extraction adapters into the common provenance and atomic ledger pipeline."""

import copy
import hashlib
import json
import re
from datetime import date

from .financial_parsers import money_minor
from .graph import add_edge, record_change
from .graph_relationships import validate_relationship
from .ledger import LedgerService, record_in_state


def canonical_reference(state, value, types):
    if not value:
        return None
    if isinstance(types, str):
        types = (types,)
    direct = state["entities"].get(value)
    if direct and direct["type"] in types and not direct.get("merged_into"):
        return direct["id"]
    needle = str(value).strip().casefold()
    matches = []
    for entity in state["entities"].values():
        if entity["type"] not in types or entity.get("merged_into"):
            continue
        terms = [entity["name"], entity["fields"].get("ref", "")] + entity.get("aliases", [])
        if needle in {str(term).casefold() for term in terms if term}:
            matches.append(entity["id"])
    return matches[0] if len(matches) == 1 else None


def candidate_evidence(candidate, spans, chunks, text, document):
    result = []
    for span in spans:
        overlapping = [chunk for chunk in chunks
                       if chunk["char_start"] < span["end"] and chunk["char_end"] > span["start"]]
        containing = [chunk for chunk in overlapping
                      if chunk["char_start"] <= span["start"] and chunk["char_end"] >= span["end"]]
        for chunk in containing[:1] or overlapping:
            start, end = max(span["start"], chunk["char_start"]), min(span["end"], chunk["char_end"])
            result.append({
                "document_id": document["id"], "chunk_id": chunk["id"],
                "span": {"start": start, "end": end, "text": text[start:end]},
                "confidence": span["confidence"], "fields": list(candidate.get("fields", {})),
                "extractor_version": document["extractor_version"],
                "method": span.get("method", "exact_span"),
            })
    return result


def resolve_financial(state, candidate, evidence, document):
    ledger = LedgerService(None)
    if candidate.get("id") in state["entities"] and not candidate.get("fields"):
        entity = state["entities"][candidate["id"]]
        if entity["type"] != "transaction":
            raise ValueError("Transaction mention points to a different entity type")
        before = copy.deepcopy(entity)
        ledger._evidence(state, entity, {"evidence": evidence, "source_file": document["id"]})
        if entity != before:
            from .store import now
            entity.update(version=entity["version"] + 1, updated_at=now())
            record_change(state, "ledger.evidence", "ingestion", "Source mentions recorded transaction",
                          before, entity)
        return entity, "record_id"
    fields = copy.deepcopy(candidate.get("fields", {}))
    if candidate.get("source_type") == "bank_statement":
        fields.update(confidence=1.0, status="cleared")
    fields.setdefault("description", candidate.get("description", ""))
    prop_ref = candidate.get("property_id") or candidate.get("property_ref")
    prop = canonical_reference(state, prop_ref, "property")
    if prop_ref and not prop:
        # Retain unknown references in the narrative for later queue allocation.
        fields["description"] += " Property reference: " + str(prop_ref)
    provider = canonical_reference(state, candidate.get("provider_id") or
                                   candidate.get("paid_to") or fields.get("counterparty_name"),
                                   ("service_provider", "company", "person"))
    ticket = canonical_reference(state, candidate.get("ticket_id"), "ticket")
    incoming_category = fields.get("category") in {"rent_received", "deposit_received", "landlord_contribution"}
    payer = canonical_reference(state, candidate.get("paid_by") or
                                (fields.get("counterparty_name") if incoming_category else None),
                                ("person", "company"))
    payload = {
        "property_id": prop, "fields": fields, "paid_by": payer,
        "paid_to": provider if fields.get("category") == "expense" else
                   canonical_reference(state, candidate.get("paid_to"), ("person", "company")),
        "ticket_id": ticket, "evidence": evidence, "source_file": document["id"],
    }
    if candidate.get("needs_classification"):
        from .registry import validate_fields
        from .store import publish

        validate_fields(state, "transaction", {
            **fields, "ref": fields.get("ref") or "UNCLASSIFIED", "currency": "GBP",
            "category": "expense", "kind": "payment",
        })

        payload["paid_to"] = provider
        fingerprint = json.dumps({key: fields.get(key) for key in (
            "external_ref", "amount_minor", "effective_date", "counterparty_name",
        )}, sort_keys=True)
        key = "unallocated:receipt-" + hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
        entry = state.setdefault("unallocated", {}).setdefault(key, {
            "id": key, "status": "unallocated", "needs_classification": True,
            "payload": payload, "actor": "ingestion", "created_at": document["created_at"],
        })
        for item in evidence:
            if item not in entry["payload"].setdefault("evidence", []):
                entry["payload"]["evidence"].append(item)
        publish(state, "ledger.classification_required", {"id": key, "document_id": document["id"]})
        return entry, "classification_required"
    result = record_in_state(state, payload, "ingestion")
    return result, "ledger_dedupe_or_append"


def claim_candidates(state, text, payload, records):
    """Conservative offline claims: one explicitly stated payment amount, never inferred bank money."""
    if any(record.get("type") == "transaction" for record in records):
        return []
    communication = next((r for r in records if r.get("type") in ("email", "call")), None)
    if not communication:
        return []
    body = communication.get("fields", {}).get("body_text") or communication.get("fields", {}).get(
        "transcript_text") or text
    matches = list(re.finditer(r"(?i)\b(?:paid|transferred|sent)\s+(?:the\s+rent\s+of\s+)?£([\d,]+\.\d{2}|[\d,]+)\b", body))
    if len(matches) != 1:
        return []
    explicit = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", body)
    fields = communication.get("fields", {})
    sent = fields.get("sent_at") or fields.get("started_at") or payload.get("received_at")
    if explicit:
        effective = explicit[1]
    elif re.search(r"(?i)\btoday\b", body):
        effective = sent[:10] if sent else date.today().isoformat()
    else:
        return []
    sender = fields.get("from_address")
    parties = [e for e in state["entities"].values() if e["type"] == "person"
               and sender in e["fields"].get("emails", [])] if sender else []
    party = parties[0] if len(parties) == 1 else None
    return [{"type": "transaction", "name": "Reported rent payment", "fields": {
        "kind": "payment", "category": "rent_received", "amount_minor": money_minor(matches[0][1]),
        "effective_date": effective, "status": "pending", "confidence": 0.4,
        "counterparty_name": party["name"] if party else fields.get("from_name", "Unknown tenant"),
        "description": body,
    }, "paid_by": party["id"] if party else None}]


def validated_edge(state, source, target, relation, attributes=None):
    metadata = validate_relationship(state, source, target, relation, attributes)
    edge = add_edge(state, source, target, relation)
    edge.update(metadata)
    return edge


def link_candidate_relations(state, records, resolved_names, relationships=None):
    for candidate in records:
        source = resolved_names.get(candidate.get("name")) or candidate.get("id")
        if source not in state["entities"]:
            continue
        type_name = state["entities"][source]["type"]
        provider = canonical_reference(state, candidate.get("provider_id"), "service_provider")
        prop = canonical_reference(state, candidate.get("property_id") or candidate.get("property_ref"), "property")
        if type_name == "service_offering" and provider:
            validated_edge(state, provider, source, "offers")
        if type_name == "property" and candidate.get("tenant_id"):
            tenant = canonical_reference(state, candidate["tenant_id"], "person")
            if tenant:
                fields = state["entities"][source]["fields"]
                validated_edge(state, tenant, source, "tenant_of", {
                    "from": fields.get("tenancy_start"), "to": fields.get("tenancy_end"),
                    "is_lead_tenant": True,
                })
        if type_name == "ticket" and prop:
            validated_edge(state, source, prop, "at")
        if type_name == "quote" and provider:
            validated_edge(state, source, provider, "from")
            ticket = canonical_reference(state, candidate.get("ticket_id"), "ticket")
            if ticket:
                validated_edge(state, source, ticket, "for")
    allowed = {"offers", "at", "about", "mentions", "contact", "registered_as", "tenant_of", "owns", "manages"}
    for relationship in relationships or []:
        relation = relationship.get("relation")
        if relation not in allowed:
            raise ValueError("Unsupported extracted relationship")
        source = resolved_names.get(relationship.get("source")) or relationship.get("source")
        target = resolved_names.get(relationship.get("target")) or relationship.get("target")
        if source not in state["entities"] or target not in state["entities"]:
            raise ValueError("Extracted relationship references unresolved entities")
        if any(state["entities"][key]["type"] == "transaction" for key in (source, target)):
            raise ValueError("Transaction relationships belong to the ledger")
        metadata = relationship.get("attributes", {})
        validated_edge(state, source, target, relation, metadata)


def tenancy_candidates(state, text, payload):
    """Labelled tenancy documents update a known unit, with explicit tenant relationships."""
    if payload.get("source_type") not in ("rent_schedule", "tenancy_agreement"):
        return []
    from .financial_parsers import source_date

    def labelled(label):
        match = re.search(rf"(?im)^\s*(?:{label})\s*[:#]\s*(.+?)\s*$", text)
        return match[1] if match else None

    reference = labelled("property|property ref")
    property_id = canonical_reference(state, reference, "property")
    if not property_id:
        return []  # New units need explicit address schemas or configured semantic extraction.
    prop = state["entities"][property_id]
    fields = {}
    for key, labels in (("rent_amount_minor", "rent|rent amount"),
                        ("deposit_amount_minor", "deposit|deposit amount")):
        value = labelled(labels)
        if value:
            fields[key] = money_minor(value)
    frequency, due = labelled("frequency|rent frequency"), labelled("due day|rent due day")
    if frequency:
        fields["rent_frequency"] = frequency.lower()
    if due:
        fields["rent_due_day"] = int(due)
    for key, label in (("tenancy_start", "tenancy start|start date"),
                       ("tenancy_end", "tenancy end|end date")):
        value = labelled(label)
        if value:
            fields[key] = source_date(value)
    tenant_id = canonical_reference(state, labelled("tenant|tenant name"), "person")
    return [{"id": property_id, "type": "property", "name": prop["name"], "fields": fields,
             "tenant_id": tenant_id}]
