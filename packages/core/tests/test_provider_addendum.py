"""Focused schema/backfill/recommendation and quote regression coverage."""

from datetime import date, timedelta

import pytest
from propadmin_core.addendum_upgrade import refresh_property_edges, upgrade_addendum
from propadmin_core.graph import GraphService, add_edge
from propadmin_core.provider_directory import ProviderService
from propadmin_core.registry import hard_keys, validate_fields
from propadmin_core.store import Store


def property_entity(graph, ref="P1", address="24 Hoxton Street", postcode="N1 6SH"):
    return graph.create_entity(
        {
            "type": "property",
            "name": ref,
            "fields": {
                "ref": ref,
                "address_line1": address,
                "postcode": postcode,
                "address_text": address + ", " + postcode,
            },
        }
    )


def provider(directory, name="Safe Plumbing", **fields):
    return directory.upsert_provider(
        {
            "name": name,
            "fields": {
                "ref": name,
                "trading_name": name,
                "trades": ["plumbing"],
                "postcode_districts": ["N1"],
                "status": "approved",
                "emergency_callout": True,
                "typical_response_hours": 2,
                **fields,
            },
        }
    )


def test_fixed_schema_normalisation_composite_keys_and_protected_metrics():
    store = Store()
    graph = GraphService(store)
    prop = property_entity(graph, postcode="n16sh")
    assert prop["fields"]["postcode"] == "N1 6SH"
    with pytest.raises(ValueError, match="read-only"):
        graph.update_entity(prop["id"], {"version": 1, "fields": {"tenant_balance_minor": 999}})
    with pytest.raises(ValueError, match="at least"):
        validate_fields(
            store.snapshot(),
            "property",
            {"ref": "P2", "address_line1": "Road", "postcode": "E1 1AA", "rent_amount_minor": -1},
        )
    directory = ProviderService(store)
    first = provider(directory, phone_main="07700 900123", emails=["OFFICE@example.org"])
    assert first["fields"]["phone_main"] == "+447700900123"
    assert first["fields"]["emails"] == ["office@example.org"]
    with pytest.raises(ValueError, match="structured"):
        provider(
            directory,
            name="Bad",
            accreditations=[{"scheme": "Gas Safe", "number": "123", "secret": "x"}],
        )
    state = store.snapshot()
    base = {
        "type": "transaction",
        "fields": {
            "external_ref": "invoice1",
            "amount_minor": 1000,
            "effective_date": "2026-10-10",
            "kind": "charge",
            "category": "expense",
        },
    }
    paid = {**base, "fields": {**base["fields"], "kind": "payment"}}
    assert not hard_keys(state, base) & hard_keys(state, paid)


def test_exact_coverage_accreditation_status_ranking_prices_and_stale_warning():
    store = Store()
    graph = GraphService(store)
    prop = property_entity(graph)
    directory = ProviderService(store)
    safe = provider(
        directory,
        name="Safe Gas",
        trades=["heating/gas"],
        status="preferred",
        accreditations=[
            {
                "scheme": "Gas Safe",
                "number": "123",
                "expires_on": (date.today() + timedelta(days=30)).isoformat(),
            }
        ],
    )
    provider(
        directory,
        name="Expired Gas",
        trades=["heating/gas"],
        accreditations=[{"scheme": "Gas Safe", "number": "124", "expires_on": "2020-01-01"}],
    )
    provider(directory, name="Suspended", trades=["heating/gas"], status="suspended")
    provider(directory, name="Wrong District", postcode_districts=["N10"])
    price = directory.upsert_offering(
        {
            "name": "Boiler service",
            "trade": "heating/gas",
            "pricing_model": "fixed",
            "price_minor": 12000,
            "last_confirmed_at": "2020-01-01",
            "price_source": "website",
        },
        safe["id"],
    )
    results = directory.find_providers(
        trade="heating/gas", property_id=prop["id"], service="Boiler", urgency="emergency"
    )
    assert [item["id"] for item in results] == [safe["id"]]
    assert results[0]["matching_price_minor"] == 12000
    assert results[0]["offerings"][0]["price_stale"]
    assert price["id"] in {item["owner"] for item in store.snapshot()["embeddings"].values()}
    directory.set_provider_status(safe["id"], "do_not_use", "Unsafe work")
    assert not directory.find_providers(trade="heating/gas", postcode="N1 6SH")
    assert directory.find_providers(status="do_not_use")[0]["id"] == safe["id"]


