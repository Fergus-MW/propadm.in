"""History provenance, future-information isolation and actual production-agent grading."""

import base64
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.workflow_corpus import WorkflowCorpus
from propadmin_core.workflow_parser import parse_case
from propadmin_core.workflow_replay import prepare_replay
from propadmin_runtime import create_app
from propadmin_runtime.auth import issue_token
from propadmin_runtime.config import Settings

from eval.workflows.__main__ import sources
from services.agent.app import managed


def source(path, text):
    raw = text.encode()
    return {"path": path, "mime": "text/markdown", "text": text,
            "content_base64": base64.b64encode(raw).decode(), "sha256": hashlib.sha256(raw).hexdigest()}


def fixture_sources(case_ref="001"):
    index = f"""# Case {case_ref}: Door repair

## Case details
- **Source role:** Tenant
- **Status:** Completed
- **Created:** 2026-01-01 10:00:00 UTC
- **Property:** Flat 1, 1 Example Road, London, ZZ1 1ZZ

## Initial request
Door won't close.

## Overview
FORBIDDEN_SUMMARY: the final repair succeeds.

## Outcome
FORBIDDEN_OUTCOME: lock replaced.

## Attachments
[report](attachments/report.md)
"""
    events = [("Note", "Agency / system", "Not specified", "Tenant reports door problem"),
              ("Email", "Northbridge Lettings", "Tenant", "EXPECTED_NEXT: ask tenant for a photo"),
              ("Email", "Tenant", "Northbridge Lettings", "FUTURE_REPLY: here is the photo [report](attachments/report.md)"),
              ("Update", "Agency / system", "Not specified", "FUTURE_COMPLETION: repair succeeded")]
    history = f"# Case {case_ref} history\n\nTotal events: 4\n\n"
    for ordinal, (channel, sender, recipient, body) in enumerate(events, 1):
        history += (f'<a id="event-{ordinal:03}"></a>\n'
                    f"## 2026-01-01 10:00:00 UTC — event {ordinal:03}\n\n"
                    f"- **Channel:** {channel}\n- **From:** {sender}\n- **To:** {recipient}\n\n{body}\n\n")
    return [source("index.md", index), source("history.md", history),
            source("attachments/report.md", "FORBIDDEN_FUTURE_ATTACHMENT: lock details")]


def corpus(store=None):
    store = store or Store()
    result = WorkflowCorpus(store).ingest("test", "001", fixture_sources())
    return store, result


def test_lossless_case_ingestion_and_replay_never_expose_the_answer():
    store, result = corpus()
    state = store.snapshot()
    assert result["events"] == 4 and result["transitions"] == 3
    assert WorkflowCorpus(store).ingest("test", "001", fixture_sources())["deduplicated"]
    events = sorted((e for e in state["entities"].values() if e["type"] == "workflow_event"),
                    key=lambda e: e["fields"]["ordinal"])
    assert len({e["fields"]["occurred_at"] for e in events}) == 1
    for event in events:
        span = event["evidence"][0]["span"]
        text = state["documents"][event["fields"]["source_document"]]["text"]
        assert text[span["start"]:span["end"]] == span["text"]
    transition = next(e for e in state["entities"].values()
                      if e["type"] == "workflow_transition" and e["fields"]["after_step"] == 1)
    replay = prepare_replay(state, transition["id"])
    assert "status" not in replay["state"]["entities"]["ticket:replay-case"]["fields"]
    assert "ref" not in replay["state"]["entities"]["ticket:replay-case"]["fields"]
    assert prepare_replay(state, transition["id"])["context_hash"] == replay["context_hash"]
    state["skills"]["skill:test-policy"] = {
        "id": "skill:test-policy", "slug": "test-policy", "current_version": 1,
    }
    assert prepare_replay(state, transition["id"])["context_hash"] != replay["context_hash"]
    exposed = json.dumps({"context": replay["context"], "state": replay["state"]})
    assert all(term not in exposed for term in ["EXPECTED_NEXT", "FORBIDDEN_SUMMARY", "FORBIDDEN_OUTCOME",
                                              "FUTURE_REPLY", "FUTURE_COMPLETION", "FORBIDDEN_FUTURE_ATTACHMENT"])
    assert "EXPECTED_NEXT" in replay["expected"]
    later = next(e for e in state["entities"].values()
                 if e["type"] == "workflow_transition" and e["fields"]["after_step"] == 3)
    assert "FORBIDDEN_FUTURE_ATTACHMENT" in prepare_replay(state, later["id"])["context"]
    observation = next(e for e in state["entities"].values()
                       if e["type"] == "workflow_transition" and e["fields"]["after_step"] == 2)
    with pytest.raises(ValueError, match="external observations"):
        prepare_replay(state, observation["id"])


def test_invalid_sources_are_atomic_and_revisions_are_immutable():
    store, result = corpus()
    original = store.snapshot()
    invalid = fixture_sources()
    invalid[1]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        WorkflowCorpus(store).ingest("test", "001", invalid)
    assert store.snapshot() == original
    revised = fixture_sources()
    revised[0] = source("index.md", revised[0]["text"].replace("Door won't close", "Door sticks"))
    imported = WorkflowCorpus(store).ingest("test", "001", revised)
    assert imported["case_id"] != result["case_id"]
    assert store.snapshot()["entities"][result["case_id"]] == original["entities"][result["case_id"]]


