"""Agent runs on Claude Managed Agents (HTTP mocked), plan rules and skill proposal review."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app
from propadmin_runtime.auth import verify_token
from propadmin_runtime.routes_email import TOOLS as EMAIL_TOOLS
from propadmin_runtime.tools_agent import TOOLS

from services.agent.app import managed

ENV = {
    "ANTHROPIC_API_KEY": "test-key",
    "MANAGED_AGENT_ID": "agent_1",
    "MANAGED_ENVIRONMENT_ID": "env_1",
    "MCP_SERVER_URL": "https://api.example.test/mcp",
}


@pytest.fixture
def anthropic(monkeypatch):
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    calls, sessions = [], iter(f"sesn_{i}" for i in range(1, 100))

    def handler(request):
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, body, request.headers))
        path = request.url.path
        if path == "/v1/vaults":
            return httpx.Response(200, json={"id": "vlt_1"})
        if path == "/v1/sessions":
            return httpx.Response(200, json={"id": next(sessions)})
        if request.method == "GET" and path.endswith("/events"):
            event = {
                "id": "sevt_1",
                "type": "agent.message",
                "content": [{"type": "text", "text": "Booked Moss Plumbing."}],
            }
            return httpx.Response(200, json={"data": [event], "next_page": None})
        if request.method == "GET":
            return httpx.Response(200, json={"id": path.rsplit("/", 1)[1], "status": "idle"})
        return httpx.Response(200, json={"id": "ok"})

    monkeypatch.setattr(managed, "http", httpx.Client(transport=httpx.MockTransport(handler)))
    return calls


@pytest.fixture
def agent():
    app = create_app("agent", store=Store(), seed=False)
    app.include_router(managed.router)
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {app.state.settings.internal_token}"
    return client


def test_unconfigured_provider_is_explicit_503(agent, monkeypatch):
    for name in [*ENV, "AGENT_SERVICE_URL"]:
        monkeypatch.delenv(name, raising=False)
    response = agent.post("/internal/runs", json={"goal": "Fix boiler"})
    assert response.status_code == 503 and "MANAGED_AGENT_ID" in response.json()["detail"]
    assert agent.app.state.store.snapshot()["runs"] == {}
    with TestClient(create_app(store=Store(), seed=False)) as api:
        token = api.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        api.headers["Authorization"] = f"Bearer {token}"
        assert api.post("/v1/agent-runs", json={"goal": "Fix boiler"}).status_code == 503


def test_run_creates_session_with_mcp_grant_and_relays_events(agent, anthropic):
    run = agent.post(
        "/internal/runs", json={"goal": "Fix boiler", "subjects": ["ticket:prop-1042"]}
    )
    assert run.status_code == 201
    run = run.json()
    assert run["status"] == "running" and run["session_id"] == "sesn_1"
    assert all(h["anthropic-beta"] == "managed-agents-2026-04-01" for *_, h in anthropic)
    credential = next(b for m, p, b, _ in anthropic if p == "/v1/vaults/vlt_1/credentials")
    assert credential["auth"]["mcp_server_url"] == ENV["MCP_SERVER_URL"]
    settings = agent.app.state.settings
    assert verify_token(settings, credential["auth"]["token"]) == f"agent_run:{run['id']}"
    assert agent.app.state.store.snapshot()["mcp_sessions"][run["id"]]["revoked"] is False
    session = next(b for m, p, b, _ in anthropic if p == "/v1/sessions")
    assert session["agent"] == "agent_1" and session["vault_ids"] == ["vlt_1"]
    kickoff = next(b for m, p, b, _ in anthropic if p == "/v1/sessions/sesn_1/events")
    assert "Fix boiler" in kickoff["events"][0]["content"][0]["text"]

    synced = agent.post(f"/internal/runs/{run['id']}/sync").json()
    assert synced["transcript"][0]["text"] == "Booked Moss Plumbing."
    assert synced["status"] == "done"  # idle with no unfinished plan


@pytest.mark.parametrize("previous_reply", [False, True])
@pytest.mark.parametrize("has_plan", [False, True])
def test_idle_run_waits_for_pending_message_before_settling(
    agent, anthropic, monkeypatch, previous_reply, has_plan
):
    run = agent.post("/internal/runs", json={"goal": "Call a plumber"}).json()
    run_id, store = run["id"], agent.app.state.store
    if has_plan:
        TOOLS["create_plan"]["handler"](
            agent.app, run_id, {"goal": "Call a plumber", "steps": [{"title": "Place call"}]}
        )
    events = []
    if previous_reply:
        events.append({"id": "reply-1", "type": "agent.message", "content": []})
    events.append({"id": "pending", "type": "user.message", "content": []})

    def handler(request):
        if request.url.path.endswith("/events"):
            return httpx.Response(200, json={"data": events, "next_page": None})
        return httpx.Response(200, json={"status": "idle"})

    monkeypatch.setattr(managed, "http", httpx.Client(transport=httpx.MockTransport(handler)))
    for _ in range(2):
        response = agent.post(f"/internal/runs/{run_id}/sync")
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        state = store.snapshot()
        assert state["mcp_sessions"][run_id]["revoked"] is False
        assert not state["wakeups"]

    events.append({"id": "reply-2", "type": "agent.message", "content": []})
    response = agent.post(f"/internal/runs/{run_id}/sync")
    assert response.status_code == 200
    assert response.json()["status"] == ("sleeping" if has_plan else "done")
    assert store.snapshot()["mcp_sessions"][run_id]["revoked"] is (not has_plan)


def test_events_wake_owning_run_or_start_new_one(agent, anthropic, monkeypatch):
    monkeypatch.setenv("AGENT_MAX_SESSIONS", "1")
    first = agent.post(
        "/internal/runs", json={"goal": "Fix boiler", "subjects": ["ticket:prop-1042"]}
    ).json()
    TOOLS["sleep"]["handler"](
        agent.app, first["id"], {"reason": "Waiting for reply", "wake_on": ["thread:42"]}
    )
    woken = agent.post(
        "/internal/events",
        json={"kind": "email.received", "subjects": ["thread:42"], "summary": "Tenant replied"},
    ).json()
    assert woken == {"run_id": first["id"], "action": "woken"}
    messages = [b for m, p, b, _ in anthropic if p == "/v1/sessions/sesn_1/events" and m == "POST"]
    assert "Tenant replied" in messages[-1]["events"][0]["content"][0]["text"]
    state = agent.app.state.store.snapshot()
    assert state["runs"][first["id"]]["status"] == "running"
    assert {w["status"] for w in state["wakeups"].values()} == {"fired"}

    started = agent.post(
        "/internal/events",
        json={"kind": "email.received", "subjects": ["thread:99"], "summary": "New leak"},
    ).json()
    assert started["action"] == "started" and started["run_id"] != first["id"]
    queued = agent.app.state.store.snapshot()["runs"][started["run_id"]]
    assert queued["status"] == "queued"  # cap of one running session
    ignored = agent.post(
        "/internal/events",
        json={"kind": "email.delivered", "subjects": ["thread:7"], "summary": "Receipt"},
    ).json()
    assert ignored["action"] == "ignored"


def test_supplier_threads_resume_repair_until_completion_and_notification(
    agent, anthropic, monkeypatch
):
    from propadmin_runtime import routes_email

    run = agent.post(
        "/internal/runs", json={"goal": "Resolve leak", "subjects": ["tenant-thread"]}
    ).json()
    run_id, app = run["id"], agent.app
    TOOLS["create_plan"]["handler"](app, run_id, {
        "goal": "Repair and notify tenant",
        "steps": [{"title": "Acknowledge and contact suppliers"},
                  {"title": "Verify repair"}, {"title": "Send final tenant reply"}],
    })
    sends = iter([
        {"thread_id": "tenant-thread", "email_id": "email:ack"},
        {"thread_id": "supplier-a", "email_id": "email:quote-a"},
        {"thread_id": "supplier-b", "email_id": "email:quote-b"},
    ])
    monkeypatch.setattr(routes_email, "call_service", lambda *args: next(sends))
    EMAIL_TOOLS["reply_email"]["handler"](
        app, run_id, {"email_id": "email:tenant", "body": "We are arranging repair."}
    )
    for address in ("a@example.net", "b@example.net"):
        EMAIL_TOOLS["send_email"]["handler"](
            app, run_id, {"to": [address], "subject": "Leak quote", "body": "Earliest visit?"}
        )
    assert set(app.state.store.snapshot()["runs"][run_id]["subjects"]) == {
        "tenant-thread", "supplier-a", "supplier-b", "email:ack",
        "email:quote-a", "email:quote-b",
    }
    TOOLS["update_step"]["handler"](
        app, run_id, {"step_id": "step-1", "status": "done", "evidence": "email:quote-b"}
    )
    TOOLS["update_step"]["handler"](
        app, run_id, {"step_id": "step-2", "status": "blocked", "note": "Awaiting repair"}
    )
    # Supplier threads are owned even when the model omits them from wake_on.
    for thread in ("supplier-b", "supplier-a", "tenant-thread"):
        TOOLS["sleep"]["handler"](app, run_id, {"reason": "Awaiting replies"})
        event = agent.post("/internal/events", json={
            "kind": "email.received", "subjects": [thread], "summary": "Reply arrived",
        }).json()
        assert event == {"run_id": run_id, "action": "woken"}
        # An idle provider session must not finish a repair with open plan steps.
        assert agent.post(f"/internal/runs/{run_id}/sync").json()["status"] == "sleeping"
    assert len(app.state.store.snapshot()["runs"]) == 1
    actions = list(app.state.store.snapshot()["actions"].values())
    assert [a["tool"] for a in actions if a["tool"] in EMAIL_TOOLS] == [
        "reply_email", "send_email", "send_email",
    ]

    before = app.state.store.snapshot()["runs"][run_id]["subjects"]

    def failed_send(*args):
        raise ValueError("Email provider unavailable")

    monkeypatch.setattr(routes_email, "call_service", failed_send)
    with pytest.raises(ValueError, match="provider unavailable"):
        EMAIL_TOOLS["send_email"]["handler"](
            app, run_id, {"to": ["c@example.net"], "subject": "Leak quote", "body": "Quote?"}
        )
    state = app.state.store.snapshot()
    assert state["runs"][run_id]["subjects"] == before
    assert list(state["actions"].values())[-1]["error"] == "Email provider unavailable"


def test_plan_rules_are_enforced():
    app = create_app(store=Store(), seed=False)
    app.state.store.mutate(
        lambda s: s["runs"].__setitem__(
            "agent_run:1", {"id": "agent_run:1", "subjects": [], "status": "running"}
        )
    )

    def call(name, **args):
        return TOOLS[name]["handler"](app, "agent_run:1", args)

    call("create_plan", goal="Repair", steps=[{"title": "Call tenant"}, {"title": "Book"}])
    with pytest.raises(ValueError, match="in_progress or blocked"):
        call("sleep", reason="wait")
    call("update_step", step_id="step-1", status="in_progress")
    with pytest.raises(ValueError, match="Only one step"):
        call("update_step", step_id="step-2", status="in_progress")
    with pytest.raises(ValueError, match="evidence"):
        call("update_step", step_id="step-1", status="done")
    plan = call("update_step", step_id="step-1", status="done", evidence="call:abc completed")
    assert plan["version"] == 3 and len(plan["history"]) == 2
    plan = call(
        "revise_plan",
        reason="New info",
        steps=[{"id": "step-1", "title": "Call tenant"}, {"title": "Order part"}],
    )
    assert [s["status"] for s in plan["steps"]] == ["done", "pending"]
    errors = [a for a in app.state.store.snapshot()["actions"].values() if a["error"]]
    assert len(errors) == 3  # failed tool calls are audited too


def test_approved_proposal_creates_version_and_resolves_issues():
    with TestClient(create_app(store=Store())) as api:
        token = api.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        api.headers["Authorization"] = f"Bearer {token}"
        app = api.app
        app.state.store.mutate(
            lambda s: s["runs"].__setitem__(
                "agent_run:1", {"id": "agent_run:1", "subjects": [], "status": "running"}
            )
        )
        issue_args = dict(
            skill="book-contractor",
            title="No access check",
            description="Visit failed",
            evidence="call:1",
            category="missing_step",
            severity="high",
        )
        issue = TOOLS["report_workflow_issue"]["handler"](app, "agent_run:1", issue_args)
        again = TOOLS["report_workflow_issue"]["handler"](app, "agent_run:1", issue_args)
        assert again["id"] == issue["id"] and again["occurrences"] == 2
        with pytest.raises(ValueError):
            TOOLS["propose_skill_change"]["handler"](
                app,
                "agent_run:1",
                dict(
                    skill="book-contractor",
                    proposed_content="x",
                    reasoning="r",
                    expected_effect="e",
                    risks="none",
                    issues=[],
                ),
            )
        proposal = TOOLS["propose_skill_change"]["handler"](
            app,
            "agent_run:1",
            dict(
                skill="book-contractor",
                proposed_content="# Book\n\nConfirm access first.\n",
                reasoning="Visits fail",
                expected_effect="Fewer failed visits",
                risks="none",
                issues=[issue["id"]],
            ),
        )

        assert (
            api.post(
                f"/v1/skill-proposals/{proposal['id']}/review", json={"decision": "rejected"}
            ).status_code
            == 422
        )
        reviewed = api.post(
            f"/v1/skill-proposals/{proposal['id']}/review",
            json={"decision": "approved", "notes": "Good"},
        )
        assert reviewed.status_code == 200 and reviewed.json()["published_version"] == 2
        skill = api.get("/v1/skills/skill:book-contractor").json()
        assert skill["current_version"] == 2 and "Confirm access" in skill["content"]
        assert skill["issues"][0]["status"] == "resolved"
        version = api.get("/v1/entities/skill_version:book-contractor-v2")
        assert version.status_code == 200
        assert (
            api.post(
                f"/v1/skill-proposals/{proposal['id']}/review", json={"decision": "approved"}
            ).status_code
            == 422
        )


def test_admin_chat_runs_admin_agent_with_admin_grant_and_waits(agent, anthropic, monkeypatch):
    assert agent.post("/internal/admin-chat", json={"message": "List rules"}).status_code == 503
    monkeypatch.setenv("MANAGED_ADMIN_AGENT_ID", "agent_admin")
    chat = agent.post("/internal/admin-chat", json={"message": "List rules"}).json()
    assert chat["kind"] == "admin" and chat["status"] == "running"
    session = next(b for m, p, b, _ in anthropic if p == "/v1/sessions")
    assert session["agent"] == "agent_admin"
    kickoff = next(b for m, p, b, _ in anthropic if p == "/v1/sessions/sesn_1/events")
    assert kickoff["events"][0]["content"][0]["text"] == "List rules"
    store = agent.app.state.store
    assert store.snapshot()["mcp_sessions"][chat["id"]]["scope"] == "admin"

    synced = agent.post(f"/internal/runs/{chat['id']}/sync").json()
    assert synced["status"] == "sleeping"  # answered: waits for the admin, never "done"
    assert not store.snapshot()["wakeups"]

    reply = agent.post(
        "/internal/admin-chat", json={"message": "Thanks", "run_id": chat["id"]}
    ).json()
    assert reply["status"] == "running" and reply["sessions"] == ["sesn_1"]
    sent = [b for m, p, b, _ in anthropic if p == "/v1/sessions/sesn_1/events" and m == "POST"]
    assert sent[-1]["events"][0]["content"][0]["text"] == "Thanks"
    run = agent.post("/internal/runs", json={"goal": "Fix boiler"}).json()
    refused = agent.post("/internal/admin-chat", json={"message": "Hi", "run_id": run["id"]})
    assert refused.status_code == 422


def test_inbound_event_returns_durable_grant_before_provider_start(agent, anthropic):
    import asyncio

    from fastapi import BackgroundTasks

    tasks = BackgroundTasks()
    result = managed.route_event(agent.app, 'call.inbound_started', ['person:test'],
                                 'Controlled inbound call', {'conversation_id': 'conv_test'}, tasks)
    state = agent.app.state.store.snapshot()
    run = state['runs'][result['run_id']]
    assert run['status'] == 'queued' and run['session_id'] is None
    assert state['mcp_sessions'][run['id']]['revoked'] is False
    assert not anthropic  # webhook response does not await remote provisioning
    asyncio.run(tasks())
    assert agent.app.state.store.snapshot()['runs'][run['id']]['session_id'] == 'sesn_1'
