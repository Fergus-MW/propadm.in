"""Case leakage boundaries, private tests and autonomous version publication."""

import json

import pytest
from fastapi.testclient import TestClient
from propadmin_core.graph import create_in_state
from propadmin_core.store import Store, identifier
from propadmin_core.workflow_corpus import WorkflowCorpus
from propadmin_core.workflow_tuning import (
    READ_TOOLS,
    evaluation_record,
    isolated_graph,
    prepare_sample,
    skill_candidate,
)
from propadmin_runtime import create_app
from propadmin_runtime.auth import issue_token
from propadmin_runtime.config import Settings
from propadmin_runtime.workflow_tuner import advance, create_job

from services.agent.app import managed
from tests.test_workflow_replay import corpus, fixture_sources, source

CONTENT = "---\nname: test-workflow\n---\nFollow workflow.\n"
EDIT = {
    "slug": "test-workflow",
    "name": "Test workflow",
    "based_on_version": 1,
    "old_text": "Follow workflow.",
    "new_text": "Check the approval before booking.",
    "summary": "Check approval at booking",
    "create": False,
}


def training_store():
    store = Store()
    sources = fixture_sources()
    history = "# Case 001 history\n\nTotal events: 15\n\n"
    for ordinal in range(1, 16):
        history += (
            f"## 2026-01-01 10:00:00 UTC — event {ordinal:03}\n\n"
            "- **Channel:** Note\n- **From:** Agency / system\n- **To:** Not specified\n\n"
            f"UNIQUE_STEP_{ordinal:03}: check the next operational requirement.\n\n"
        )
    sources[1] = source("history.md", history)
    imported = WorkflowCorpus(store).ingest("test", "001", sources)

    def skills(state):
        state["skills"]["skill:test-workflow"] = {
            "id": "skill:test-workflow",
            "slug": "test-workflow",
            "name": "Test workflow",
            "description": "A test workflow",
            "source": "custom",
            "status": "active",
            "current_version": 1,
            "content": CONTENT,
            "versions": [],
        }
        create_in_state(
            state,
            {
                "id": "skill:test-workflow",
                "type": "skill",
                "name": "Test workflow",
                "fields": {"slug": "test-workflow", "source": "custom", "status": "active"},
            },
        )
        create_in_state(
            state,
            {
                "id": "skill_version:test-workflow-v1",
                "type": "skill_version",
                "name": "Test workflow v1",
                "fields": {"version": 1, "content": CONTENT},
            },
        )

    store.mutate(skills)
    return store, imported


def test_graph_masks_all_revisions_sources_derivatives_and_runtime_answer_keys():
    store, imported = corpus()
    other = WorkflowCorpus(store).ingest("test", "002", fixture_sources("002"))
    holdout = WorkflowCorpus(store).ingest("test", "005", fixture_sources("005"))
    revised = fixture_sources()
    revised[0] = source(
        "index.md", revised[0]["text"].replace("Door won't close", "Door is jammed")
    )
    revision = WorkflowCorpus(store).ingest("test", "001", revised)

    def derived(state):
        doc_id = imported["documents"]["history.md"]
        create_in_state(
            state,
            {
                "id": "ticket:derived-secret",
                "type": "ticket",
                "name": "SECRET_TICKET",
                "fields": {},
                "evidence": [{"document_id": doc_id}],
            },
        )
        state["chunks"]["chunk:secret-derived"] = {
            "id": "chunk:secret-derived",
            "document_id": doc_id,
            "text": "SECRET_CHUNK",
        }
        state["facts"]["fact:secret"] = {
            "id": "fact:secret",
            "document_id": doc_id,
            "value": "SECRET_FACT",
        }
        create_in_state(
            state,
            {
                "id": "workflow_evaluation:old",
                "type": "workflow_evaluation",
                "name": "Old grade",
                "fields": {"actual": "SECRET_REPLAY_ANSWER", "status": "graded"},
            },
        )
        state["runs"]["old-run"] = {"final_message": "SECRET_RUNTIME_ANSWER"}

    store.mutate(derived)
    state = store.snapshot()
    transition = next(
        e
        for e in state["entities"].values()
        if e["type"] == "workflow_transition"
        and e["fields"]["case_id"] == imported["case_id"]
        and e["fields"]["after_step"] == 1
    )
    sample = prepare_sample(state, transition["id"])
    exposed = json.dumps({"context": sample["context"], "state": sample["state"]})
    # Other case has identical wording; selected records are checked by provenance ids.
    for result in (imported, revision):
        assert result["case_id"] not in exposed
        for doc_id in result["documents"].values():
            assert doc_id not in sample["state"]["documents"]
    assert other["case_id"] in sample["state"]["entities"]
    assert holdout["case_id"] in sample["state"]["entities"]
    assert all(
        term not in exposed
        for term in (
            "SECRET_TICKET",
            "SECRET_CHUNK",
            "SECRET_FACT",
            "SECRET_REPLAY_ANSWER",
            "SECRET_RUNTIME_ANSWER",
        )
    )
    assert not sample["state"]["changes"] and not sample["state"]["workflow_tuning_jobs"]
    assert store.snapshot() == state


