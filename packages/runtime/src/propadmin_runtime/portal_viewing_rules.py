"""Evidence-backed availability and viewing rules for canonical graph records."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from propadmin_core.store import now, publish
from pydantic import BaseModel, Field

from .auth import require_admin

router = APIRouter(prefix="/v1/portal", dependencies=[Depends(require_admin)])


class ViewingRules(BaseModel):
    occupied: bool
    consent: bool
    compliant: bool
    notice_hours: int = Field(default=24, ge=24, le=720)
    start: datetime
    end: datetime
    evidence: str = Field(min_length=3, max_length=4000)


class ProspectAvailability(BaseModel):
    person_id: str = Field(min_length=1, max_length=200)
    budget: float = Field(gt=0, le=100000)
    start: datetime
    end: datetime
    evidence: str = Field(min_length=3, max_length=4000)


def check_window(start, end):
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("Use timezone-aware times with the end after the start")
    if end <= datetime.fromisoformat(now()):
        raise ValueError("Choose future availability")


@router.put("/properties/{property_id}/viewing-rules")
def viewing_rules(property_id: str, payload: ViewingRules, request: Request):
    check_window(payload.start, payload.end)
    if not payload.evidence.strip():
        raise ValueError("Record the consent and compliance evidence")

    def write(state):
        entity = state["entities"][property_id]
        if entity["type"] != "property" or entity.get("merged_into"):
            raise KeyError(property_id)
        rules = payload.model_dump(mode="json")
        state.setdefault("portal", {}).setdefault("viewing_rules", {})[property_id] = rules
        publish(
            state, "portal.viewing_rules", {"id": property_id, "actor": "admin", "rules": rules}
        )
        return rules

    return request.app.state.store.mutate(write)


@router.put("/prospects/availability")
def prospect_availability(payload: ProspectAvailability, request: Request):
    check_window(payload.start, payload.end)
    if not payload.evidence.strip():
        raise ValueError("Record the source of this availability")

    def write(state):
        entity = state["entities"][payload.person_id]
        if entity["type"] != "person" or entity.get("merged_into"):
            raise KeyError(payload.person_id)
        prospect = {**payload.model_dump(mode="json"), "id": entity["id"], "name": entity["name"]}
        state.setdefault("portal", {}).setdefault("prospects", {})[entity["id"]] = prospect
        publish(
            state,
            "portal.prospect_availability",
            {"id": entity["id"], "actor": "admin", "availability": prospect},
        )
        return prospect

    return request.app.state.store.mutate(write)