def test_idempotent_existing_state_backfill_preserves_custom_types_and_links():
    store = Store()
    graph = GraphService(store)
    prop = property_entity(graph)
    company = graph.create_entity(
        {
            "type": "company",
            "name": "Original Contractor",
            "fields": {"type": "contractor", "trades": ["heating"]},
        }
    )
    ticket = graph.create_entity(
        {
            "type": "ticket",
            "name": "Boiler issue",
            "fields": {"location_detail": "24 Hoxton Street"},
        }
    )

    def legacy(state):
        state["entity_types"]["custom_type"] = {"id": "custom_type", "fields": {}, "version": 8}
        state["entity_types"]["ticket"]["fields"]["location"] = state["entity_types"]["ticket"][
            "fields"
        ].pop("location_detail")
        state["entities"][ticket["id"]]["fields"]["location"] = state["entities"][ticket["id"]][
            "fields"
        ].pop("location_detail")
        add_edge(state, ticket["id"], company["id"], "assigned_to")

    store.mutate(legacy)
    assert store.mutate(upgrade_addendum)
    snapshot = store.snapshot()
    assert not store.mutate(upgrade_addendum)
    assert store.snapshot()["version"] == snapshot["version"]
    assert snapshot["entity_types"]["custom_type"]["version"] == 8
    assert "location" not in snapshot["entities"][ticket["id"]]["fields"]
    edges = list(snapshot["edges"].values())
    assert any(
        edge["source"] == ticket["id"] and edge["target"] == prop["id"] and edge["relation"] == "at"
        for edge in edges
    )
    assert any(
        edge["source"] == ticket["id"]
        and edge["target"].startswith("service_provider:")
        and edge["relation"] == "assigned_to"
        for edge in edges
    )
    assert any(
        edge["target"] == company["id"] and edge["relation"] == "registered_as" for edge in edges
    )
    store.mutate(refresh_property_edges)


def test_accept_quote_is_atomic_expected_expense_and_no_money_moves():
    from propadmin_core.ledger import LedgerService

    store = Store()
    graph = GraphService(store)
    prop = property_entity(graph)
    ticket = graph.create_entity(
        {"type": "ticket", "name": "Leaking tap", "fields": {"category": "plumbing"}}
    )
    store.mutate(lambda state: add_edge(state, ticket["id"], prop["id"], "at"))
    directory = ProviderService(store)
    plumber = provider(directory)
    quote = directory.record_quote(
        plumber["id"], ticket["id"], {"ref": "Q123", "amount_minor": 15000, "scope": "Replace tap"}
    )
    accepted = directory.accept_quote(quote["id"])
    assert accepted["fields"]["status"] == "accepted"
    directory.accept_quote(quote["id"])
    state = store.snapshot()
    expenses = [item for item in state["entities"].values() if item["type"] == "transaction"]
    assert len(expenses) == 1
    assert expenses[0]["fields"]["kind"] == "charge"
    assert expenses[0]["fields"]["status"] == "expected"
    assert LedgerService(store).get_balances(prop["id"])["landlord_balance_minor"] == 0
    assert any(
        edge["source"] == ticket["id"]
        and edge["target"] == plumber["id"]
        and edge["relation"] == "assigned_to"
        for edge in state["edges"].values()
    )


def test_observed_provider_metrics_reversed_spend_and_optimistic_upsert():
    from propadmin_core.ledger import LedgerService
    from propadmin_core.provider_directory import refresh_metrics
    from propadmin_core.store import ConflictError

    store, directory = Store(), None
    graph = GraphService(store)
    directory = ProviderService(store)
    prop = property_entity(graph)
    plumber = provider(directory)
    same = provider(directory)
    assert same["id"] == plumber["id"]
    with pytest.raises(ConflictError, match="version"):
        directory.upsert_provider({"fields": {"phone_main": "+447700900333"}}, id=plumber["id"])
    ticket = graph.create_entity(
        {
            "type": "ticket",
            "name": "Resolved tap",
            "fields": {
                "status": "closed",
                "final_answer": "The tap was repaired in one visit.",
                "reasoning": "The synthetic completion record reports one visit and tenant feedback of 4/5.",
                "reported_at": "2026-10-10T10:00:00Z",
                "scheduled_visit_at": "2026-10-10T11:00:00Z",
                "first_visit_at": "2026-10-10T12:00:00Z",
                "visits_count": 1,
                "tenant_feedback_rating": 4,
            },
        }
    )
    store.mutate(lambda state: add_edge(state, ticket["id"], plumber["id"], "assigned_to"))
    store.mutate(refresh_metrics)
    fields = directory.get_provider(plumber["id"])["fields"]
    assert fields["jobs_completed"] == 1
    assert fields["avg_response_hours"] == 2
    assert fields["first_time_fix_rate"] == 1
    assert fields["rating"] == 4
    ledger = LedgerService(store)
    tx = ledger.record_transaction(
        {
            "property_id": prop["id"],
            "paid_to": plumber["id"],
            "fields": {
                "kind": "payment",
                "category": "expense",
                "amount_minor": 15000,
                "effective_date": "2026-10-10",
                "status": "cleared",
            },
        }
    )
    assert directory.get_provider(plumber["id"])["spend_minor"] == 15000
    ledger.reverse_transaction(tx["id"], "Wrong invoice recorded")
    assert directory.get_provider(plumber["id"])["spend_minor"] == 0
    assert directory.get_provider(plumber["id"])["fields"]["avg_job_cost_minor"] is None


