"""Atomic, append-only property ledgers with reconciliation and auditable evidence."""

import copy
import hashlib
import re
from datetime import date, timedelta
from decimal import Decimal

from .embeddings import EmbeddingService
from .graph import add_edge, create_in_state, record_change
from .ledger_rules import (
    BALANCES,
    CATEGORY_RULES,
    STATUSES,
    economic_effect,
    iso_date,
    positive,
    rounded,
    validate_economics,
)
from .store import ConflictError, identifier, now, publish


def resolve(state, ref, expected=None):
    entity = state["entities"].get(ref)
    if not entity:
        entity = next((e for e in state["entities"].values()
                       if e["fields"].get("ref") == ref and not e.get("merged_into")), None)
    if not entity or entity.get("merged_into"):
        raise KeyError(ref)
    if expected and entity["type"] not in (
        expected if isinstance(expected, tuple) else (expected,)
    ):
        raise ValueError(f"Expected {expected}")
    return entity


def edges_from(state, entity_id, relation=None):
    return [e for e in state["edges"].values() if e["source"] == entity_id
            and (relation is None or e["relation"] == relation)]


def property_id(state, tx_id):
    links = edges_from(state, tx_id, "for")
    if len(links) != 1:
        raise ValueError("Every canonical transaction must have exactly one property")
    return links[0]["target"]


def is_reversed(state, tx_id):
    return any(e["target"] == tx_id and e["relation"] == "reverses"
               for e in state["edges"].values())


def effect(state, tx):
    values = economic_effect(tx["fields"])
    if edges_from(state, tx["id"], "reverses"):
        return {key: -value for key, value in values.items()}
    return values


def transactions(state, prop):
    ids = {e["source"] for e in state["edges"].values()
           if e["relation"] == "for" and e["target"] == prop}
    return sorted([state["entities"][key] for key in ids
                   if state["entities"].get(key, {}).get("type") == "transaction"],
                  key=lambda tx: (tx["fields"]["effective_date"], tx["created_at"], tx["id"]))


def balances(state, prop):
    result = dict.fromkeys(BALANCES, 0)
    for tx in transactions(state, prop):
        for key, value in effect(state, tx).items():
            result[key] += value
    if any(abs(value) > 2**53 - 1 for value in result.values()):
        raise ValueError("Derived balances exceed the exact supported pence range")
    return result


def refresh(state, prop):
    entity = resolve(state, prop, "property")
    entity["fields"].update(balances(state, prop))
    entity.update(version=entity["version"] + 1, updated_at=now())
    publish(state, "ledger.updated", {"property_id": prop, "balances": balances(state, prop)})
    from .provider_directory import refresh_metrics
    refresh_metrics(state)


def issue(state, key, title, description, entity_id, severity="medium"):
    issue_id = "workflow_issue:ledger-" + key.replace(":", "-")
    if issue_id in state["entities"]:
        return
    create_in_state(state, {
        "id": issue_id, "type": "workflow_issue", "name": title,
        "description": description, "fields": {
            "title": title, "evidence": description, "category": "ledger",
            "severity": severity, "status": "open", "occurrences": 1,
        },
    }, "ledger", "Ledger mismatch")
    add_edge(state, issue_id, entity_id, "about")


def active_allocation(state, edge):
    return (not is_reversed(state, edge["source"]) and not is_reversed(state, edge["target"])
            and not edges_from(state, edge["source"], "reverses"))


def allocated(state, tx_id, direction):
    return sum(e.get("amount_minor", 0) for e in state["edges"].values()
               if e["relation"] == "settles" and e[direction] == tx_id
               and active_allocation(state, e))


def set_status(state, tx, status, actor, reason=None):
    old = tx["fields"]["status"]
    if status not in STATUSES or old not in STATUSES or STATUSES[status] < STATUSES[old]:
        raise ValueError("Transaction status may only advance")
    if old != status:
        before = copy.deepcopy(tx)
        tx["fields"]["status"] = status
        tx.update(version=tx["version"] + 1, updated_at=now())
        record_change(state, "ledger.status", actor, reason or "Evidence/reconciliation promotion", before, tx)


