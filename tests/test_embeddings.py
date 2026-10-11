"""Semantic migration preserves a live index and rejects vectors for changed sources."""

from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.embeddings import EmbeddingService
from propadmin_runtime import create_app
from propadmin_runtime import routes_embeddings as migration


def test_reindex_preserves_old_space_skips_workflows_and_is_resumable(monkeypatch):
    store = Store()
    embedder = EmbeddingService()
    store.mutate(lambda s: embedder.upsert(s, "person:test", "description", "boiler repair"))
    store.mutate(lambda s: s["embeddings"].update(workflow={
        "owner": "workflow:test", "field": "context", "index": "triplets", "model": "local",
        "text_hash": "workflow-hash", "text": "workflow", "vector": [0.1],
    }))

    class Provider:
        def embed(self, text):
            return [0.25, 0.75]

    monkeypatch.setattr(migration, "target_provider", lambda: (Provider(), "vertex:test:2"))
    with TestClient(create_app(store=store, seed=False)) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.post("/v1/embeddings/reindex", json={}).status_code == 401
        token = client.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        client.headers["Authorization"] = f"Bearer {token}"
        assert client.get("/v1/embeddings/status").json()["remaining"] == 1
        result = client.post("/v1/embeddings/reindex", json={"limit": 1})
        assert result.status_code == 200 and result.json()["complete"]
        assert result.json()["written"] == 1
        assert client.post("/v1/embeddings/reindex", json={}).json()["written"] == 0
    entries = list(store.snapshot()["embeddings"].values())
    assert {e["model"] for e in entries} == {"local-deterministic-hash-v1", "vertex:test:2", "local"}
    # A later live source edit invalidates the staged vector; it must be regenerated.
    store.mutate(lambda s: embedder.upsert(s, "person:test", "description", "hot water failure"))
    assert len(migration.pending(store.snapshot(), "vertex:test:2")[1]) == 1
    assert not any(e["model"] == "vertex:test:2" for e in store.snapshot()["embeddings"].values())


def test_removed_field_clears_both_provider_spaces(monkeypatch):
    from propadmin_core import GraphService
    from propadmin_core.embeddings import embedding_key

    store = Store()
    graph = GraphService(store)
    person = graph.create_entity({"type": "person", "name": "Migration test",
                                  "description": "Before removal"})

    def stage(state):
        entry = next(e for e in state["embeddings"].values() if e["owner"] == person["id"])
        key = embedding_key(person["id"], "description", "vertex:test:2")
        state["embeddings"][key] = {**entry, "id": key, "model": "vertex:test:2", "vector": [0.5, 0.5]}

    store.mutate(stage)
    graph.update_entity(person["id"], {"version": person["version"], "description": ""})
    assert not any(e["owner"] == person["id"] for e in store.snapshot()["embeddings"].values())


def test_source_edit_during_embedding_does_not_commit_stale_vector(monkeypatch):
    store = Store()
    embedder = EmbeddingService()
    store.mutate(lambda s: embedder.upsert(s, "person:test", "description", "before"))

    class Provider:
        def embed(self, text):
            store.mutate(lambda s: embedder.upsert(s, "person:test", "description", "after"))
            return [0.25, 0.75]

    monkeypatch.setattr(migration, "target_provider", lambda: (Provider(), "vertex:test:2"))
    with TestClient(create_app(store=store, seed=False)) as client:
        token = client.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        client.headers["Authorization"] = f"Bearer {token}"
        result = client.post("/v1/embeddings/reindex", json={}).json()
        assert result["written"] == 0 and result["remaining"] == 1
    assert not any(e["model"] == "vertex:test:2" for e in store.snapshot()["embeddings"].values())
