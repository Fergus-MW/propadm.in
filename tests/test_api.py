"""A few end-to-end API scenarios exercise boundaries the domain tests do not."""

import json
import struct

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store, publish
from propadmin_runtime import create_app
from propadmin_runtime.config import Settings
from propadmin_runtime.routes_graph import event_batch


@pytest.fixture
def client():
    with TestClient(create_app(store=Store())) as instance:
        token = instance.post("/v1/auth/login", json={"password": "propadmin-local"}).json()[
            "token"
        ]
        instance.headers["Authorization"] = f"Bearer {token}"
        yield instance


def test_authentication_typed_updates_conflicts_and_undo(client):
    assert client.post("/v1/auth/login", json={"password": "incorrect"}).status_code == 401
    assert (
        client.get("/v1/entities", headers={"Authorization": "Bearer invalid"}).status_code == 401
    )
    entity = client.post(
        "/v1/entities",
        json={
            "type": "person",
            "name": "Test Resident",
            "fields": {"emails": ["resident@example.test"], "roles": ["tenant"]},
        },
    ).json()
    update = client.patch(
        f"/v1/entities/{entity['id']}",
        json={"version": 1, "description": "Prefers visits after 5pm"},
    )
    assert update.status_code == 200
    assert update.json()["version"] == 2
    assert (
        client.patch(
            f"/v1/entities/{entity['id']}", json={"version": 1, "description": "Stale edit"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/v1/entities/{entity['id']}", json={"version": 2, "fields": {"unknown": "field"}}
        ).status_code
        == 422
    )
    action = next(
        a
        for a in client.get("/v1/actions").json()["items"]
        if a.get("entity_id") == entity["id"] and a.get("kind") == "entity.updated"
    )
    undo = client.post(f"/v1/actions/{action['id']}/undo")
    assert undo.status_code == 200
    assert undo.json()["description"] == ""
    assert client.post(f"/v1/actions/{action['id']}/undo").status_code == 409


def test_ingestion_search_sources_rules_and_generated_edges(client):
    upload = {
        "filename": "visit.md",
        "text": "Resident resident@example.test reported a boiler problem. Hot water is unavailable.",
        "mime": "text/markdown",
    }
    job = client.post("/v1/ingest/upload", json=upload)
    assert job.status_code == 201
    document = client.get("/v1/documents/" + job.json()["document_id"]).json()
    assert document["chunks"] and document["text"] == upload["text"]
    assert client.post("/v1/ingest/upload", json=upload).json()["document_id"] == document["id"]
    results = client.post("/v1/search", json={"query": "boiler hot water", "limit": 10}).json()[
        "results"
    ]
    assert results and any(item.get("citations") for item in results)
    rule = client.get("/v1/edge-rules").json()["items"][0]
    preview = client.post(f"/v1/edge-rules/{rule['id']}/preview")
    assert preview.status_code == 200 and "samples" in preview.json()
    recompute = client.post(f"/v1/edge-rules/{rule['id']}/recompute")
    assert recompute.status_code == 200 and recompute.json()["count"] >= 0
    edited = {
        k: v
        for k, v in rule.items()
        if k
        in {
            "id",
            "name",
            "relation",
            "source_type",
            "target_type",
            "kind",
            "params",
            "enabled",
            "version",
            "prompt",
        }
    }
    edited["enabled"] = not edited["enabled"]
    assert client.patch(f"/v1/edge-rules/{rule['id']}", json=edited).status_code == 200
    assert client.patch(f"/v1/edge-rules/{rule['id']}", json=edited).status_code == 409


def test_binary_snapshot_and_replay_cursor_preserve_graph(client):
    graph = client.get("/v1/entities/graph").json()
    binary = client.get("/v1/entities/graph.bin").content
    assert binary[:4] == b"PGR1"
    metadata_length, nodes, edges = struct.unpack("<III", binary[4:16])
    metadata = json.loads(binary[16 : 16 + metadata_length])
    assert nodes == len(graph["nodes"]) == len(metadata["nodes"])
    assert edges == len(metadata["edges"])
    assert len(binary) == 16 + metadata_length + nodes * 8 + edges * 8
    entity = graph["nodes"][0]
    focused = client.get("/v1/entities/graph.bin", params={"entity_id": entity["id"], "depth": 0})
    assert struct.unpack("<III", focused.content[4:16])[1] == 1
    assert client.get("/v1/entities/graph.bin", params={"depth": 99}).status_code == 422
    store = client.app.state.store
    version = store.snapshot()["version"]
    store.mutate(lambda state: publish(state, "node_updated", {"id": entity["id"]}))
    kind, batch = event_batch(store, version)
    assert kind == "delta" and len(batch["events"]) == 1
    assert event_batch(store, batch["version"])[1]["events"] == []
    assert event_batch(store, batch["version"] + 100)[0] == "reset"
    store.mutate(lambda state: state.update(events=state["events"][-1:]))
    assert event_batch(store, 0)[0] == "reset"


def test_ingestion_service_auth_and_persistence_across_services(tmp_path):
    path = tmp_path / "shared.json"
    api = create_app(store=Store(path), seed=False)
    ingestion = create_app("ingestion", store=Store(path), seed=False)
    with TestClient(api) as gateway, TestClient(ingestion) as worker:
        payload = {
            "filename": "source.md",
            "text": "A tenant needs a plumbing repair.",
            "mime": "text/markdown",
        }
        assert worker.post("/internal/events/land", json=payload).status_code == 401
        token = ingestion.state.settings.internal_token
        response = worker.post(
            "/internal/events/land", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        admin = gateway.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        documents = gateway.get(
            "/v1/documents", headers={"Authorization": f"Bearer {admin}"}
        ).json()["items"]
        assert documents[0]["id"] == response.json()["document_id"]
        assert (
            worker.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            ).status_code
            == 404
        )


def test_cloud_runtime_fails_explicitly_without_durable_repository():
    settings = Settings(
        mode="cloud", admin_password="password", token_secret="secret", internal_token="internal"
    )
    with pytest.raises(RuntimeError, match="Cloud mode needs a shared store"):
        create_app(settings=settings)