def settlement(state, payment, charge, amount=None, actor="ledger"):
    p, c = payment["fields"], charge["fields"]
    if p["kind"] != "payment" or c["kind"] != "charge":
        raise ValueError("Settlement requires a payment and a charge")
    if p["status"] not in ("cleared", "reconciled"):
        raise ValueError("Pending payment claims cannot settle charges")
    if property_id(state, payment["id"]) != property_id(state, charge["id"]):
        raise ValueError("Payments and charges must belong to the same property")
    compatible = ((p["category"] == "rent_received" and c["category"] in
                   ("rent_due", "tenant_recharge")) or
                  (p["category"] == "expense" and c["category"] == "expense"))
    if not compatible:
        raise ValueError("Payment category cannot settle this charge")
    if is_reversed(state, payment["id"]) or is_reversed(state, charge["id"]):
        raise ValueError("Reversed entries cannot be settled")
    if edges_from(state, payment["id"], "reverses") or edges_from(state, charge["id"], "reverses"):
        raise ValueError("Reversal entries cannot be settled")
    remaining_p = p["amount_minor"] - allocated(state, payment["id"], "source")
    remaining_c = c["amount_minor"] - allocated(state, charge["id"], "target")
    amount = min(remaining_p, remaining_c) if amount is None else positive(amount)
    positive(amount)
    if amount > min(remaining_p, remaining_c):
        raise ValueError("Settlement exceeds remaining payment or charge")
    existing = next((e for e in edges_from(state, payment["id"], "settles")
                     if e["target"] == charge["id"]), None)
    if existing:
        existing["amount_minor"] += amount
        edge = existing
    else:
        edge = add_edge(state, payment["id"], charge["id"], "settles")
        edge["amount_minor"] = amount
    if amount == remaining_p:
        set_status(state, payment, "reconciled", actor)
    if amount == remaining_c:
        set_status(state, charge, "reconciled", actor)
    publish(state, "ledger.settled", {"payment_id": payment["id"], "charge_id": charge["id"],
                                      "amount_minor": amount})
    return edge


def reconcile(state, prop):
    txs = transactions(state, prop)
    charges = [t for t in txs if t["fields"]["kind"] == "charge"
               and not is_reversed(state, t["id"]) and not edges_from(state, t["id"], "reverses")]
    payments = [t for t in txs if t["fields"]["kind"] == "payment"
                and t["fields"]["status"] in ("cleared", "reconciled")
                and not is_reversed(state, t["id"]) and not edges_from(state, t["id"], "reverses")]
    for payment in payments:
        category = payment["fields"]["category"]
        if category not in ("rent_received", "expense"):
            continue
        for charge in charges:
            if allocated(state, payment["id"], "source") >= payment["fields"]["amount_minor"]:
                break
            if allocated(state, charge["id"], "target") >= charge["fields"]["amount_minor"]:
                continue
            if category == "rent_received" and charge["fields"]["category"] not in (
                "rent_due", "tenant_recharge"
            ):
                continue
            if category == "expense":
                if charge["fields"]["category"] != "expense":
                    continue
                if payment["fields"].get("external_ref") != charge["fields"].get("external_ref"):
                    p_tickets = {e["target"] for e in edges_from(state, payment["id"], "for_ticket")}
                    c_tickets = {e["target"] for e in edges_from(state, charge["id"], "for_ticket")}
                    if not p_tickets.intersection(c_tickets):
                        continue
            settlement(state, payment, charge)
        if allocated(state, payment["id"], "source") == 0:
            issue(state, payment["id"], "Payment without matching charge",
                  "A cleared payment has no matching open charge", payment["id"])
    for charge in charges:
        fields = charge["fields"]
        if (fields["category"] == "rent_due" and
                iso_date(fields["effective_date"]) < date.today() - timedelta(days=3) and
                allocated(state, charge["id"], "target") < fields["amount_minor"]):
            issue(state, charge["id"], "Rent arrears after grace period",
                  "Rent remains unpaid after the three day grace period", charge["id"])


