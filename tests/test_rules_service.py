"""Rules service: internal auth, Pub/Sub incremental recompute, layout and compiler."""

import base64
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.layout import BOUND
from propadmin_runtime import create_app
from propadmin_runtime.config import Settings

# Every service names its package `app`; load by path to avoid collisions.
_spec = importlib.util.spec_from_file_location(
    "rules_routes", Path(__file__).parents[1] / "services/rules/app/routes.py"
)
routes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(routes)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PIPELINE_MODEL", raising=False)
    store = Store(None)
    app = create_app("rules", store=store, seed=True)
    app.include_router(routes.router)
    with TestClient(app) as instance:
        instance.headers["Authorization"] = f"Bearer {Settings().internal_token}"
        yield instance


def kinds_since(store, version):
    return [event["kind"] for event in store.snapshot()["events"] if event["version"] > version]


def test_internal_auth_required(client):
    for path in ("/internal/recompute", "/internal/events", "/internal/compile"):
        assert client.post(path, headers={"Authorization": "Bearer wrong"}).status_code == 403
        assert client.post(path, headers={"Authorization": ""}).status_code == 401


def test_pubsub_entity_event_recomputes_only_rules_touching_its_type(client):
    store = client.app.state.store
    state = store.snapshot()
    entity = next(e for e in state["entities"].values() if e["type"] == "ticket")
    touching = {
        key
        for key, rule in state["rules"].items()
        if rule.get("enabled", True) and "ticket" in (rule["source_type"], rule["target_type"])
    }
    assert touching and touching != {k for k, r in state["rules"].items() if r.get("enabled", 1)}
    data = base64.b64encode(
        json.dumps({"kind": "entity.changed", "entity_id": entity["id"]}).encode()
    )
    response = client.post("/internal/events", json={"message": {"data": data.decode()}})
    assert response.status_code == 200
    assert set(response.json()["rules"]) == touching
    assert kinds_since(store, state["version"])[-1] == "layout.updated"

    rule_id = next(iter(touching))
    response = client.post("/internal/events", json={"kind": "rule.changed", "rule_id": rule_id})
    assert list(response.json()["rules"]) == [rule_id]
    assert client.post("/internal/events", json={"kind": "nope"}).status_code == 422


def test_full_recompute_layout_within_bounds_and_stable(client):
    store = client.app.state.store
    assert client.post("/internal/recompute").status_code == 200
    first = {k: (e["layout_x"], e["layout_y"]) for k, e in store.snapshot()["entities"].items()}
    assert all(abs(x) <= BOUND and abs(y) <= BOUND for x, y in first.values())
    assert len(set(first.values())) == len(first)

    client.post("/internal/recompute")
    second = {k: (e["layout_x"], e["layout_y"]) for k, e in store.snapshot()["entities"].items()}
    drift = max(abs(a - c) + abs(b - d) for (a, b), (c, d) in zip(first.values(), second.values()))
    assert drift < BOUND * 0.05


def test_compile_unconfigured_returns_503(client):
    response = client.post("/internal/compile", json={"prompt": "link landlords to their agents"})
    assert response.status_code == 503
