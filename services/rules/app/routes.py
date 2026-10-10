"""Internal rules endpoints: Pub/Sub push, full recompute and the rule compiler."""

import base64
import json

from fastapi import APIRouter, Depends, Request
from propadmin_core.layout import apply_layout
from propadmin_core.rules import recompute_enabled, safe_apply
from propadmin_runtime.auth import require_internal

router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])


def full_recompute(store):
    def run(state):
        rules = recompute_enabled(state)
        return {"rules": rules, "layout": apply_layout(state)}

    return store.mutate(run)


def incremental(store, event):
    def run(state):
        kind = event.get("kind")
        if kind == "rule.changed":
            rules = {event["rule_id"]: safe_apply(state, state["rules"][event["rule_id"]])}
        elif kind == "entity.changed":
            entity = state["entities"].get(event.get("entity_id"))
            # Deleted entity: fall back to a full pass so no dangling rule edges remain.
            rules = recompute_enabled(state, entity["type"] if entity else None)
        else:
            raise ValueError("Event kind must be entity.changed or rule.changed")
        return {"rules": rules, "layout": apply_layout(state)}

    return store.mutate(run)


@router.post("/events")
async def events(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        raise ValueError("Event must be a JSON object")
    if "message" in payload:
        try:
            payload = json.loads(base64.b64decode(payload["message"]["data"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid Pub/Sub envelope") from exc
    return incremental(request.app.state.store, payload)


@router.post("/recompute")
def recompute(request: Request):
    return full_recompute(request.app.state.store)


@router.post("/compile")
def compile_rule(payload: dict, request: Request):
    return request.app.state.rules.compile(payload.get("prompt"))
