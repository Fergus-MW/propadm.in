"""Critical ledger invariants, exact money arithmetic, reconciliation and calendar accrual."""

import pytest
from propadmin_core.graph import GraphService
from propadmin_core.ledger import LedgerService
from propadmin_core.store import ConflictError, Store


@pytest.fixture
def ledger():
    store = Store()
    graph = GraphService(store)
    prop = graph.create_entity({"type": "property", "name": "E1 flat", "fields": {
        "ref": "P1", "address_line1": "1 Example Street", "postcode": "E1 1AA",
        "status": "let", "rent_amount_minor": 95000, "rent_frequency": "monthly",
        "rent_due_day": 31, "tenancy_start": "2026-01-10", "management_fee_pct": 10,
    }})
    return LedgerService(store), graph, prop["id"]


def record(service, prop, category, amount, *, kind=None, **fields):
    kinds = {"rent_due": "charge", "tenant_recharge": "charge", "management_fee": "charge",
             "deposit_deduction": "transfer", "adjustment": "adjustment"}
    return service.record_transaction({"property_id": prop, "fields": {
        "kind": kind or kinds.get(category, "payment"), "category": category,
        "amount_minor": amount, "effective_date": "2026-10-01",
        "counterparty_name": "Alice", **fields,
    }})


def test_rent_partial_reconciliation_fee_and_atomic_reversal(ledger):
    service, graph, prop = ledger
    charge = record(service, prop, "rent_due", 95000)
    payment = record(service, prop, "rent_received", 50001, external_ref="BANK-1")
    assert service.get_balances(prop)["tenant_balance_minor"] == 44999
    assert service.get_balances(prop)["landlord_balance_minor"] == 45001
    assert graph.get_entity(payment["id"])["fields"]["status"] == "reconciled"
    assert graph.get_entity(charge["id"])["fields"]["status"] == "cleared"
    with pytest.raises(ValueError, match="exceeds|positive"):
        service.settle(payment["id"], charge["id"], 1)
    reversal = service.reverse_transaction(payment["id"], "Duplicate bank import")
    values = service.get_balances(prop)
    assert values["tenant_balance_minor"] == 95000
    assert values["landlord_balance_minor"] == 0
    assert len(service.get_ledger(prop)["transactions"]) == 5
    assert graph.get_entity(reversal["id"])["edges"]
    with pytest.raises(ConflictError):
        service.reverse_transaction(payment["id"], "Again")


def test_pending_bank_promotion_dedupes_evidence_and_never_credits_twice(ledger):
    service, graph, prop = ledger
    service.store.mutate(lambda state: state["chunks"].update({"chunk:claim": {}, "chunk:bank": {}}))
    claim = service.record_transaction({"property_id": prop, "fields": {
        "kind": "payment", "category": "rent_received", "amount_minor": 95000,
        "effective_date": "2026-10-01", "counterparty_name": "Alice", "status": "pending",
        "confidence": 0.4,
    }, "evidence": ["chunk:claim"]}, "ingestion")
    assert service.get_balances(prop)["landlord_balance_minor"] == 0
    bank = service.record_transaction({"property_id": prop, "fields": {
        "kind": "payment", "category": "rent_received", "amount_minor": 95000,
        "effective_date": "2026-10-03", "counterparty_name": "Alice", "external_ref": "BANK-1",
        "status": "cleared", "confidence": 1.0,
    }, "evidence": ["chunk:bank"]}, "ingestion")
    assert bank["id"] == claim["id"]
    assert len(bank["evidence"]) == 2
    assert bank["fields"]["effective_date"] == "2026-10-01"
    service.record_transaction({"property_id": prop, "fields": {
        "kind": "payment", "category": "rent_received", "amount_minor": 95000,
        "effective_date": "2026-10-03", "counterparty_name": "Alice", "external_ref": "BANK-1",
    }}, "ingestion")
    assert service.get_balances(prop)["landlord_balance_minor"] == 85500
    assert len(service.get_ledger(prop)["transactions"]) == 2
    with pytest.raises(ValueError, match="advance"):
        service.promote_status(bank["id"], "pending")
    assert graph.get_entity(bank["id"])["fields"]["confidence"] == 1.0


def test_deposits_adjustments_and_invoice_payment_are_distinct(ledger):
    service, _, prop = ledger
    record(service, prop, "deposit_received", 100000)
    record(service, prop, "deposit_deduction", 10000)
    record(service, prop, "deposit_returned", 90000)
    assert service.get_balances(prop)["deposit_held_minor"] == 0
    invoice = record(service, prop, "expense", 12000, kind="charge", external_ref="INV-1")
    assert service.get_balances(prop)["landlord_balance_minor"] == 10000
    paid = record(service, prop, "expense", 12000, external_ref="INV-1")
    assert paid["id"] != invoice["id"]
    assert service.get_balances(prop)["landlord_balance_minor"] == -2000
    adjustment = record(service, prop, "adjustment", 2000, notes=["Landlord correction"],
                        adjustment_deltas={"landlord_balance_minor": 2000})
    assert service.get_balances(prop)["landlord_balance_minor"] == 0
    service.reverse_transaction(adjustment["id"], "Correction cancelled")
    assert service.get_balances(prop)["landlord_balance_minor"] == -2000
    for category, amount, fields in [("rent_due", True, {}), ("rent_received", 1, {"currency": "USD"}),
                                    ("adjustment", 1, {})]:
        before = service.store.snapshot()
        with pytest.raises(ValueError):
            record(service, prop, category, amount, **fields)
        assert service.store.snapshot() == before


