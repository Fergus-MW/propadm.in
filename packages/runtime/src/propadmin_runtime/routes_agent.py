"""API-side agent routes and MCP tools. Owned by the agent service build."""

from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from propadmin_core import ProviderNotConfigured
from propadmin_core.graph import add_edge, create_in_state
from propadmin_core.store import now, publish
from pydantic import Field

from .auth import require_admin
from .models import Input
from .routes_graph import stream_events
from .services import call_service
from .tools_agent import TOOLS  # noqa: F401  (wired into /mcp by mcp.py)

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


class CaseContext(Input):
    batch_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    case_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    attempt_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    input: dict = Field(default_factory=dict)


class RunCreate(Input):
    goal: str = Field(min_length=1, max_length=4000)
    subjects: list[str] = Field(default_factory=list, max_length=50)
    case: CaseContext | None = None


class Review(Input):
    decision: Literal["approved", "rejected", "changes_requested"]
    notes: str = Field(default="", max_length=10000)


def present(state, run):
    """Public run shape: plan and audited actions resolved, internal bookkeeping dropped."""
    hidden = {"vault_id", "synced", "pending_messages", "plan_id"}
    return {
        **{k: v for k, v in run.items() if k not in hidden},
        "plan": state["plans"].get(run.get("plan_id") or ""),
        "wakeups": [w for w in state["wakeups"].values() if w["run_id"] == run["id"]],
        "actions": [
            a
            for a in state["actions"].values()
            if a.get("session") == run["id"] or a.get("session_id") == run["id"]
        ],
    }


@router.get("/agent-runs")
def list_runs(request: Request):
    state = request.app.state.store.snapshot()
    runs = sorted(state["runs"].values(), key=lambda r: r["created_at"], reverse=True)
    return {"items": [present(state, run) for run in runs]}


@router.post("/agent-runs", status_code=201)
def create_run(payload: RunCreate, request: Request):
    return call_service(request.app.state.settings, "agent", "/internal/runs", payload.model_dump())


@router.get("/agent-runs/{run_id}")
def get_run(run_id: str, request: Request):
    state = request.app.state.store.snapshot()
    return present(state, state["runs"][run_id])


