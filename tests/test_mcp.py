"""Focused contract checks for the one graph MCP gateway and its write boundaries."""

import json

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime.auth import issue_token
from propadmin_runtime.config import Settings
from propadmin_runtime.factory import create_app


@pytest.fixture
def gateway():
    store, settings = Store(), Settings()
    with TestClient(create_app(store=store, settings=settings, seed=False)) as client:
        admin = {"Authorization": f"Bearer {issue_token(settings)}"}
        response = client.post("/v1/mcp/tokens", json={"session_id": "test-session"}, headers=admin)
        assert response.status_code == 201
        token = response.json()["token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25",
        }
        yield client, store, admin, headers, token


def rpc(client, headers, method="tools/call", params=None, **kwargs):
    return client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params or {},
    }, headers=headers, **kwargs)


def call(client, headers, name, arguments):
    return rpc(client, headers, params={"name": name, "arguments": arguments}).json()["result"]


def test_single_gateway_protocol_and_inline_tool_contract(gateway):
    client, store, admin, headers, _ = gateway
    assert rpc(client, {}).status_code == 401
    assert rpc(client, {**headers, **admin}).status_code == 403
    initialized = rpc(client, headers, "initialize", {"protocolVersion": "2025-11-25"}).json()
    assert initialized["result"]["serverInfo"]["name"] == "propadmin-graph"
    response = client.post("/mcp", json={
        "jsonrpc": "2.0", "method": "notifications/initialized",
    }, headers=headers)
    assert response.status_code == 202 and response.content == b""
    assert client.get("/mcp", headers=headers).status_code == 405
    tools = rpc(client, headers, "tools/list").json()["result"]["tools"]
    assert {t["name"] for t in tools} >= {
        "search", "get_entity", "traverse", "get_document", "query_graph", "upsert_entity",
        "update_entity", "link_entities", "unlink_entities", "merge_entities", "add_note",
        "send_email", "reply_email", "place_call", "browser_open", "browser_login",
        "create_plan", "update_step", "sleep", "propose_skill_change",
    }
    assert "$ref" not in json.dumps(tools)
    for item in tools:
        schema = item["inputSchema"]
        assert schema["type"] == "object"
        assert not {"oneOf", "anyOf", "allOf"} & schema.keys()
    denied = call(client, headers, "query_graph", {"query": "DELETE person"})
    assert denied["isError"] and denied["structuredContent"]["error"]["code"] == "unavailable"
    assert not store.snapshot()["entities"]
    assert rpc(client, headers, params={"name": ["bad"]}).status_code == 400
    assert rpc(client, headers, "unknown").status_code == 404
    assert rpc(client, {**headers, "Origin": "https://other.example"}).status_code == 403
    assert rpc(client, {**headers, "Accept": "application/json"}).status_code == 406
    malformed = client.post("/mcp", content="{", headers={**headers, "Content-Type": "application/json"})
    assert malformed.json()["error"]["code"] == -32700