def test_generic_graph_cannot_mutate_ledger_or_derived_balance(ledger):
    service, graph, prop = ledger
    tx = record(service, prop, "rent_due", 95000)
    edge = next(e for e in graph.get_entity(tx["id"])["edges"] if e["relation"] == "for")
    for mutation in (
        lambda: graph.create_entity({"type": "transaction", "name": "Bypass", "fields": tx["fields"]}),
        lambda: graph.update_entity(tx["id"], {"version": tx["version"], "fields": {"amount_minor": 1}}),
        lambda: graph.update_entity(prop, {"version": graph.get_entity(prop)["version"],
                                          "fields": {"tenant_balance_minor": 1}}),
        lambda: graph.unlink_entities(edge["id"]),
        lambda: graph.link_entities({"source": tx["id"], "target": prop, "relation": "for"}),
        lambda: graph.merge_entities(tx["id"], tx["id"]),
    ):
        before = service.store.snapshot()
        with pytest.raises(ValueError):
            mutation()
        assert service.store.snapshot() == before
    graph.update_entity(prop, {"version": graph.get_entity(prop)["version"], "fields": {"city": "London"}})
    assert service.get_balances(prop)["tenant_balance_minor"] == 95000


def test_unallocated_inference_owner_shares_and_statement(ledger):
    service, graph, prop = ledger
    owner = graph.create_entity({"type": "person", "name": "Landlord", "fields": {"roles": ["landlord"]}})
    service.store.mutate(lambda state: state["edges"].update({"edge:owner": {
        "id": "edge:owner", "source": owner["id"], "target": prop, "relation": "owns", "share_pct": 33.333,
    }}))
    staged = record(service, None, "landlord_contribution", 101)
    assert staged["status"] == "unallocated" and len(service.unallocated()) == 1
    duplicate = record(service, None, "landlord_contribution", 101, external_ref="BANK-STAGED",
                       effective_date="2026-10-02")
    assert duplicate["id"] == staged["id"] and len(service.unallocated()) == 1
    before = service.store.snapshot()
    with pytest.raises(ValueError, match="Unknown fields"):
        record(service, None, "landlord_contribution", 101, sort_code="00-00-00")
    assert service.store.snapshot() == before
    tx = service.allocate(staged["id"], prop)
    assert service.unallocated() == []
    assert service.get_balances(owner["id"])["landlord_balance_minor"] == 34
    with pytest.raises(ValueError, match="cannot change"):
        service.allocate(tx["id"], prop)
    statement = service.statement(owner["id"], "2026-10")
    assert statement["to_date"] == "2026-10-31"
    assert statement["properties"][0]["transactions"][0]["id"] == tx["id"]
    record(service, prop, "landlord_contribution", 101, effective_date="2026-11-01")
    assert service.get_balances(owner["id"])["landlord_balance_minor"] == 67
    historical = service.statement(owner["id"], "2026-10")
    assert historical["balances"]["landlord_balance_minor"] == 34
    assert historical["properties"][0]["closing_balances"]["landlord_balance_minor"] == 101


def test_rent_schedule_clamps_calendar_catches_up_and_is_idempotent(ledger):
    service, graph, prop = ledger
    result = service.generate_rent_due("2026-04-30")
    assert [t["fields"]["effective_date"] for t in result["created"]] == [
        "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30",
    ]
    assert service.generate_rent_due("2026-04-30")["count"] == 0
    graph.update_entity(prop, {"version": graph.get_entity(prop)["version"], "fields": {
        "tenancy_end": "2026-05-15",
    }})
    assert service.generate_rent_due("2026-07-31")["count"] == 0
    weekly = graph.create_entity({"type": "property", "name": "Weekly room", "fields": {
        "ref": "P2", "address_line1": "2 Example Street", "postcode": "E1 1AA",
        "status": "let", "rent_amount_minor": 10000, "rent_frequency": "weekly", "rent_due_day": 1,
        "tenancy_start": "2026-10-01", "tenancy_end": "2026-10-13",
    }})
    assert [t["fields"]["effective_date"] for t in service.generate_rent_due("2026-10-30")["created"]
            if t["id"] in {t["id"] for t in service.get_ledger(weekly["id"])["transactions"]}] == [
        "2026-10-05", "2026-10-12",
    ]

    quarterly = graph.create_entity({"type": "property", "name": "Quarterly unit", "fields": {
        "ref": "P3", "address_line1": "3 Example Street", "postcode": "E1 1AA",
        "status": "let", "rent_amount_minor": 300000, "rent_frequency": "quarterly", "rent_due_day": 31,
        "tenancy_start": "2026-01-01", "tenancy_end": "2026-11-01",
    }})
    result = service.generate_rent_due("2026-12-31")
    quarterly_ids = {t["id"] for t in service.get_ledger(quarterly["id"])["transactions"]}
    assert [t["fields"]["effective_date"] for t in result["created"] if t["id"] in quarterly_ids] == [
        "2026-01-31", "2026-04-30", "2026-07-31", "2026-10-31",
    ]
