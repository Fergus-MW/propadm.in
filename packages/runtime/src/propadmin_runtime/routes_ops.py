"""Read-only communications logs, graph audit undo and runtime status."""

from fastapi import APIRouter, Depends, Request
from propadmin_core import ConflictError

from .auth import require_admin

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


@router.get("/actions")
def actions(request: Request, session: str | None = None, subject: str | None = None):
    items = request.app.state.store.snapshot()["actions"].values()
    items = [
        a
        for a in items
        if (not session or a.get("session") == session or a.get("actor") == f"agent_run:{session}")
        and (not subject or a.get("entity_id") == subject or subject in str(a.get("arguments", {})))
    ]
    return {"items": sorted(items, key=lambda a: a.get("created_at", ""), reverse=True)}


@router.post("/actions/{action_id}/undo")
def undo(action_id: str, request: Request):
    state = request.app.state.store.snapshot()
    action = state["actions"][action_id]
    change = state["changes"].get(action.get("change_id"))
    if not change or not change.get("before") or change.get("action") != "entity.updated":
        raise ValueError("Only entity updates with a previous value can be undone")
    entity_id = change["entity_id"]
    before = change["before"]
    current = request.app.state.graph.get_entity(entity_id)
    if current["version"] != change["after"]["version"]:
        raise ConflictError("Record changed after this action; cannot undo a newer edit")
    schema = state["entity_types"][current["type"]]["fields"]
    fields = {
        key: value for key, value in before.get("fields", {}).items()
        if not schema.get(key, {}).get("read_only")
    }
    return request.app.state.graph.update_entity(
        entity_id,
        {
            "version": current["version"],
            "name": before["name"],
            "description": before.get("description", ""),
            "fields": fields,
            "aliases": before.get("aliases", []),
            "description_pinned": before.get("description_pinned", False),
        },
        reason=f"Undo {action_id}",
    )


@router.get("/calls")
def calls(request: Request):
    return {"items": request.app.state.graph.list_entities(type="call")}


@router.get("/calls/{call_id}")
def call(call_id: str, request: Request):
    result = request.app.state.graph.get_entity(call_id)
    if result["type"] != "call":
        raise KeyError(call_id)
    return result


@router.get("/emails")
def emails(request: Request):
    return {"items": request.app.state.graph.list_entities(type="email")}


@router.get("/emails/{email_id}")
def email(email_id: str, request: Request):
    result = request.app.state.graph.get_entity(email_id)
    if result["type"] != "email":
        raise KeyError(email_id)
    return result


@router.get("/settings")
def settings(request: Request):
    return request.app.state.settings.public()