@router.get("/agent-runs/{run_id}/stream")
async def run_stream(run_id: str, request: Request, since: int = 0):
    request.app.state.store.snapshot()["runs"][run_id]
    try:
        cursor = max(0, int(request.headers.get("last-event-id", since)))
    except ValueError:
        raise HTTPException(400, "Invalid event cursor") from None
    return StreamingResponse(
        stream_events(request, cursor, run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/agent-runs/{run_id}/wake")
def wake_run(run_id: str, request: Request):
    return call_service(
        request.app.state.settings,
        "agent",
        f"/internal/runs/{run_id}/wake",
        {"reason": "Woken by an admin from the agent console"},
    )


@router.post("/agent-runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request):
    return call_service(request.app.state.settings, "agent", f"/internal/runs/{run_id}/cancel", {})


@router.post("/agent-runs/{run_id}/sync")
def sync_run(run_id: str, request: Request):
    return call_service(request.app.state.settings, "agent", f"/internal/runs/{run_id}/sync", {})


@router.get("/skills")
def list_skills(request: Request):
    skills = request.app.state.store.snapshot()["skills"].values()
    return {"items": sorted(skills, key=lambda s: s["slug"])}


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str, request: Request):
    state = request.app.state.store.snapshot()
    skill = state["skills"][skill_id]
    return {
        **skill,
        "issues": [i for i in state["issues"].values() if i["skill_id"] == skill_id],
        "proposals": [p for p in state["proposals"].values() if p["skill_id"] == skill_id],
    }


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@router.get("/workflow-issues")
def list_issues(request: Request, skill: str | None = None, status: str | None = None):
    items = [
        i
        for i in request.app.state.store.snapshot()["issues"].values()
        if (not skill or i["skill_id"] == skill) and (not status or i["status"] == status)
    ]
    items.sort(key=lambda i: (SEVERITY_RANK.get(i["severity"], 9), -i["occurrences"]))
    return {"items": items}


@router.get("/skill-proposals")
def list_proposals(request: Request, status: str | None = None):
    items = [
        p
        for p in request.app.state.store.snapshot()["proposals"].values()
        if not status or p["status"] == status
    ]
    return {"items": sorted(items, key=lambda p: p["created_at"], reverse=True)}


def publish_version(state, skill, proposal):
    """Approved proposal -> new skill_version entity + record, current edge moved."""
    version = skill["current_version"] + 1
    slug, previous = skill["slug"], f"skill_version:{skill['slug']}-v{skill['current_version']}"
    version_id = f"skill_version:{slug}-v{version}"
    create_in_state(
        state,
        {
            "id": version_id,
            "type": "skill_version",
            "name": f"{skill['name']} · version {version}",
            "description": proposal["reasoning"][:2000],
            "fields": {
                "version": version,
                "content": proposal["proposed_content"],
                "change_summary": proposal["expected_effect"],
                "created_by": "proposal",
                "published_at": now(),
            },
        },
        "admin",
        f"Approved {proposal['id']}",
    )
    state["edges"].pop(f"edge:{skill['id']}|current|{previous}|manual", None)
    add_edge(state, skill["id"], version_id, "current")
    add_edge(state, skill["id"], version_id, "has_version")
    if previous in state["entities"]:
        add_edge(state, version_id, previous, "supersedes")
    skill["versions"].append(
        {
            "version": version,
            "content": proposal["proposed_content"],
            "created_by": "proposal",
            "proposal_id": proposal["id"],
            "change_summary": proposal["expected_effect"],
            "created_at": now(),
        }
    )
    # ponytail: not yet uploaded to the Skills API / agent definition; deploy pipeline redeclares.
    skill.update(current_version=version, content=proposal["proposed_content"])
    return version


@router.post("/skill-proposals/{proposal_id}/review")
def review_proposal(proposal_id: str, payload: Review, request: Request):
    if payload.decision != "approved" and not payload.notes.strip():
        raise ValueError("Rejecting or requesting changes needs notes for the agent")

    def write(state):
        proposal = state["proposals"][proposal_id]
        if proposal["status"] != "pending_review":
            raise ValueError("Only pending proposals can be reviewed")
        skill = state["skills"][proposal["skill_id"]]
        if payload.decision == "approved":
            if proposal["based_on_version"] != skill["current_version"]:
                raise ValueError("Proposal is based on an outdated skill version")
            proposal["published_version"] = publish_version(state, skill, proposal)
        issue_status = {"approved": "resolved", "rejected": "open", "changes_requested": None}
        for issue_id in proposal["issues"]:
            if issue_status[payload.decision] and issue_id in state["issues"]:
                state["issues"][issue_id]["status"] = issue_status[payload.decision]
        proposal.update(
            status=payload.decision,
            review_notes=payload.notes,
            reviewed_by="admin",
            reviewed_at=now(),
        )
        publish(
            state, "skill_proposal.reviewed", {"id": proposal_id, "run_id": proposal["proposed_by"]}
        )
        return proposal

    proposal = request.app.state.store.mutate(write)
    if payload.decision == "changes_requested":
        try:  # Route the notes back to the proposing session; the review itself is already saved.
            call_service(
                request.app.state.settings,
                "agent",
                "/internal/events",
                {
                    "kind": "skill_proposal.changes_requested",
                    "subjects": [proposal_id],
                    "summary": f"Changes requested on {proposal_id}: {payload.notes}",
                    "data": {"proposal_id": proposal_id, "notes": payload.notes},
                },
            )
            proposal["agent_notified"] = True
        except (ProviderNotConfigured, ValueError, httpx.HTTPError):
            proposal["agent_notified"] = False
    return proposal