def test_modern_discovery_header_validation_and_direct_tools(gateway):
    client, _, _, legacy_headers, _ = gateway
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}
    headers = {**legacy_headers, "MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "server/discover"}
    discovered = rpc(client, headers, "server/discover", {"_meta": meta}).json()["result"]
    assert discovered["resultType"] == "complete"
    assert discovered["supportedVersions"] == ["2026-07-28", "2025-11-25"]
    mismatch = rpc(client, headers, "tools/list", {"_meta": meta})
    assert mismatch.status_code == 400 and mismatch.json()["error"]["code"] == -32020
    unsupported = rpc(client, {**headers, "MCP-Protocol-Version": "1900-01-01"})
    assert unsupported.json()["error"]["data"]["supported"] == discovered["supportedVersions"]
    response = rpc(client, {**headers, "Mcp-Method": "tools/call", "Mcp-Name": "search"}, params={
        "name": "search", "arguments": {"query": "plumber"}, "_meta": meta,
    })
    assert response.status_code == 200 and response.json()["result"]["isError"] is False
    missing_meta = rpc(client, {**headers, "Mcp-Method": "tools/list"}, "tools/list")
    assert missing_meta.json()["error"]["code"] == -32020


def test_agent_ticket_completion_requires_answer_and_evidence_explanation(gateway):
    client, store, _, headers, _ = gateway
    result = call(client, headers, "upsert_entity", {
        "type": "ticket", "id": "ticket:query", "name": "Query", "reason": "Operator request",
    })
    assert not result["isError"]
    update = {"id": "ticket:query", "version": 1, "reason": "Query finished"}
    denied = call(client, headers, "update_entity", {
        **update, "fields": {"status": "resolved", "final_answer": "No matching records."},
    })
    assert denied["isError"] and "reasoning" in denied["content"][0]["text"]
    assert store.snapshot()["entities"]["ticket:query"]["version"] == 1
    completed = call(client, headers, "update_entity", {**update, "fields": {
        "status": "resolved", "final_answer": "No matching records.",
        "reasoning": "Searched the graph for the supplied identifier; the result was empty.",
    }})
    assert not completed["isError"]
    assert completed["structuredContent"]["fields"]["status"] == "resolved"


def test_mutations_conflicts_protection_audit_and_revocation(gateway):
    client, store, admin, headers, token = gateway
    def invoke(tool_name, **arguments):
        arguments.setdefault("reason", "Maintenance follow-up")
        return call(client, headers, tool_name, arguments)

    created = invoke("upsert_entity", id="person:test", type="person", name="Test tenant")
    assert not created["isError"]
    result = invoke("update_entity", id="person:test", version=1, description="Needs plumber")
    assert result["structuredContent"]["version"] == 2
    stale = invoke("update_entity", id="person:test", version=1, description="Stale update")
    assert stale["structuredContent"]["error"]["code"] == "conflict"
    note = invoke("add_note", id="person:test", version=2, note="Access after 4pm")
    assert note["structuredContent"]["fields"]["notes"] == ["Access after 4pm"]
    assert any(item["owner"] == "person:test" for item in store.snapshot()["embeddings"].values())
    invoke("upsert_entity", id="person:duplicate", type="person", name="Duplicate tenant")
    linked = invoke("link_entities", source="person:test", target="person:duplicate", relation="knows")
    edge_id = linked["structuredContent"]["id"]
    assert invoke("unlink_entities", id=edge_id)["structuredContent"]["deleted"]
    store.mutate(lambda state: state["edges"].update({"edge:rule": {
        "id": "edge:rule", "source": "person:test", "target": "person:duplicate",
        "relation": "related", "rule": "rule:test",
    }}))
    protected = invoke("unlink_entities", id="edge:rule")
    assert protected["isError"] and "Rule-generated" in protected["content"][0]["text"]
    denied = invoke("upsert_entity", type="skill", name="Live skill")
    assert denied["isError"]
    stale_merge = invoke("merge_entities", id="person:duplicate", target_id="person:test",
                         version=1, target_version=1)
    assert stale_merge["structuredContent"]["error"]["code"] == "conflict"
    merged = invoke("merge_entities", id="person:duplicate", target_id="person:test",
                    version=1, target_version=3)
    assert merged["structuredContent"]["version"] == 4
    state = store.snapshot()
    actions = [a for a in state["actions"].values() if a["kind"] == "mcp.tool"]
    assert len(actions) == 11
    assert {a["status"] for a in actions} == {"completed", "failed"}
    assert all(a["actor"] == "agent_run:test-session" and a["reason"] for a in actions)
    changes = [c for c in state["changes"].values() if c["action"] == "entity.updated"]
    assert changes[0]["before"]["description"] == ""
    assert changes[0]["after"]["description"] == "Needs plumber"
    assert token not in json.dumps(state)
    assert client.get("/v1/mcp/tokens", headers=headers).status_code == 403
    assert "token" not in client.get("/v1/mcp/tokens", headers=admin).json()["items"][0]
    assert client.post("/v1/mcp/tokens", json={"session_id": "test-session"}, headers=admin).status_code == 409
    assert client.delete("/v1/mcp/tokens/test-session", headers=admin).status_code == 200
    assert rpc(client, headers, "tools/list").status_code == 403
    assert client.post("/v1/mcp/tokens", json={"session_id": "test-session"}, headers=admin).status_code == 409
    expired = issue_token(client.app.state.settings, "agent_run:test-session", -1)
    assert rpc(client, {**headers, "Authorization": f"Bearer {expired}"}).status_code == 401


def test_admin_scope_adds_admin_api_and_lifts_skill_protection(gateway):
    client, store, admin, headers, _ = gateway
    names = lambda: {t["name"] for t in rpc(client, headers, "tools/list").json()["result"]["tools"]}  # noqa: E731
    assert "admin_api" not in names()
    assert rpc(client, headers, params={
        "name": "admin_api", "arguments": {"method": "GET", "path": "/v1/overview"},
    }).json()["error"]["code"] == -32602

    store.mutate(lambda state: state["mcp_sessions"]["test-session"].update(scope="admin"))
    assert names() >= {"admin_api", "list_admin_endpoints", "send_email", "upsert_entity"}
    paths = {e["path"] for e in call(client, headers, "list_admin_endpoints", {})["structuredContent"]["items"]}
    assert "/v1/entity-types" in paths and not any(p.startswith("/v1/mcp/tokens") for p in paths)

    read = call(client, headers, "admin_api", {"method": "GET", "path": "/v1/entity-types"})
    assert not read["isError"] and read["structuredContent"]["status"] == 200
    entity = {"type": "person", "name": "Admin made"}
    unreasoned = call(client, headers, "admin_api", {"method": "POST", "path": "/v1/entities", "body": entity})
    assert unreasoned["isError"] and "reason" in unreasoned["structuredContent"]["error"]["message"]
    created = call(client, headers, "admin_api", {
        "method": "POST", "path": "/v1/entities", "body": entity, "reason": "Admin asked",
    })
    assert created["structuredContent"]["status"] == 201
    for path in ("/v1/mcp/tokens", "/v1/entities/graph/stream", "/v1/admin-chat"):
        blocked = call(client, headers, "admin_api", {"method": "GET", "path": path})
        assert blocked["isError"]
    skill = call(client, headers, "upsert_entity", {"type": "skill", "name": "Live skill", "reason": "Admin edit"})
    assert not skill["isError"]