class LedgerService:
    def __init__(self, store):
        self.store = store
        self.embedder = EmbeddingService()

    def properties(self):
        state = self.store.snapshot()
        return sorted([e for e in state["entities"].values()
                       if e["type"] == "property" and not e.get("merged_into")], key=lambda e: e["name"])

    def get_property(self, ref_or_id):
        state = self.store.snapshot()
        prop = resolve(state, ref_or_id, "property")
        prop["edges"] = [e for e in state["edges"].values()
                         if prop["id"] in (e["source"], e["target"])]
        prop["related"] = [state["entities"][key] for key in sorted(
            {end for e in prop["edges"] for end in (e["source"], e["target"])} - {prop["id"]})
            if key in state["entities"] and state["entities"][key]["type"] != "transaction"]
        prop["balances"] = balances(state, prop["id"])
        return prop

    def get_ledger(self, property, from_date=None, to_date=None, category=None):
        state = self.store.snapshot()
        prop = resolve(state, property, "property")
        start = iso_date(from_date) if from_date else None
        end = iso_date(to_date) if to_date else None
        if start and end and start > end:
            raise ValueError("from_date must not follow to_date")
        running, opening, result = dict.fromkeys(BALANCES, 0), dict.fromkeys(BALANCES, 0), []
        closing = dict.fromkeys(BALANCES, 0)
        for tx in transactions(state, prop["id"]):
            day = iso_date(tx["fields"]["effective_date"])
            if start and day < start:
                for key, value in effect(state, tx).items():
                    opening[key] += value
            for key, value in effect(state, tx).items():
                running[key] += value
            if not end or day <= end:
                closing = copy.deepcopy(running)
            if (start and day < start) or (end and day > end):
                continue
            if category and tx["fields"]["category"] != category:
                continue
            tx["edges"] = edges_from(state, tx["id"])
            tx["running_balances"] = copy.deepcopy(running)
            tx["remaining_minor"] = tx["fields"]["amount_minor"] - allocated(
                state, tx["id"], "target" if tx["fields"]["kind"] == "charge" else "source")
            result.append(tx)
        return {"property": prop, "transactions": result, "balances": balances(state, prop["id"]),
                "opening_balances": opening, "closing_balances": closing,
                "from_date": from_date, "to_date": to_date}

    def get_balances(self, subject):
        state = self.store.snapshot()
        entity = resolve(state, subject, ("property", "person", "company"))
        if entity["type"] == "property":
            return {"subject": entity["id"], **balances(state, entity["id"])}
        totals = {key: Decimal(0) for key in BALANCES}
        properties = []
        for edge in edges_from(state, entity["id"], "owns"):
            resolve(state, edge["target"], "property")
            share = Decimal(str(edge.get("share_pct", 100)))
            if not 0 < share <= 100:
                raise ValueError("Ownership shares must be between zero and 100")
            values = balances(state, edge["target"])
            weighted = {key: Decimal(value) * share / 100 for key, value in values.items()}
            unit = resolve(state, edge["target"], "property")
            properties.append({"property_id": edge["target"], "id": edge["target"],
                               "name": unit["name"], "share_pct": float(share),
                               **{key: rounded(value) for key, value in weighted.items()}})
            for key, value in weighted.items():
                totals[key] += value
        if any(abs(rounded(value)) > 2**53 - 1 for value in totals.values()):
            raise ValueError("Landlord balances exceed the exact supported pence range")
        return {"subject": entity["id"], "properties": properties,
                **{key: rounded(value) for key, value in totals.items()}}

    def unallocated(self):
        return list(self.store.snapshot().get("unallocated", {}).values())

    def record_transaction(self, payload, actor="admin"):
        return self.store.mutate(lambda state: self._record(state, payload, actor))

    def _resolve_property(self, state, payload):
        if payload.get("property_id"):
            return resolve(state, payload["property_id"], "property")["id"]
        ids = set()
        ticket = payload.get("ticket_id")
        if ticket:
            resolve(state, ticket, "ticket")
            ids.update(e["target"] for e in edges_from(state, ticket, "at"))
        payer = payload.get("paid_by")
        if payer:
            resolve(state, payer, ("person", "company"))
            ids.update(e["target"] for e in edges_from(state, payer)
                       if e["relation"] in ("tenant_of", "owns"))
        fields = payload.get("fields", {})
        text = (str(fields.get("external_ref", "")) + " " + fields.get("description", "")).casefold()
        for e in state["entities"].values():
            ref = e["fields"].get("ref")
            if e["type"] == "property" and ref and re.search(
                r"(?<!\w)" + re.escape(ref.casefold()) + r"(?!\w)", text
            ):
                ids.add(e["id"])
        return ids.pop() if len(ids) == 1 else None

    def _duplicate(self, state, prop, fields):
        for tx in transactions(state, prop):
            other = tx["fields"]
            if edges_from(state, tx["id"], "reverses") or is_reversed(state, tx["id"]):
                continue
            if fields.get("ref"):
                if other["ref"] == fields["ref"]:
                    return tx
                continue
            if (other["kind"], other["category"], other["amount_minor"]) != (
                fields["kind"], fields["category"], fields["amount_minor"]
            ):
                continue
            gap = abs((iso_date(other["effective_date"]) - iso_date(fields["effective_date"])).days)
            same_ref = bool(fields.get("external_ref") and
                            fields["external_ref"] == other.get("external_ref"))
            seen_refs = {v for k, v in tx.get("external_ids", {}).items()
                         if k.startswith("ledger_ref:")}
            if other.get("external_ref"):
                seen_refs.add(other["external_ref"])
            if fields.get("external_ref") and seen_refs:
                if fields["external_ref"] not in seen_refs:
                    continue
                same_ref = True
            same_party = bool(fields.get("counterparty_name") and
                              fields["counterparty_name"].casefold() ==
                              other.get("counterparty_name", "").casefold())
            if gap <= 3 and (same_ref or same_party):
                return tx
        return None

    def _evidence(self, state, tx, payload):
        reference = payload.get("fields", {}).get("external_ref")
        if reference:
            key = "ledger_ref:" + hashlib.sha256(reference.encode()).hexdigest()[:16]
            tx["external_ids"][key] = reference
        for supplied in payload.get("evidence", []):
            if not isinstance(supplied, (str, dict)):
                raise ValueError("Evidence must contain chunk ids or provenance objects")
            item = {"chunk_id": supplied} if isinstance(supplied, str) else copy.deepcopy(supplied)
            chunk_id = item.get("chunk_id", item.get("chunk"))
            if chunk_id:
                if chunk_id not in state["chunks"]:
                    raise KeyError(chunk_id)
                chunk = state["chunks"][chunk_id]
                item["chunk_id"] = chunk_id
                item.setdefault("document_id", chunk.get("document_id"))
                item.setdefault("confidence", 1.0)
                document = state["documents"].get(item.get("document_id"))
                if document:
                    span = item.setdefault("span", {
                        "start": chunk["char_start"], "end": chunk["char_end"], "text": chunk["text"],
                    })
                    start, end = span.get("start"), span.get("end")
                    if type(start) is not int or type(end) is not int or not (
                        chunk["char_start"] <= start < end <= chunk["char_end"]
                    ):
                        raise ValueError("Ledger evidence span must lie within its source chunk")
                    if span.get("text") != document["text"][start:end]:
                        raise ValueError("Ledger evidence span does not match its source")
                    if chunk.get("document_id") != document["id"]:
                        raise ValueError("Ledger evidence document must match the chunk source")
                    add_edge(state, tx["id"], document["id"], "derived_from")
                add_edge(state, tx["id"], chunk_id, "evidenced_by", evidence=[item])
            if item not in tx["evidence"]:
                tx["evidence"].append(item)
        if payload.get("source_file"):
            if payload["source_file"] not in state["documents"]:
                raise KeyError(payload["source_file"])
            add_edge(state, tx["id"], payload["source_file"], "derived_from")

    def _record(self, state, payload, actor, *, reversed_tx=None, defer=False):
        payload = copy.deepcopy(payload)
        if set(payload) - {"property_id", "fields", "paid_by", "paid_to", "ticket_id", "evidence",
                           "source_file", "settles", "adjustment_deltas"}:
            raise ValueError("Unknown transaction payload fields")
        fields = payload.get("fields", {})
        fields.setdefault("currency", "GBP")
        fields.setdefault("status", "cleared")
        fields.setdefault("confidence", 1.0)
        fields.setdefault("description", "")
        fields.setdefault("notes", [])
        if "adjustment_deltas" in payload:
            fields["adjustment_deltas"] = payload["adjustment_deltas"]
        validate_economics(fields)
        if not isinstance(fields.get("counterparty_name", ""), str):
            raise ValueError("counterparty_name must be a string")
        fields.setdefault("counterparty_name", "")
        from .registry import validate_fields
        validate_fields(state, "transaction", {
            **fields, "ref": fields.get("ref") or "UNALLOCATED",
            "recorded_by": {"kind": "admin", "ref": actor},
        })
        prop = self._resolve_property(state, payload)
        if not prop:
            for existing in state.setdefault("unallocated", {}).values():
                other = existing["payload"]["fields"]
                if (other["kind"], other["category"], other["amount_minor"]) != (
                    fields["kind"], fields["category"], fields["amount_minor"]
                ):
                    continue
                gap = abs((iso_date(other["effective_date"]) - iso_date(fields["effective_date"])).days)
                old_ref, new_ref = other.get("external_ref"), fields.get("external_ref")
                if old_ref and new_ref and old_ref != new_ref:
                    continue
                same_ref = bool(old_ref and old_ref == new_ref)
                same_party = bool(fields.get("counterparty_name") and
                                  fields["counterparty_name"].casefold() ==
                                  other.get("counterparty_name", "").casefold())
                if gap > 3 or not (same_ref or same_party):
                    continue
                for item in payload.get("evidence", []):
                    if item not in existing["payload"].setdefault("evidence", []):
                        existing["payload"]["evidence"].append(item)
                if STATUSES[fields["status"]] > STATUSES[other["status"]]:
                    other["status"] = fields["status"]
                    other["confidence"] = max(fields["confidence"], other.get("confidence", 0))
                if new_ref and not old_ref:
                    other["external_ref"] = new_ref
                publish(state, "ledger.unallocated_evidence", {"id": existing["id"]})
                return existing
            key = identifier("unallocated")
            entry = {"id": key, "status": "unallocated", "payload": payload,
                     "actor": actor, "created_at": now()}
            state.setdefault("unallocated", {})[key] = entry
            publish(state, "ledger.unallocated", {"id": key})
            return entry
        resolve(state, prop, "property")
        duplicate = None if reversed_tx else self._duplicate(state, prop, fields)
        if duplicate:
            for key in ("kind", "category", "amount_minor", "currency", "adjustment_deltas"):
                if duplicate["fields"].get(key) != fields.get(key):
                    raise ConflictError("Transaction ref conflicts with immutable economic data")
            before = copy.deepcopy(duplicate)
            self._evidence(state, duplicate, payload)
            if STATUSES[fields["status"]] > STATUSES[duplicate["fields"]["status"]]:
                set_status(state, duplicate, fields["status"], actor)
                duplicate["fields"]["confidence"] = max(fields["confidence"],
                                                        duplicate["fields"].get("confidence", 0))
                self._fee(state, duplicate, actor)
            if duplicate != before and duplicate["version"] == before["version"]:
                duplicate.update(version=duplicate["version"] + 1, updated_at=now())
            record_change(state, "ledger.evidence", actor, "Additional transaction evidence",
                          before, duplicate)
            reconcile(state, prop)
            refresh(state, prop)
            return duplicate
        year = iso_date(fields["effective_date"]).year
        if not fields.get("ref"):
            refs = {e["fields"].get("ref") for e in state["entities"].values()
                    if e["type"] == "transaction"}
            sequence = 1
            while f"TX-{year}-{sequence:06d}" in refs:
                sequence += 1
            fields["ref"] = f"TX-{year}-{sequence:06d}"
        fields["recorded_by"] = {"kind": "ingestion" if actor == "ingestion" else
                                  "admin" if actor == "admin" else "agent session", "ref": actor}
        tx = create_in_state(state, {"type": "transaction", "name": fields["ref"],
                                    "description": fields["description"], "fields": fields},
                             actor, "Append ledger entry", self.embedder, ledger=True)
        for action in state["actions"].values():
            if action.get("entity_id") == tx["id"]:
                action["reversible"] = False
        add_edge(state, tx["id"], prop, "for")
        for key, relation, types in (
            ("paid_by", "paid_by", ("person", "company")),
            ("paid_to", "paid_to", ("person", "company", "service_provider")),
            ("ticket_id", "for_ticket", "ticket"),
        ):
            if payload.get(key):
                related = resolve(state, payload[key], types)
                if key == "ticket_id":
                    units = {e["target"] for e in edges_from(state, related["id"], "at")}
                    if units and prop not in units:
                        raise ValueError("Ticket and transaction must refer to the same property")
                add_edge(state, tx["id"], related["id"], relation)
        self._evidence(state, tx, payload)
        if reversed_tx:
            add_edge(state, tx["id"], reversed_tx["id"], "reverses")
        else:
            self._fee(state, tx, actor)
        if payload.get("settles"):
            target = payload["settles"]
            if isinstance(target, str):
                settlement(state, tx, resolve(state, target, "transaction"))
            else:
                for match in target:
                    settlement(state, tx, resolve(state, match["charge_id"], "transaction"),
                               match.get("amount_minor"))
        for edge in edges_from(state, tx["id"], "for_ticket"):
            ticket = resolve(state, edge["target"], "ticket")
            estimate = ticket["fields"].get("cost_estimate")
            if fields["category"] == "expense" and estimate is not None:
                if fields["amount_minor"] > rounded(Decimal(str(estimate)) * 100):
                    issue(state, tx["id"] + "-overrun", "Contractor invoice exceeds estimate",
                          "Invoice amount exceeds the linked ticket cost estimate", tx["id"], "high")
        if not defer:
            reconcile(state, prop)
            refresh(state, prop)
        return tx

    def _fee(self, state, tx, actor):
        fields = tx["fields"]
        if fields["category"] != "rent_received" or fields["status"] not in ("cleared", "reconciled"):
            return
        if any(e["relation"] == "fee_for" and e["target"] == tx["id"]
               for e in state["edges"].values()):
            return
        prop = property_id(state, tx["id"])
        pct = resolve(state, prop, "property")["fields"].get("management_fee_pct")
        if pct is None or pct == 0:
            return
        if not 0 <= Decimal(str(pct)) <= 100:
            raise ValueError("Management fee percentage must be between zero and 100")
        amount = rounded(Decimal(fields["amount_minor"]) * Decimal(str(pct)) / 100)
        if amount <= 0:
            return
        fee = self._record(state, {"property_id": prop, "fields": {
            "ref": fields["ref"] + "-FEE", "kind": "charge", "category": "management_fee",
            "amount_minor": amount, "effective_date": fields["effective_date"],
            "counterparty_name": "Managing agent", "description": "Management fee on " + fields["ref"],
        }, "evidence": tx.get("evidence", []) + resolve(state, prop, "property").get("evidence", [])},
                           actor, defer=True)
        add_edge(state, fee["id"], tx["id"], "fee_for")

    def reverse_transaction(self, tx_id, reason, actor="admin"):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A reversal reason is required")
        def reverse(state):
            tx = resolve(state, tx_id, "transaction")
            if is_reversed(state, tx["id"]):
                raise ConflictError("Transaction has already been reversed")
            if edges_from(state, tx["id"], "reverses"):
                raise ValueError("Reversal entries cannot be reversed; append a correct entry")
            result = self._reverse(state, tx, reason, actor)
            for edge in list(state["edges"].values()):
                if edge["relation"] == "fee_for" and edge["target"] == tx["id"]:
                    fee = resolve(state, edge["source"], "transaction")
                    if not is_reversed(state, fee["id"]):
                        self._reverse(state, fee, reason, actor)
            prop = property_id(state, tx["id"])
            reconcile(state, prop)
            refresh(state, prop)
            if actor not in ("admin", "ingestion", "ledger"):
                issue(state, result["id"], "Ledger correction after agent workflow",
                      reason, result["id"], "high")
            return result
        return self.store.mutate(reverse)

    def _reverse(self, state, tx, reason, actor):
        fields = copy.deepcopy(tx["fields"])
        fields["ref"] += "-REV"
        fields["notes"] = fields.get("notes", []) + [reason]
        fields["description"] = "Reversal: " + fields.get("description", "")
        fields.pop("external_ref", None)
        payload = {"property_id": property_id(state, tx["id"]), "fields": fields,
                   "evidence": tx.get("evidence", [])}
        for edge in edges_from(state, tx["id"]):
            key = {"paid_by": "paid_by", "paid_to": "paid_to", "for_ticket": "ticket_id"}.get(
                edge["relation"])
            if key:
                payload[key] = edge["target"]
        return self._record(state, payload, actor, reversed_tx=tx, defer=True)

    def allocate(self, tx_id, property_id, actor="admin", category=None, kind=None):
        def allocate(state):
            if tx_id in state["entities"]:
                raise ValueError("Canonical transaction property cannot change")
            entry = state.setdefault("unallocated", {})[tx_id]
            payload = {**copy.deepcopy(entry["payload"]), "property_id": property_id}
            if entry.get("needs_classification") and not category:
                raise ValueError("This receipt requires an explicit category before allocation")
            if category:
                if category not in CATEGORY_RULES:
                    raise ValueError("Unknown transaction category")
                expected = CATEGORY_RULES[category][0]
                payload["fields"].update(category=category, kind=kind or (
                    "payment" if isinstance(expected, tuple) else expected))
            elif kind:
                payload["fields"]["kind"] = kind
            result = self._record(state, payload, entry["actor"])
            del state["unallocated"][tx_id]
            publish(state, "ledger.allocated", {"id": tx_id, "transaction_id": result["id"], "actor": actor})
            return result
        return self.store.mutate(allocate)

    def settle(self, payment_id, charge_id, amount_minor=None, actor="admin"):
        def settle(state):
            payment, charge = resolve(state, payment_id, "transaction"), resolve(
                state, charge_id, "transaction")
            result = settlement(state, payment, charge, amount_minor, actor)
            refresh(state, property_id(state, payment["id"]))
            return result
        return self.store.mutate(settle)

    def promote_status(self, tx_id, status, evidence=None, actor="admin", reason=None):
        def promote(state):
            tx = resolve(state, tx_id, "transaction")
            if is_reversed(state, tx["id"]) or edges_from(state, tx["id"], "reverses"):
                raise ValueError("Reversed entries cannot change status")
            set_status(state, tx, status, actor, reason)
            self._evidence(state, tx, {"evidence": evidence or []})
            self._fee(state, tx, actor)
            prop = property_id(state, tx["id"])
            reconcile(state, prop)
            refresh(state, prop)
            return tx
        return self.store.mutate(promote)

    def statement(self, subject, period):
        from .ledger_schedule import statement_period
        start, end = statement_period(period)
        state = self.store.snapshot()
        entity = resolve(state, subject, ("property", "person", "company"))
        ids = ([entity["id"]] if entity["type"] == "property" else
               [e["target"] for e in edges_from(state, entity["id"], "owns")])
        rows = [self.get_ledger(key, start, end) for key in ids]
        totals = {key: Decimal(0) for key in BALANCES}
        for row in rows:
            share = Decimal(100)
            if entity["type"] != "property":
                ownership = next(e for e in edges_from(state, entity["id"], "owns")
                                 if e["target"] == row["property"]["id"])
                share = Decimal(str(ownership.get("share_pct", 100)))
            row["share_pct"] = float(share)
            for key, value in row["closing_balances"].items():
                totals[key] += Decimal(value) * share / 100
        return {"subject": entity, "period": period, "from_date": start, "to_date": end,
                "properties": rows,
                "balances": {"subject": entity["id"],
                             **{key: rounded(value) for key, value in totals.items()}}, "currency": "GBP"}

    def generate_rent_due(self, as_of=None):
        from .ledger_schedule import generate_rent
        return self.store.mutate(lambda state: generate_rent(state, self, as_of))


def record_in_state(state, payload, actor="ingestion"):
    """Ingestion/quote integration within the caller's existing atomic mutation."""
    return LedgerService(None)._record(state, payload, actor)