def test_relationship_metadata_joint_ownership_and_fixed_schema_guards():
    from propadmin_core.ledger import LedgerService
    from propadmin_core.store import ConflictError

    store = Store()
    graph = GraphService(store)
    prop, other = property_entity(graph), property_entity(graph, ref="P2", address="Other Road")
    owners = [
        graph.create_entity({"type": "person", "name": name})
        for name in ("Owner A", "Owner B", "Tenant")
    ]
    first = graph.link_entities(
        {
            "source": owners[0]["id"],
            "target": prop["id"],
            "relation": "owns",
            "attributes": {"share_pct": 50},
        }
    )
    second = graph.link_entities(
        {
            "source": owners[1]["id"],
            "target": prop["id"],
            "relation": "owns",
            "attributes": {"share_pct": 50},
        }
    )
    assert first["share_pct"] == second["share_pct"] == 50
    with pytest.raises(ValueError, match="total"):
        graph.link_entities(
            {
                "source": owners[2]["id"],
                "target": prop["id"],
                "relation": "owns",
                "attributes": {"share_pct": 1},
            }
        )
    with pytest.raises(ValueError, match="endpoint"):
        graph.link_entities({"source": owners[0]["id"], "target": prop["id"], "relation": "at"})
    tenant = graph.link_entities(
        {
            "source": owners[2]["id"],
            "target": prop["id"],
            "relation": "tenant_of",
            "attributes": {
                "from": "2026-10-01",
                "to": "2027-09-30",
                "is_lead_tenant": True,
            },
        }
    )
    assert tenant["is_lead_tenant"]
    ticket = graph.create_entity({"type": "ticket", "name": "Tap issue"})
    graph.link_entities({"source": ticket["id"], "target": prop["id"], "relation": "at"})
    with pytest.raises(ConflictError, match="one property"):
        graph.link_entities({"source": ticket["id"], "target": other["id"], "relation": "at"})
    ledger = LedgerService(store)
    ledger.record_transaction(
        {
            "property_id": prop["id"],
            "fields": {
                "kind": "payment",
                "category": "landlord_contribution",
                "amount_minor": 10000,
                "effective_date": "2026-10-10",
                "status": "cleared",
            },
        }
    )
    assert ledger.get_balances(owners[0]["id"])["landlord_balance_minor"] == 5000
    schema = store.snapshot()["entity_types"]["property"]
    schema["fields"]["tenant_balance_minor"]["read_only"] = False
    with pytest.raises(ValueError, match="fixed"):
        graph.save_entity_type(schema)
    with pytest.raises(ValueError, match="safe integer"):
        graph.create_entity(
            {
                "type": "property",
                "name": "Big",
                "fields": {
                    "ref": "Big",
                    "address_line1": "Big Road",
                    "postcode": "N1 6SH",
                    "rent_amount_minor": 2**53,
                },
            }
        )


def test_recurring_issue_follows_property_not_identical_location_text():
    store, graph = Store(), None
    graph = GraphService(store)
    prop = property_entity(graph)
    other = property_entity(graph, ref="P2", address="Other Road")
    tickets = []
    for name, day, unit in (
        ("Original", "2026-09-01", prop),
        ("Returned", "2026-10-01", prop),
        ("Other unit", "2026-10-02", other),
    ):
        ticket = graph.create_entity(
            {
                "type": "ticket",
                "name": name,
                "description": "Kitchen sink leaking waste trap",
                "fields": {
                    "category": "plumbing",
                    "location_detail": "Kitchen",
                    "tags": ["sink-leak"],
                    "reported_at": day + "T10:00:00Z",
                },
            }
        )
        graph.link_entities({"source": ticket["id"], "target": unit["id"], "relation": "at"})
        tickets.append(ticket)
    store.mutate(refresh_property_edges)
    edges = [
        item for item in store.snapshot()["edges"].values() if item["relation"] == "recurring_issue"
    ]
    assert {(edge["source"], edge["target"]) for edge in edges} == {
        (tickets[1]["id"], tickets[0]["id"])
    }
    store.mutate(refresh_property_edges)
    assert (
        len(
            [
                edge
                for edge in store.snapshot()["edges"].values()
                if edge["relation"] == "recurring_issue"
            ]
        )
        == 1
    )
