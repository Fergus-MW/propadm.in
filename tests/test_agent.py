"""Agent runs on Claude Managed Agents (HTTP mocked), plan rules and skill proposal review."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app
from propadmin_runtime.auth import verify_token
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
