"""Expiring, revocable repair links with server-side audience projections."""

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from propadmin_core.store import identifier, now, publish
from pydantic import BaseModel

from .auth import bearer, issue_token, require_admin, verify_token
from .portal_data import EMERGENCY_STAGES, STAGES, snapshot
from .portal_policy import blocked

router = APIRouter(prefix="/v1/portal")
TENANT_STAGES = [
    "We've got your report",
    "Tell us a bit more",
    "Your repair has been assessed",
    "Getting approval",
    "Finding the right person",
    "Your visit is booked",
    "You're confirmed",
    "On the way",
    "Work in progress",
    "Is everything working?",
    "All done",
    "Closed",
]


class ShareRepair(BaseModel):
    audience: Literal["tenant", "landlord"]


@router.post("/items/{item_id}/share", dependencies=[Depends(require_admin)])
def share(item_id: str, payload: ShareRepair, request: Request, demo: bool = False):
    def write(state):
        if not any(i["id"] == item_id for i in snapshot(state, demo)["items"]):
            raise KeyError(item_id)
        key = identifier("share")
        state.setdefault("portal_shares", {})[key] = dict(
            item_id=item_id, audience=payload.audience, demo=demo, created_at=now()
        )
        publish(
            state,
            "portal.share_created",
            {"id": key, "item_id": item_id, "audience": payload.audience, "actor": "admin"},
        )
        return {
            "id": key,
            "token": issue_token(request.app.state.settings, actor=f"repair:{key}", lifetime=86400),
            "expires_in": 86400,
        }

    return request.app.state.store.mutate(write)


@router.delete("/shares/{share_id}", dependencies=[Depends(require_admin)])
def revoke(share_id: str, request: Request):
    def write(state):
        state.get("portal_shares", {}).pop(share_id, None)
        publish(state, "portal.share_revoked", {"id": share_id, "actor": "admin"})
        return {"revoked": True}

    return request.app.state.store.mutate(write)


@router.get("/shared")
def shared(request: Request, response: Response):
    actor = verify_token(request.app.state.settings, bearer(request))
    if not actor.startswith("repair:"):
        blocked(
            "This is not a repair link", "share_scope", "Ask your property manager for a new link"
        )
    state = request.app.state.store.snapshot()
    grant = state.get("portal_shares", {}).get(actor.removeprefix("repair:"))
    if not grant:
        raise KeyError("Share no longer available")
    item = next(
        (i for i in snapshot(state, grant["demo"])["items"] if i["id"] == grant["item_id"]), None
    )
    if item is None:
        raise KeyError("Repair no longer available")
    # Explicit allow-list. Never copy messages, internal flags, notes or evidence into a shared response.
    stages = (
        EMERGENCY_STAGES
        if item["emergency"]
        else TENANT_STAGES
        if grant["audience"] == "tenant"
        else STAGES
    )
    result = dict(
        audience=grant["audience"],
        demo=grant["demo"],
        property=item["property"],
        stage=item["stage"],
        steps=stages,
        contractor=item["contractor"],
        eta=item["eta"],
        reported_at=item["reported_at"],
        title="Repair update",
    )
    if grant["audience"] == "landlord":
        result.update(estimate=item["estimate"], approved=item["approved"])
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return result