def configured_agent(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "MANAGED_AGENT_ID",
        "MANAGED_TUNING_AGENT_ID",
        "MANAGED_ENVIRONMENT_ID",
        "MCP_SERVER_URL",
    ):
        monkeypatch.setenv(name, name.lower())


def test_tuning_agent_definition_and_mcp_enforce_read_tools_even_when_called_by_name(monkeypatch):
    store, imported = training_store()
    settings = Settings()
    app = create_app(store=store, settings=settings, seed=False)
    agent = create_app("agent", store=store, settings=settings, seed=False)
    configured_agent(monkeypatch)
    from propadmin_runtime.workflow_tuner import new_evaluation

    job = create_job(store)
    transition_id = next(
        e["id"] for e in store.snapshot()["entities"].values() if e["type"] == "workflow_transition"
    )
    sample = prepare_sample(store.snapshot(), transition_id)
    evaluation = new_evaluation(store, job["id"], sample)
    calls = []

    def ma(method, path, payload=None, params=None):
        calls.append((path, payload))
        if path == "/vaults":
            return {"id": "vault"}
        if path == "/sessions":
            assert payload["agent"] == "managed_tuning_agent_id"
            return {"id": "session"}
        return {}

    monkeypatch.setattr(managed, "ma", ma)
    run = managed.create_run(agent, "Predict", [], evaluation_id=evaluation["id"])
    assert run["kind"] == "tuning"
    assert run["provider"]["agent_id"] == "managed_tuning_agent_id"
    assert sample["expected"] not in json.dumps(calls)
    assert run["evaluation_id"] == evaluation["id"]
    with TestClient(app) as client:
        headers = {
            "Authorization": f"Bearer {issue_token(settings, 'agent_run:' + run['id'])}",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-11-25",
        }

        def rpc(method, params=None):
            return client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
            ).json()["result"]

        assert {t["name"] for t in rpc("tools/list")["tools"]} == READ_TOOLS
        for name, args in (
            ("send_email", {"to": ["tenant@example.test"], "subject": "Test", "body": "Test"}),
            ("place_call", {"to": "+441234567890", "objective": "Test"}),
            ("upsert_entity", {"type": "ticket", "name": "Forbidden", "reason": "Test"}),
            ("query_graph", {"query": "SELECT * FROM workflow_evaluation"}),
            ("get_entity", {"id": imported["case_id"]}),
            ("get_document", {"id": imported["documents"]["history.md"]}),
        ):
            assert rpc("tools/call", {"name": name, "arguments": args})["isError"]
        assert not rpc(
            "tools/call", {"name": "get_skill", "arguments": {"skill": "test-workflow"}}
        )["isError"]
        assert "ticket:forbidden" not in store.snapshot()["entities"]


