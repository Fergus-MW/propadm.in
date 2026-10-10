"""Three cross-layer scenarios for Addendum A's HTTP and one-MCP contracts."""

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.graph import add_edge
from propadmin_runtime.auth import issue_token
from propadmin_runtime.config import Settings
from propadmin_runtime.factory import create_app


@pytest.fixture
def app_client():
    store, settings = Store(), Settings()
    app = create_app(store=store, settings=settings, seed=False)
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {issue_token(settings)}"
        yield client, app, store


def make_property(app, ref="P1"):
    return app.state.graph.create_entity(
        {
            "type": "property",
            "name": ref,
            "fields": {
                "ref": ref,
                "address_line1": ref + " Hoxton Street",
                "postcode": "N1 6SH",
                "management_fee_pct": 10,
            },
        }
    )


def write_transaction(client, property_id, kind, category, amount, **fields):
    return client.post(
        "/v1/transactions",
        json={
            "property_id": property_id,
            "fields": {
                "kind": kind,
                "category": category,
                "amount_minor": amount,
                "effective_date": "2026-10-10",
                "status": "cleared",
                **fields,
            },
        },
    )


def test_ledger_http_auth_status_and_generic_write_boundaries(app_client):
    client, app, store = app_client
    prop = make_property(app)
    assert (
        client.get("/v1/properties", headers={"Authorization": "Bearer invalid"}).status_code == 401
    )
    assert client.get("/v1/properties").json()["items"][0]["id"] == prop["id"]
    due = write_transaction(client, prop["id"], "charge", "rent_due", 100000)
    assert due.status_code == 201
    pending = write_transaction(
        client, prop["id"], "payment", "rent_received", 100000, status="pending"
    )
    assert pending.status_code == 201
    tx = pending.json()
    assert (
        client.get(f"/v1/properties/{prop['id']}/balances").json()["tenant_balance_minor"] == 100000
    )
    promoted = client.post(
        f"/v1/transactions/{tx['id']}/status",
        json={"status": "cleared", "reason": "Bank confirmed"},
    )
    assert promoted.status_code == 200
    balances = client.get(f"/v1/properties/{prop['id']}/balances").json()
    assert balances["tenant_balance_minor"] == 0 and balances["landlord_balance_minor"] == 90000
    assert (
        client.patch(
            f"/v1/entities/{prop['id']}",
            json={
                "version": app.state.graph.get_entity(prop["id"])["version"],
                "fields": {"tenant_balance_minor": 999},
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/entities", json={"type": "transaction", "name": "Bypass", "fields": tx["fields"]}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/v1/entities/{tx['id']}",
            json={"version": tx["version"], "fields": {"amount_minor": 1}},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/v1/transactions/{tx['id']}/status", json={"status": "pending", "reason": "Backwards"}
        ).status_code
        == 422
    )
    result = client.post(
        f"/v1/transactions/{tx['id']}/reverse", json={"reason": "Incorrect payment"}
    )
    assert result.status_code == 201
    assert (
        client.get(f"/v1/properties/{prop['id']}/balances").json()["tenant_balance_minor"] == 100000
    )
    assert app.state.graph.get_entity(tx["id"])["fields"]["amount_minor"] == 100000


def test_provider_quotes_and_property_scoped_graph_http_contract(app_client):
    client, app, store = app_client
    prop, other = make_property(app), make_property(app, "P2")
    ticket = app.state.graph.create_entity(
        {"type": "ticket", "name": "Tap leak", "fields": {"category": "plumbing"}}
    )
    store.mutate(lambda state: add_edge(state, ticket["id"], prop["id"], "at"))
    payload = {
        "type": "service_provider",
        "name": "N1 Plumbing",
        "fields": {
            "ref": "SP1",
            "trading_name": "N1 Plumbing",
            "trades": ["plumbing"],
            "postcode_districts": ["N1"],
            "status": "approved",
            "emergency_callout": True,
        },
    }
    response = client.post("/v1/providers", json=payload)
    assert response.status_code == 201
    provider = response.json()
    assert client.post("/v1/providers", json=payload).json()["id"] == provider["id"]
    assert (
        client.patch(
            f"/v1/providers/{provider['id']}", json={"version": 99, "description": "Stale"}
        ).status_code
        == 409
    )
    offering = client.post(
        f"/v1/providers/{provider['id']}/offerings",
        json={
            "fields": {
                "name": "Tap repair",
                "trade": "plumbing",
                "price_minor": 12000,
                "pricing_model": "fixed",
                "last_confirmed_at": "2026-10-10",
                "price_source": "admin",
            }
        },
    )
    assert offering.status_code == 201
    found = client.get(
        "/v1/providers", params={"trade": "plumbing", "property_id": prop["id"], "service": "Tap"}
    ).json()["items"]
    assert found[0]["id"] == provider["id"] and found[0]["matching_price_minor"] == 12000
    quote = client.post(
        "/v1/quotes",
        json={
            "provider_id": provider["id"],
            "ticket_id": ticket["id"],
            "fields": {"amount_minor": 12000, "scope": "Replace tap", "ref": "Q1"},
        },
    )
    assert quote.status_code == 201
    accepted = client.post(f"/v1/quotes/{quote.json()['id']}/accept")
    assert accepted.status_code == 200 and accepted.json()["fields"]["status"] == "accepted"
    assert client.get(f"/v1/properties/{prop['id']}/balances").json()["landlord_balance_minor"] == 0
    another = write_transaction(client, other["id"], "charge", "rent_due", 50000).json()
    assert all(
        node["type"] != "transaction" for node in client.get("/v1/entities/graph").json()["nodes"]
    )
    focused = client.get(
        "/v1/entities/graph", params={"include_transactions": True, "property_id": prop["id"]}
    ).json()["nodes"]
    transactions = [node for node in focused if node["type"] == "transaction"]
    assert len(transactions) == 1 and another["id"] not in {node["id"] for node in focused}
    assert (
        client.get(f"/v1/providers/{provider['id']}").json()["quotes"][0]["id"]
        == quote.json()["id"]
    )


def test_single_mcp_discovery_ledger_audit_and_internal_rent_auth(app_client):
    client, app, store = app_client
    prop = make_property(app)
    minted = client.post("/v1/mcp/tokens", json={"session_id": "ledger-contract"})
    assert minted.status_code == 201
    headers = {
        "Authorization": "Bearer " + minted.json()["token"],
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }

    def rpc(method, params=None):
        response = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        )
        assert response.status_code == 200
        return response.json()["result"]

    rpc("initialize", {"protocolVersion": "2025-11-25"})
    names = [tool["name"] for tool in rpc("tools/list")["tools"]]
    assert len(names) == len(set(names))
    assert {
        "get_property",
        "get_ledger",
        "record_transaction",
        "reverse_transaction",
        "find_providers",
        "accept_quote",
        "generate_statement",
    } <= set(names)
    result = rpc(
        "tools/call",
        {
            "name": "record_transaction",
            "arguments": {
                "property_id": prop["id"],
                "fields": {
                    "kind": "charge",
                    "category": "rent_due",
                    "amount_minor": 100,
                    "effective_date": "2026-10-10",
                    "status": "expected",
                },
            },
        },
    )
    assert not result["isError"]
    balance = rpc("tools/call", {"name": "get_balances", "arguments": {"subject": prop["id"]}})
    assert balance["structuredContent"]["tenant_balance_minor"] == 100
    tx_id = result["structuredContent"]["id"]
    edge = next(
        item
        for item in store.snapshot()["edges"].values()
        if item["source"] == tx_id and item["relation"] == "for"
    )
    denied = rpc(
        "tools/call",
        {
            "name": "unlink_entities",
            "arguments": {"id": edge["id"], "reason": "Attempt ledger bypass"},
        },
    )
    assert denied["isError"]
    assert edge["id"] in store.snapshot()["edges"]
    actions = [item for item in store.snapshot()["actions"].values() if item["kind"] == "mcp.tool"]
    assert len(actions) == 3 and all(
        item["actor"] == "agent_run:ledger-contract" for item in actions
    )
    assert minted.json()["token"] not in str(store.snapshot())
    for number in (1, 2):
        app.state.ingestion.ingest({
            "filename": f"ambiguous-{number}.txt", "source_type": "receipt",
            "text": f"Receipt: UNKNOWN-{number}\nDate: 2026-10-10\nAmount: £2.00\nTenant: Alice\n",
        })
    queued = client.get("/v1/ledger/unallocated").json()["items"]
    assert len(queued) == 2 and all(row["needs_classification"] for row in queued)
    path = f"/v1/transactions/{queued[0]['id']}/allocate"
    assert client.post(path, json={"property_id": prop["id"]}).status_code == 422
    classified = client.post(path, json={"property_id": prop["id"],
                                         "category": "deposit_received", "kind": "payment"})
    assert classified.status_code == 200 and classified.json()["fields"]["category"] == "deposit_received"
    classified = rpc("tools/call", {"name": "allocate", "arguments": {
        "tx": queued[1]["id"], "property": prop["id"],
        "category": "landlord_contribution", "kind": "payment",
    }})
    assert not classified["isError"]
    assert classified["structuredContent"]["fields"]["category"] == "landlord_contribution"
    assert client.get("/v1/ledger/unallocated").json()["items"] == []
    assert app.state.ledger.get_balances(prop["id"])["deposit_held_minor"] == 0  # Pending receipt.
    rules = create_app("rules", store=store, seed=False)
    with TestClient(rules) as worker:
        assert worker.post("/mcp", headers=headers, json={}).status_code == 404
        assert worker.post("/internal/rent-schedule").status_code == 401
        response = worker.post(
            "/internal/rent-schedule",
            headers={"Authorization": "Bearer " + rules.state.settings.internal_token},
        )
        assert response.status_code == 200 and response.json()["count"] == 0