@pytest.mark.parametrize("heading", ["Observations", "## Observations", "**OBSERVATIONS**:"])
def test_attachment_replay_removes_hindsight_commentary_and_original_byte_access(heading):
    store, result = corpus()
    document_id = result["documents"]["attachments/report.md"]

    def amend(state):
        document = state["documents"][document_id]
        document.update(mime="application/pdf", text=f"Original quote: repair the lock.\n{heading}\n"
                        "FORBIDDEN_HINDSIGHT: the case overview later says the job succeeded.")

    store.mutate(amend)
    state = store.snapshot()
    transition = next(e for e in state["entities"].values()
                      if e["type"] == "workflow_transition" and e["fields"]["after_step"] == 3)
    replay = prepare_replay(state, transition["id"])
    assert "FORBIDDEN_HINDSIGHT" not in json.dumps(replay["state"])
    assert "FORBIDDEN_HINDSIGHT" not in replay["context"]
    assert "Original quote" in replay["context"]
    assert replay["state"]["documents"][document_id]["raw_content_base64"] is None
    assert "FORBIDDEN_HINDSIGHT" in store.snapshot()["documents"][document_id]["text"]


def test_entire_added_corpus_parses_with_exact_declared_event_counts():
    cases = list(Path("Property Management").glob("*/index.md"))
    assert len(cases) == 50
    events, triplets = 0, 0
    for index in cases:
        items = sources(index.parent)
        for item in items:
            item["text"] = ("attachment" if item["mime"] == "application/pdf"
                            else base64.b64decode(item["content_base64"]).decode())
        parsed = parse_case("property-management", index.parent.name, items)
        events += len(parsed["events"])
        triplets += max(0, len(parsed["events"]) - 2)
    assert events == 1505
    assert triplets == 1405


def test_production_agent_replay_mcp_and_grading_share_only_prefix(monkeypatch):
    store, result = corpus()
    settings = Settings()
    app = create_app(store=store, settings=settings, seed=False)
    agent = create_app("agent", store=store, settings=settings, seed=False)
    agent.include_router(managed.router)
    for name in ["ANTHROPIC_API_KEY", "MANAGED_AGENT_ID", "MANAGED_ENVIRONMENT_ID", "MCP_SERVER_URL"]:
        monkeypatch.setenv(name, "test")
    messages = []

    def ma(method, path, payload=None, params=None):
        if path == "/vaults":
            return {"id": "vault-test"}
        if path == "/sessions":
            return {"id": "session-test"}
        if method == "GET" and path.endswith("/events"):
            return {"data": [{"id": "answer", "type": "agent.message", "content": [
                {"type": "text", "text": 'Ask tenant for a photo.'}]}]}
        if method == "GET":
            return {"status": "idle"}
        if path.endswith("/events"):
            messages.append(json.dumps(payload))
        return {"id": "ok"}

    monkeypatch.setattr(managed, "ma", ma)
    with TestClient(app) as client:
        admin = {"Authorization": f"Bearer {issue_token(settings)}"}
        transition = next(e for e in store.snapshot()["entities"].values()
                          if e["type"] == "workflow_transition" and e["fields"]["after_step"] == 1)
        prepared = client.post("/v1/workflow-evaluations", json={"transition_id": transition["id"]}, headers=admin)
        assert prepared.status_code == 201, prepared.text
        evaluation_id = prepared.json()["id"]
        run = managed.create_run(agent, "Next step", [], evaluation_id=evaluation_id)
        assert "EXPECTED_NEXT" not in "".join(messages)
        assert "FORBIDDEN" not in "".join(messages)
        assert run["provider"]["name"] == "claude-managed-agents"
        with pytest.raises(ValueError, match="submitted"):
            managed.create_run(agent, "Next step", [], evaluation_id=evaluation_id)
        token = issue_token(settings, f"agent_run:{run['id']}")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": "2025-11-25"}

        def rpc(name, args):
            return client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1,
                "method": "tools/call", "params": {"name": name, "arguments": args}}).json()["result"]

        hidden = rpc("get_entity", {"id": result["case_id"]})
        assert hidden["isError"]
        before = copy_entities(store)
        outgoing = rpc("send_email", {"to": ["tenant@example.test"], "subject": "Door photo", "body": "Please send a photo"})
        assert outgoing["structuredContent"]["external_execution"] is False
        assert copy_entities(store) == before
        assert rpc("get_entity", {"id": "ticket:replay-case"})["isError"] is False
        done = managed.sync(agent, run["id"])
        assert done["status"] == "done"
        monkeypatch.setattr("propadmin_runtime.routes_workflow.grade", lambda context, expected, actual: {
            "scores": {"action": 95}, "score": 95, "passed": True,
            "explanation": "Same next action", "differences": [], "judge_model": "claude-haiku-5-5",
            "judge_response_id": "grade-test", "judge_usage": {"input_tokens": 100},
        })
        graded = client.post(f"/v1/workflow-evaluations/{evaluation_id}/grade", headers=admin, json={})
        assert graded.status_code == 200, graded.text
        assert graded.json()["fields"]["status"] == "graded"
        assert graded.json()["fields"]["agent_provider"]["agent_id"] == "test"


def copy_entities(store):
    return json.dumps(store.snapshot()["entities"], sort_keys=True)


def test_holdout_cannot_be_used_to_publish_workflows():
    store = Store()
    imported = WorkflowCorpus(store).ingest("test", "005", fixture_sources("005"))
    assert imported["split"] == "holdout"
    settings = Settings()
    with TestClient(create_app(store=store, settings=settings, seed=False)) as client:
        response = client.post("/v1/workflow-skills/publish", headers={"Authorization": f"Bearer {issue_token(settings)}"},
            json={"slug": "test-skill", "name": "Test", "content": "---\nname: test-skill\n---\nTest workflow content",
                  "summary": "Test", "based_on_version": 0, "training_cases": [imported["case_id"]]})
        assert response.status_code == 422 and "holdout" in response.text
        assert not store.snapshot()["skills"]