def fake_controller(app, monkeypatch, answers=None, revision=EDIT):
    answers = iter(answers or [])

    def service(settings, name, path, payload=None, **kwargs):
        if path == "/internal/tuning/config":
            return {"agent_id": "tuner"}
        if path == "/internal/runs":
            evaluation_id = payload["evaluation_id"]
            state = app.state.store.snapshot()
            fields = evaluation_record(state, evaluation_id)["fields"]
            if fields["tuning_mode"] == "revision":
                final = json.dumps(revision)
            else:
                answer = next(answers, "correct")
                final = json.dumps(
                    {"answer": answer, "reasoning": "Based on the supplied prefix and workflow."}
                )

            def write(state):
                key = identifier("agent_run")
                run = {
                    "id": key,
                    "status": "done",
                    "kind": "tuning",
                    "evaluation_id": evaluation_id,
                    "final_message": final,
                    "provider": {"name": "test", "agent_id": "tuner"},
                }
                state["runs"][key] = run
                evaluation_record(state, evaluation_id)["fields"].update(
                    status="running", run_id=key
                )
                return run

            return app.state.store.mutate(write)
        raise AssertionError(path)

    monkeypatch.setattr("propadmin_runtime.workflow_tuner.call_service", service)
    monkeypatch.setattr("propadmin_runtime.routes_tuning.call_service", service)

    def judge(context, expected, actual):
        assert '"reasoning"' not in actual
        passed = actual != "wrong"
        return {
            "passed": passed,
            "score": 95 if passed else 30,
            "scores": {
                d: 95 if passed else 30
                for d in ("action", "facts", "recipient_channel", "sequence", "communication")
            },
            "explanation": "Matches" if passed else "Wrong next action",
            "differences": [] if passed else ["Check approval"],
            "judge_model": "test-haiku",
            "judge_response_id": "test",
            "judge_usage": {},
        }

    monkeypatch.setattr("propadmin_runtime.workflow_tuner.grade", judge)


def settle(app, job_id, limit=100):
    for _ in range(limit):
        job = app.state.store.snapshot()["workflow_tuning_jobs"][job_id]
        if job["status"] != "running":
            return job
        advance(app, job_id)
    raise AssertionError("Loop did not settle")


def test_loop_corrects_small_edit_automatically_and_stops_at_ten_unique_passes(monkeypatch):
    store, _ = training_store()
    app = create_app(store=store, seed=False)
    fake_controller(app, monkeypatch, ["wrong", "correct"])
    job = create_job(store)
    with pytest.raises(ValueError, match="already running"):
        create_job(store)
    result = settle(app, job["id"])
    assert result["status"] == "completed", result.get("error")
    assert result["trials"] == 11 and result["streak"] == 10
    assert len(set(result["successful"])) == 10
    assert len(result["changes"]) == 1
    skill = store.snapshot()["skills"]["skill:test-workflow"]
    assert skill["current_version"] == 2
    assert skill["content"] == CONTENT.replace(EDIT["old_text"], EDIT["new_text"])
    proposal = next(iter(store.snapshot()["proposals"].values()))
    assert proposal["reviewed_by"] == "workflow-tuner" and proposal["status"] == "approved"
    assert proposal["validation"][0]["passed"]


@pytest.mark.parametrize(
    "answers, failed_phase",
    [(["wrong", "wrong"], "validate"), (["correct", "wrong", "correct", "wrong"], "regress")],
)
def test_candidate_is_rejected_without_changing_live_skills(monkeypatch, answers, failed_phase):
    store, _ = training_store()
    app = create_app(store=store, seed=False)
    fake_controller(app, monkeypatch, answers)
    job = create_job(store)
    result = settle(app, job["id"])
    assert result["status"] == "completed", result.get("error")
    assert not result["changes"]
    assert result["rejected"][0]["validation"][-1]["phase"] == failed_phase
    assert store.snapshot()["skills"]["skill:test-workflow"]["current_version"] == 1
    assert not store.snapshot()["proposals"]


def test_private_upload_reference_is_hidden_never_ingested_and_never_tunes(monkeypatch):
    store, _ = training_store()
    app = create_app(store=store, seed=False)
    fake_controller(app, monkeypatch, ["wrong"])
    uploaded = {
        "name": "Private case",
        "initial_context": "PRIVATE_CONTEXT",
        "steps": [f"PRIVATE_STEP_{i}" for i in range(1, 10)],
        "expected": "PRIVATE_ANSWER",
    }
    original = store.snapshot()
    with TestClient(app) as client:
        admin = {"Authorization": f"Bearer {issue_token(app.state.settings)}"}
        assert client.post("/v1/workflow-tuning/tests", json=uploaded).status_code == 401
        response = client.post("/v1/workflow-tuning/tests", json=uploaded, headers=admin)
        assert response.status_code == 201, response.text
        assert "uploaded" not in response.json()
        assert response.json()["id"] not in {
            j["id"] for j in client.get("/v1/ingest/jobs", headers=admin).json()["items"]
        }
        result = settle(app, response.json()["id"])
    assert result["status"] == "completed" and result["history"][0]["passed"] is False
    assert not result["changes"]
    state = store.snapshot()
    for collection in ("entities", "documents", "chunks", "facts", "embeddings", "skills", "edges"):
        assert state[collection] == original[collection], collection
    sandbox = next(iter(state["workflow_sandboxes"].values()))
    assert "PRIVATE_ANSWER" not in json.dumps(sandbox)
    evaluation = next(iter(state["workflow_private_evaluations"].values()))
    assert "PRIVATE_STEP_9" in evaluation["fields"]["context"]
    assert "PRIVATE_ANSWER" not in evaluation["fields"]["context"]


