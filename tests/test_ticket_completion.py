"""Completion invariants, persistent backfill and authenticated Markdown exports."""

import copy

import pytest
from fastapi.testclient import TestClient
from propadmin_core import GraphService, Store, seed_demo
from propadmin_core.addendum_upgrade import upgrade_addendum
from propadmin_runtime import create_app
from propadmin_runtime.auth import issue_token


@pytest.fixture
def client():
    with TestClient(create_app(store=Store(), seed=False)) as client:
        client.headers["Authorization"] = f"Bearer {issue_token(client.app.state.settings)}"
        yield client


@pytest.mark.parametrize("status", ["resolved", "closed"])
def test_completion_is_atomic_requires_both_fields_and_keeps_full_markdown(client, status):
    payload = {"type": "ticket", "name": "Query result", "fields": {"status": status}}
    assert client.post("/v1/entities", json=payload).status_code == 422
    ticket = client.post("/v1/entities", json={
        **payload, "fields": {"status": "reported"},
    }).json()
    path = f"/v1/entities/{ticket['id']}"
    ticket = client.get(path).json()
    assert ticket["fields"]["final_answer"] == ticket["fields"]["reasoning"] == ""
    answer = "# Result\n\nThe query returned **£95**. No payment was executed."
    reasoning = "# Evidence\n\n" + "- Queried the recorded cost: £95; payment unavailable.\n" * 2500
    reasoning = reasoning.strip()
    for fields in (
        {"status": status},
        {"status": status, "final_answer": answer},
        {"status": status, "reasoning": reasoning},
        {"status": status, "final_answer": answer, "reasoning": " \n "},
    ):
        failed = client.patch(path, json={"version": ticket["version"], "fields": fields})
        assert failed.status_code == 422
        assert client.get(path).json() == ticket
    completed = client.patch(path, json={"version": ticket["version"], "fields": {
        "status": status, "final_answer": answer, "reasoning": reasoning,
    }}).json()
    assert completed["version"] == ticket["version"] + 1
    for filename, content in (("answer.md", answer), ("reasoning.md", reasoning)):
        export = client.get(f"/v1/tickets/{ticket['id']}/exports/{filename}")
        assert export.status_code == 200
        assert export.headers["content-type"] == "text/markdown; charset=utf-8"
        assert export.headers["content-disposition"] == f'attachment; filename="{filename}"'
        assert export.headers["cache-control"] == "no-store"
        assert export.text == content + "\n"
    embeddings = client.app.state.store.snapshot()["embeddings"].values()
    assert {item["field"] for item in embeddings if item["owner"] == ticket["id"]} >= {
        "final_answer", "reasoning",
    }
    assert client.patch(path, json={"version": completed["version"], "fields": {
        "reasoning": "",
    }}).status_code == 422
    assert client.patch(path, json={"version": ticket["version"], "fields": {
        "status": status, "final_answer": answer, "reasoning": reasoning,
    }}).status_code == 409
    assert client.patch(path, json={"version": completed["version"], "fields": {
        "status": "reported",
    }}).status_code == 200
    assert client.get(f"/v1/tickets/{ticket['id']}/exports/answer.md").status_code == 409


def test_exports_reject_anonymous_incomplete_non_ticket_and_unknown_files(client):
    ticket = client.post("/v1/entities", json={"type": "ticket", "name": "Open"}).json()
    person = client.post("/v1/entities", json={"type": "person", "name": "Tenant"}).json()
    base = "/v1/tickets/"
    assert client.get(base + ticket["id"] + "/exports/answer.md").status_code == 409
    assert client.get(base + person["id"] + "/exports/answer.md").status_code == 404
    assert client.get(base + "ticket:missing/exports/answer.md").status_code == 404
    assert client.get(base + ticket["id"] + "/exports/other.md").status_code == 422
    assert client.get(base + ticket["id"] + "/exports/answer.md", headers={
        "Authorization": "Bearer invalid",
    }).status_code == 401
    definition = client.app.state.store.snapshot()["entity_types"]["ticket"]
    definition["fields"].pop("reasoning")
    assert client.patch("/v1/entity-types", json=definition).status_code == 422


def test_historical_backfill_is_durable_honest_and_idempotent(tmp_path):
    store = Store(tmp_path / "state.json")
    seed_demo(store)
    graph = GraphService(store)
    preserved = graph.create_entity({"type": "ticket", "name": "Already documented", "fields": {
        "status": "closed", "final_answer": "No action: unavailable service.",
        "reasoning": "The recorded service error prevented execution.",
    }})

    def legacy(state):
        for key in ("final_answer", "reasoning"):
            state["entity_types"]["ticket"]["fields"].pop(key)
            for id in ("ticket:prop-1036", "ticket:prop-1042"):
                state["entities"][id]["fields"].pop(key)
        state["entities"]["ticket:prop-1042"]["fields"]["status"] = "closed"
        state["entity_types"]["ticket"]["fields"]["custom"] = {
            "type": "text", "embed": True, "required": False, "unique_key": False,
        }

    store.mutate(legacy)
    assert store.mutate(upgrade_addendum)
    reopened = Store(store.path).snapshot()
    repaired = reopened["entities"]["ticket:prop-1036"]["fields"]
    assert repaired["final_answer"] == repaired["resolution"]
    assert "were not recorded" in repaired["reasoning"]
    unknown = reopened["entities"]["ticket:prop-1042"]["fields"]
    assert "cannot be established" in unknown["final_answer"]
    assert "custom" in reopened["entity_types"]["ticket"]["fields"]
    assert reopened["entities"][preserved["id"]] == preserved
    snapshot = copy.deepcopy(reopened)
    assert not store.mutate(upgrade_addendum)
    repeated = Store(store.path).snapshot()
    # The existing addendum separately refreshes derived edge timestamps on startup.
    for key in ("entities", "entity_types", "embeddings", "changes", "events", "version"):
        assert repeated[key] == snapshot[key]
