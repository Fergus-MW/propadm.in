"""Validate references, schema input and independent economic expectations."""

import hashlib
import json
from pathlib import Path

from .io import digest, read_json


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path leaves data pack: {relative}")
    return path


def read_pack(root):
    root = Path(root).resolve()
    manifest = read_json(root / "manifest.json")
    if manifest.get("kind") != "synthetic_property_portfolio":
        raise ValueError("Expected a synthetic property portfolio")
    indexes = [read_json(inside(root, path)) for path in manifest["index_files"]]
    sources = [source for index in indexes for source in index["sources"]]
    if digest(sources) != manifest["sources_sha256"]:
        raise ValueError("Source index hash mismatch")
    if len({r["path"] for r in sources}) != len(sources):
        raise ValueError("Duplicate source path")
    records = {}
    for row in sources:
        raw = inside(root, row["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"Source hash mismatch: {row['path']}")
        candidates = json.loads(raw) if row["upload"]["mime"] == "application/json" else row["upload"].get("records", [])
        for candidate in candidates:
            if candidate.get("id"):
                previous = records.get(candidate["id"])
                if previous and previous != candidate:
                    raise ValueError(f"Conflicting structured identity: {candidate['id']}")
                records[candidate["id"]] = candidate
    for row in records.values():
        for key in ("property_id", "provider_id", "ticket_id"):
            if row.get(key) and row[key] not in records:
                raise ValueError(f"Unresolved {key}: {row[key]}")
    for index in indexes:
        for edge in index["relationships"]:
            if edge["source"] not in records or edge["target"] not in records:
                raise ValueError(f"Dangling declared relationship: {edge}")
    return manifest, indexes


def verify_state(state, expected):
    entities, edges = state["entities"], list(state["edges"].values())
    problems = []

    def require(value, description):
        if not value:
            problems.append(description)

    def linked(source, target, relation):
        return any(e["source"] == source and e["target"] == target and e["relation"] == relation for e in edges)

    from propadmin_core.ledger import balances

    for row in expected:
        prop = row["property_id"]
        require(prop in entities, f"Missing property {prop}")
        if prop not in entities:
            continue
        require(balances(state, prop) == row["balances"], f"Unexpected balances for {prop}: {balances(state, prop)} != {row['balances']}")
        for tenant in row["tenant_ids"]:
            require(linked(tenant, prop, "tenant_of"), f"Missing tenancy {tenant} -> {prop}")
        for owner in row["owners"]:
            require(any(e["source"] == owner["source"] and e["target"] == prop and e["relation"] == "owns"
                        and e.get("share_pct") == owner["attributes"]["share_pct"] for e in edges), f"Ownership mismatch for {prop}")
        for repair in row["repairs"]:
            ticket, quote, provider = repair["ticket_id"], repair["quote_id"], repair["provider_id"]
            require(linked(ticket, prop, "at"), f"Missing ticket/property link: {ticket}")
            require(linked(quote, ticket, "for") and linked(quote, provider, "from"), f"Missing quote links: {quote}")
            require(bool(entities.get(ticket, {}).get("evidence")), f"Missing ticket source evidence: {ticket}")
            if repair["variant"] not in {"completed_paid", "completed_no_charge"}:
                require(entities.get(ticket, {}).get("fields", {}).get("status") != "resolved", f"Open repair became resolved: {ticket}")
    require(len(state.get("unallocated", {})) == sum(e["unallocated_count"] for e in expected), "Unexpected unallocated payment count")
    # Duplicate names are allowed; duplicate unique email identities are not.
    identities = {}
    for entity in entities.values():
        if entity["type"] == "person" and not entity.get("merged_into"):
            for email in entity["fields"].get("emails", []):
                require(email not in identities, f"Duplicate person email: {email}")
                identities[email] = entity["id"]
        if entity["type"] == "transaction":
            targets = [e for e in edges if e["source"] == entity["id"] and e["relation"] == "for"]
            require(len(targets) == 1 and entities.get(targets[0]["target"], {}).get("type") == "property",
                    f"Transaction lacks exactly one property: {entity['id']}")
            require(bool(entity.get("evidence")), f"Transaction lacks source evidence: {entity['id']}")
    return problems