def test_bad_outputs_stale_edits_stop_and_budget_do_not_report_success(monkeypatch):
    store, _ = training_store()
    app = create_app(store=store, seed=False)
    fake_controller(app, monkeypatch, ["wrong"] * 25)
    result = settle(app, create_job(store, max_trials=10)["id"], limit=100)
    assert result["status"] == "exhausted" and result["streak"] == 0
    malformed = {**EDIT, "old_text": "missing"}
    with pytest.raises(ValueError, match="unique replacement"):
        skill_candidate(store.snapshot(), json.dumps(malformed))
    stale = {**EDIT, "based_on_version": 0}
    with pytest.raises(ValueError, match="changed"):
        skill_candidate(store.snapshot(), json.dumps(stale))
    job = create_job(store)
    with TestClient(app) as client:
        admin = {"Authorization": f"Bearer {issue_token(app.state.settings)}"}
        assert (
            client.post(
                f"/v1/workflow-tuning/runs/{job['id']}/stop", json={}, headers=admin
            ).status_code
            == 200
        )
    advance(app, job["id"])
    assert store.snapshot()["workflow_tuning_jobs"][job["id"]]["status"] == "stopped"


def test_new_workflow_candidate_and_current_graph_view_are_consistent():
    store, _ = training_store()
    edit = {
        **EDIT,
        "slug": "new-workflow",
        "based_on_version": 0,
        "create": True,
        "old_text": "",
        "new_text": "---\nname: new-workflow\n---\nCheck approval before booking.\n",
    }
    candidate = skill_candidate(store.snapshot(), json.dumps(edit))
    sandbox = isolated_graph(store.snapshot(), candidate=candidate)
    assert sandbox["skills"]["skill:new-workflow"]["content"] == edit["new_text"]
    candidate = skill_candidate(store.snapshot(), json.dumps(EDIT))
    sandbox = isolated_graph(store.snapshot(), candidate=candidate)
    assert (
        sandbox["entities"]["skill_version:test-workflow-v1"]["fields"]["content"]
        == candidate["content"]
    )
    assert sandbox["skills"]["skill:test-workflow"]["content"] == candidate["content"]


def test_durable_restart_and_active_lease_prevent_duplicate_trials(monkeypatch):
    import time

    store, _ = training_store()
    app = create_app(store=store, seed=False)
    fake_controller(app, monkeypatch)
    job = create_job(store)
    advance(app, job["id"])
    evaluation_id = store.snapshot()["workflow_tuning_jobs"][job["id"]]["evaluation_id"]
    store.mutate(
        lambda state: state["workflow_tuning_jobs"][job["id"]].update(lease_until=time.time() + 60)
    )
    advance(app, job["id"])
    assert store.snapshot()["workflow_tuning_jobs"][job["id"]]["trials"] == 0
    store.mutate(lambda state: state["workflow_tuning_jobs"][job["id"]].update(lease_until=0))
    restarted = create_app(store=store, seed=False)
    advance(restarted, job["id"])
    result = store.snapshot()["workflow_tuning_jobs"][job["id"]]
    assert result["trials"] == 1 and result["history"][0]["id"] == evaluation_id


def test_tuning_provisioning_has_only_the_mcp_toolset(monkeypatch):
    from infra.scripts import managed_agent

    bodies = []
    monkeypatch.setattr(managed_agent, "find", lambda *args: None)
    monkeypatch.setattr(
        managed_agent,
        "call",
        lambda http, method, path, payload: bodies.append(payload) or {"id": "tuner"},
    )
    managed_agent.ensure_agent(
        None, managed_agent.TUNING_AGENT_NAME, managed_agent.TUNING_SYSTEM, tuning=True
    )
    assert [tool["type"] for tool in bodies[0]["tools"]] == ["mcp_toolset"]
    assert len(bodies[0]["mcp_servers"]) == 1
