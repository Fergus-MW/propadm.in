"""Thin run orchestrator around Claude Managed Agents: sessions, routing, wake-ups and relay.

Anthropic runs the agent loop and sandbox. This service only creates sessions, sends them
messages, and copies their events into the run record. No session is ever simulated.
"""

import json
import os
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from propadmin_core import ProviderNotConfigured
from propadmin_core.store import identifier, now, publish
from propadmin_runtime.auth import issue_token, require_internal
from propadmin_runtime.models import Input
from propadmin_runtime.tools_agent import MAX_SLEEP_MINUTES, plan_complete, schedule_wakeup
from pydantic import Field

API = "https://api.anthropic.com/v1"
BETA = "managed-agents-2026-04-01"
LIVE = {"queued", "running", "sleeping"}
# Events that start a session when no live or sleeping run owns their subjects.
TRIGGERS = {"email.received", "call.inbound_started", "ticket.created", "invocation.scheduled"}
TOKEN_LIFETIME = 86400
http = httpx.Client(timeout=30)  # tests swap in an httpx.MockTransport client

router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])


def config():
    names = ("ANTHROPIC_API_KEY", "MANAGED_AGENT_ID", "MANAGED_ENVIRONMENT_ID", "MCP_SERVER_URL")
    values = {name: os.getenv(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ProviderNotConfigured(
            f"Claude Managed Agents is not configured ({', '.join(missing)}); no session started"
        )
    return values


def provider():
    return {
        "name": "claude-managed-agents",
        "model": os.getenv("AGENT_MODEL", "claude-sonnet-5-5"),
        "agent_id": os.getenv("MANAGED_AGENT_ID"),
    }


def ma(method, path, payload=None, params=None):
    response = http.request(
        method,
        API + path,
        json=payload,
        params=params,
        headers={
            "x-api-key": config()["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "anthropic-beta": BETA,
        },
    )
    if response.status_code >= 400:
        raise HTTPException(502, f"Managed Agents {method} {path} failed: {response.text[:500]}")
    return response.json()


def message(text):
    return {"type": "user.message", "content": [{"type": "text", "text": text}]}


def grant(app, run_id):
    """Same grant record and token as mcp.grant_token, rotatable per new session of a run."""

    def write(state):
        state.setdefault("mcp_sessions", {})[run_id] = {
            "session_id": run_id,
            "reason": "Managed Agents session",
            "created_at": now(),
            "expires_at": int(time.time()) + TOKEN_LIFETIME,
            "revoked": False,
        }
        publish(state, "mcp.granted", {"session_id": run_id, "run_id": run_id})

    app.state.store.mutate(write)
    return issue_token(app.state.settings, f"agent_run:{run_id}", TOKEN_LIFETIME)


def open_session(app, run, text):
    """Vault with this run's MCP bearer token, then a session of the one agent, then kickoff."""
    cfg = config()
    token = grant(app, run["id"])
    vault = ma(
        "POST",
        "/vaults",
        {"display_name": f"Properly {run['id']}", "metadata": {"run_id": run["id"]}},
    )
    ma(
        "POST",
        f"/vaults/{vault['id']}/credentials",
        {
            "display_name": "Properly graph MCP",
            "auth": {
                "type": "static_bearer",
                "mcp_server_url": cfg["MCP_SERVER_URL"],
                "token": token,
            },
        },
    )
    session = ma(
        "POST",
        "/sessions",
        {
            "agent": cfg["MANAGED_AGENT_ID"],
            "environment_id": cfg["MANAGED_ENVIRONMENT_ID"],
            "vault_ids": [vault["id"]],
            "title": run["goal"][:200],
            "metadata": {"run_id": run["id"]},
        },
    )
    ma("POST", f"/sessions/{session['id']}/events", {"events": [message(text)]})

    def save(state):
        saved = state["runs"][run["id"]]
        saved.update(session_id=session["id"], vault_id=vault["id"], synced=0, updated_at=now())
        saved["sessions"].append(session["id"])
        saved["provider"]["session_id"] = session["id"]
        publish(state, "agent_run.session", {"run_id": run["id"], "session_id": session["id"]})
        return saved

    return app.state.store.mutate(save)


def kickoff(run, extra=()):
    lines = [
        f"Run {run['id']}. Goal: {run['goal']}",
        f"Subjects you own: {', '.join(run['subjects']) or 'none'}",
        "Call get_plan first; for multi-step work create_plan, then follow planning-and-sleeping.",
        *extra,
    ]
    if run.get("summary"):
        lines.insert(1, f"Earlier session summary: {run['summary']}")
    return "\n".join(lines)


def start_queued(app):
    """Fill free slots (AGENT_MAX_SESSIONS, default 20) with queued runs, oldest first."""
    cap = int(os.getenv("AGENT_MAX_SESSIONS", "20"))

    def claim(state):
        runs = state["runs"].values()
        free = cap - sum(r["status"] == "running" for r in runs)
        queued = sorted((r for r in runs if r["status"] == "queued"), key=lambda r: r["created_at"])
        picked = queued[: max(free, 0)]
        for run in picked:
            run.update(status="running", updated_at=now())
            publish(state, "agent_run.started", {"run_id": run["id"]})
        return picked

    started = []
    for run in app.state.store.mutate(claim):
        try:
            started.append(open_session(app, run, kickoff(run, run.get("pending_messages", []))))
        except Exception as exc:
            fail(app, run["id"], str(exc))
            raise
    return started


def fail(app, run_id, error):
    def write(state):
        state["runs"][run_id].update(status="failed", error=error[:2000], updated_at=now())
        publish(state, "agent_run.failed", {"run_id": run_id})

    app.state.store.mutate(write)


def create_run(app, goal, subjects, context=""):
    config()  # explicit 503 before any record exists

    def write(state):
        run = {
            "id": identifier("agent_run"),
            "goal": goal,
            "status": "queued",
            "subjects": sorted(set(subjects)),
            "plan_id": None,
            "session_id": None,
            "sessions": [],
            "transcript": [],
            "pending_messages": [context] if context else [],
            "summary": "",
            "next_wake_at": None,
            "provider": provider(),
            "created_at": now(),
            "updated_at": now(),
        }
        state["runs"][run["id"]] = run
        publish(state, "agent_run.created", {"run_id": run["id"]})
        return run

    run = app.state.store.mutate(write)
    start_queued(app)
    return app.state.store.snapshot()["runs"][run["id"]]


def session_alive(run):
    if not run.get("session_id"):
        return False
    return ma("GET", f"/sessions/{run['session_id']}").get("status") != "terminated"


def wake(app, run_id, reason, data=None, wakeup_id=None, subjects=()):
    """Idempotent: a wakeup fires once; a woken run gets a message in the same session."""
    config()

    def claim(state):
        run = state["runs"][run_id]
        if wakeup_id and state["wakeups"].get(wakeup_id, {}).get("status") != "pending":
            return None
        if run["status"] not in LIVE:
            return None
        run["subjects"] = sorted(set(run["subjects"]) | set(subjects))
        for wakeup in state["wakeups"].values():
            if wakeup["run_id"] == run_id and wakeup["status"] == "pending":
                wakeup.update(status="fired", fired_at=now(), fired_by=reason)
        if run["status"] == "queued":
            run["pending_messages"].append(reason)
            return {**run, "action": "queued"}
        run.update(status="running", next_wake_at=None, updated_at=now())
        publish(state, "agent_run.woken", {"run_id": run_id, "reason": reason})
        return run

    run = app.state.store.mutate(claim)
    if run is None or run.get("action") == "queued":
        return {"run_id": run_id, "action": "ignored" if run is None else "queued"}
    text = f"Woken: {reason}" + (f"\nData: {json.dumps(data)[:20000]}" if data else "")
    grant_ok = (
        app.state.store.snapshot().get("mcp_sessions", {}).get(run_id, {}).get("expires_at", 0)
        > time.time() + 3600
    )
    if grant_ok and session_alive(run):
        ma("POST", f"/sessions/{run['session_id']}/events", {"events": [message(text)]})
    else:  # ended session: a new one seeded with the run summary and the plan
        open_session(app, run, kickoff(run, [text]))
    return {"run_id": run_id, "action": "woken"}


def route_event(app, kind, subjects, summary, data):
    state = app.state.store.snapshot()
    wanted = set(subjects) | {kind}
    pending = {
        w["run_id"]
        for w in state["wakeups"].values()
        if w["status"] == "pending" and wanted & set(w["wake_on"])
    }
    owner = next(
        (
            r
            for r in sorted(state["runs"].values(), key=lambda r: r["created_at"])
            if r["status"] in LIVE and (set(r["subjects"]) & set(subjects) or r["id"] in pending)
        ),
        None,
    )
    if owner:
        result = wake(app, owner["id"], f"{kind}: {summary}", data, subjects=subjects)
        return {
            "run_id": owner["id"],
            "action": "woken" if result["action"] != "ignored" else "ignored",
        }
    if kind in TRIGGERS:
        run = create_run(app, summary, subjects, f"Triggered by {kind}: {json.dumps(data)[:20000]}")
        return {"run_id": run["id"], "action": "started"}
    return {"run_id": None, "action": "ignored"}


def sync(app, run_id):
    """Relay new session events into the run record; settle idle sessions per plan rules."""
    run = app.state.store.snapshot()["runs"][run_id]
    if run["status"] != "running" or not run.get("session_id"):
        return run
    sid, events, page = run["session_id"], [], None
    while True:
        params = {"order": "asc", "limit": 100, **({"page": page} if page else {})}
        body = ma("GET", f"/sessions/{sid}/events", params=params)
        events += body.get("data", [])
        page = body.get("next_page")
        if not page:
            break
    status = ma("GET", f"/sessions/{sid}").get("status")

    def write(state):
        saved = state["runs"][run_id]
        # ponytail: re-lists the whole session each sweep; use webhooks + a cursor at volume.
        for event in events[saved.get("synced", 0) :]:
            entry = {
                "id": event.get("id"),
                "type": event.get("type"),
                "at": event.get("processed_at"),
            }
            if event.get("type") == "agent.message":
                entry["text"] = "".join(c.get("text", "") for c in event.get("content", []))
                saved["summary"] = entry["text"][-2000:]
            elif event.get("type") in {"agent.mcp_tool_use", "agent.tool_use"}:
                entry["tool"] = event.get("name")
            elif event.get("type") == "session.error":
                entry["error"] = json.dumps(event.get("error", event))[:2000]
            saved["transcript"].append(entry)
            publish(state, "agent_run.event", {"run_id": run_id, **entry})
        saved["transcript"] = saved["transcript"][-500:]
        saved["synced"] = len(events)
        if saved["status"] == "running" and status in {"idle", "terminated"}:
            if plan_complete(state["plans"].get(saved.get("plan_id") or "")):
                saved.update(status="done", next_wake_at=None)
                state.setdefault("mcp_sessions", {}).get(run_id, {})["revoked"] = True
                publish(state, "agent_run.done", {"run_id": run_id})
            else:  # mandatory timeout: an unfinished plan always wakes within 10 minutes
                schedule_wakeup(
                    state, run_id, MAX_SLEEP_MINUTES, reason="Turn ended with unfinished plan steps"
                )
        saved["updated_at"] = now()
        return saved

    return app.state.store.mutate(write)


def cancel(app, run_id):
    run = app.state.store.snapshot()["runs"][run_id]
    if run["status"] not in LIVE:
        raise ValueError(f"Run is already {run['status']}")
    if run.get("session_id"):
        config()

    def write(state):
        saved = state["runs"][run_id]
        saved.update(status="cancelled", next_wake_at=None, updated_at=now())
        for wakeup in state["wakeups"].values():
            if wakeup["run_id"] == run_id and wakeup["status"] == "pending":
                wakeup["status"] = "cancelled"
        state.setdefault("mcp_sessions", {}).get(run_id, {})["revoked"] = True
        publish(state, "agent_run.cancelled", {"run_id": run_id})
        return saved

    saved = app.state.store.mutate(write)
    if run.get("session_id"):
        ma(
            "POST",
            f"/sessions/{run['session_id']}/events",
            {"events": [{"type": "user.interrupt"}]},
        )
        ma("POST", f"/vaults/{run['vault_id']}/archive")
    start_queued(app)
    return saved


def due_wakeups(app):
    """Local/cron stand-in for Cloud Tasks: fire due timers, relay running runs, fill slots."""
    current = datetime.now(timezone.utc)
    state = app.state.store.snapshot()
    due = [
        w
        for w in state["wakeups"].values()
        if w["status"] == "pending" and datetime.fromisoformat(w["due_at"]) <= current
    ]
    woken = [
        wake(
            app,
            w["run_id"],
            f"timer expired after {w['minutes']} min ({w['reason']})",
            wakeup_id=w["id"],
        )
        for w in due
    ]
    synced = [sync(app, r["id"])["id"] for r in state["runs"].values() if r["status"] == "running"]
    started = [r["id"] for r in start_queued(app)]
    return {"woken": woken, "synced": synced, "started": started}


class RunStart(Input):
    goal: str = Field(min_length=1, max_length=4000)
    subjects: list[str] = Field(default_factory=list, max_length=50)


class Event(Input):
    kind: str = Field(min_length=1, max_length=100)
    subjects: list[str] = Field(default_factory=list, max_length=50)
    summary: str = Field(min_length=1, max_length=4000)
    data: dict = Field(default_factory=dict)


class Wake(Input):
    reason: str = Field(default="Woken", min_length=1, max_length=2000)
    wakeup_id: str | None = None


@router.post("/runs", status_code=201)
def start_run(payload: RunStart, request: Request):
    return create_run(request.app, payload.goal, payload.subjects)


@router.post("/events")
def ingest_event(payload: Event, request: Request):
    return route_event(request.app, payload.kind, payload.subjects, payload.summary, payload.data)


@router.post("/runs/{run_id}/wake")
def wake_run(run_id: str, payload: Wake, request: Request):
    request.app.state.store.snapshot()["runs"][run_id]
    return wake(request.app, run_id, payload.reason, wakeup_id=payload.wakeup_id)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request):
    return cancel(request.app, run_id)


@router.post("/runs/{run_id}/sync")
def sync_run(run_id: str, request: Request):
    return sync(request.app, run_id)


@router.post("/wakeups/due")
def process_due(request: Request):
    return due_wakeups(request.app)
