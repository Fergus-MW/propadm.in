"""Authenticated property manager workspace over the existing durable repository."""

from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from propadmin_core import ConflictError
from propadmin_core.store import identifier, now, publish
from pydantic import BaseModel, Field

from .auth import require_admin
from .portal_data import EMERGENCY_STAGES, HUMAN_FLAGS, STAGES, demo_data, snapshot
from .portal_emergency import activate, end_emergency
from .portal_policy import blocked
from .portal_tanner import tanner_items

router = APIRouter(prefix="/v1/portal", dependencies=[Depends(require_admin)])


class PortalCommand(BaseModel):
    version: int = Field(ge=1)
    action: Literal[
        "takeover",
        "handback",
        "approve",
        "reject",
        "draft",
        "note",
        "stage",
        "urgency",
        "confirm_fix",
        "reopen",
        "authority",
        "emergency_override",
        "emergency_stand_down",
    ]
    text: str = Field(default="", max_length=10000)
    value: str = Field(default="", max_length=200)


class PortalSettings(BaseModel):
    paused: bool


class TripRequest(BaseModel):
    prospect_id: str | None = None
    property_ids: list[str] = Field(min_length=1, max_length=5)
    start: datetime
    end: datetime
    travel_minutes: int = Field(default=15, ge=5, le=120)


@router.get("")
def workspace(request: Request, demo: bool = False):
    return snapshot(request.app.state.store.snapshot(), demo)


@router.post("/demo")
def initialise_demo(request: Request):
    def write(state):
        if not state.get("portal_demo", {}).get("items"):
            state["portal_demo"] = demo_data()
        existing = {item["id"] for item in state["portal_demo"]["items"]}
        state["portal_demo"]["items"].extend(
            item for item in tanner_items() if item["id"] not in existing
        )
        return snapshot(state, True)

    return request.app.state.store.mutate(write)


@router.patch("/settings")
def settings(payload: PortalSettings, request: Request, demo: bool = False):
    def write(state):
        root = state.setdefault("portal_demo" if demo else "portal", demo_data() if demo else {})
        root["settings"] = payload.model_dump()
        publish(state, "portal.settings", {**payload.model_dump(), "actor": "admin", "demo": demo})
        return root["settings"]

    return request.app.state.store.mutate(write)


@router.post("/items/{item_id}/command")
def command(item_id: str, payload: PortalCommand, request: Request, demo: bool = False):
    def write(state):
        data = snapshot(state, demo)
        item = next((i for i in data["items"] if i["id"] == item_id), None)
        if item is None:
            raise KeyError(item_id)
        if item["version"] != payload.version:
            raise ConflictError("This record changed. Refresh before trying again.")
        action, text = payload.action, payload.text.strip()
        if (
            action
            in {
                "reject",
                "note",
                "stage",
                "urgency",
                "authority",
                "emergency_override",
                "emergency_stand_down",
            }
            and not text
        ):
            raise ValueError("Add a reason so the next person knows what changed")
        if action == "emergency_override" or (action == "urgency" and payload.value == "Emergency"):
            if item["emergency"]:
                raise ValueError("Make-safe is already active; record its progress instead")
            activate(item, text)
            action = "emergency_override"
        elif action == "emergency_stand_down":
            if item["emergency"]:
                raise ValueError("Record Made safe before ending an active make-safe response")
            if item["urgency"] != "Emergency":
                raise ValueError("There is no emergency concern to review")
            end_emergency(item)
        elif action == "takeover":
            item["autonomy"] = 0
        elif action == "handback":
            if item["urgency"] == "Emergency" or HUMAN_FLAGS.intersection(item["flags"]):
                blocked(
                    "Always-human decisions cannot be handed to AI",
                    "human_only",
                    "Keep this item with a property manager",
                )
            item["autonomy"] = 2 if item["confidence"] != "High" else 3
            item["instruction"] = text
        elif action == "authority":
            amount = float(payload.value)
            if not isfinite(amount) or amount < 0 or amount > 100000:
                raise ValueError("Use a spend limit between £0 and £100,000")
            item["spend_limit"] = amount
            item["approved"] = False
        elif action == "approve":
            if HUMAN_FLAGS.intersection(item["flags"]):
                blocked(
                    "Resolve the human-only review first",
                    "human_only",
                    "Take over and record the decision",
                )
            if item["estimate"] is None or item["spend_limit"] is None:
                blocked(
                    "The quote or spend limit is missing",
                    "missing_evidence",
                    "Verify the management agreement and quote",
                )
            if item["estimate"] > item["spend_limit"] and not text:
                blocked(
                    "Record evidence of landlord approval for over-limit spend",
                    "landlord_approval",
                    "Add the approval source to the decision reason",
                )
            # PM approval records the decision; it never pretends a contractor is booked.
            item["approved"] = True
            item["flags"] = [
                f for f in item["flags"] if f not in {"Needs your OK", "Waiting on landlord"}
            ]
            if not item["emergency"] and item["stage"] == 3:
                item["stage"] = 4
        elif action == "reject":
            item["approved"] = False
            item["autonomy"] = 0
        elif action == "draft":
            item["draft"] = text
        elif action == "stage":
            stages = EMERGENCY_STAGES if item["emergency"] else STAGES
            if payload.value not in stages:
                raise ValueError("Choose a valid progress stage")
            target = stages.index(payload.value)
            if not item["emergency"] and target >= 5:
                if item["urgency"] == "Emergency":
                    blocked(
                        "Review suspected danger before proceeding",
                        "emergency_review",
                        "Activate make-safe or rule out the emergency with evidence",
                    )
                if (
                    item["estimate"] is None
                    or item["spend_limit"] is None
                    or item["estimate"] > item["spend_limit"]
                ) and not item["approved"]:
                    blocked(
                        "Booking requires verified spend authority",
                        "spend_limit",
                        "Record approval before booking",
                    )
            if not item["emergency"] and target >= 10 and not item.get("tenant_fixed"):
                blocked(
                    "The tenant has not confirmed the fix",
                    "completion",
                    "Record tenant confirmation first",
                )
            item["stage"] = target
            if item["emergency"] and target == len(EMERGENCY_STAGES) - 1:
                # Making safe ends the emergency phase, not the underlying repair.
                end_emergency(item)
        elif action == "urgency":
            levels = ["Routine", "Urgent", "Emergency"]
            if payload.value not in levels:
                raise ValueError("Choose a valid urgency")
            if item["urgency"] == "Emergency":
                blocked(
                    "Review the emergency before lowering urgency",
                    "emergency_review",
                    "Record Made safe, or rule out a suspected emergency with evidence",
                )
            item["urgency"] = payload.value
            item["flags"] = [f for f in item["flags"] if f != "Emergency"]
            if payload.value == "Emergency":
                item["flags"].append("Emergency")
        elif action == "confirm_fix":
            if item["emergency"] or item["stage"] != 9:
                raise ValueError("Tenant confirmation is recorded at the Fixed? stage")
            if not text:
                raise ValueError("Record the tenant's confirmation and its source")
            item["tenant_fixed"] = True
        elif action == "reopen":
            if item["urgency"] == "Emergency":
                raise ValueError("Resolve the emergency review before reopening a standard repair")
            item["approved"] = False
            item["stage"] = 2
            item["emergency"] = False
            item["tenant_fixed"] = False
        event = dict(
            at=now(),
            actor="Property manager",
            action=action,
            detail=f"{payload.value} — {text}" if payload.value else text,
            value=payload.value,
        )
        item["timeline"] = [*item["timeline"], event]
        item["version"] += 1
        if not demo:
            # Only control metadata is overlaid; ticket evidence stays authoritative.
            keys = (
                "autonomy",
                "instruction",
                "approved",
                "flags",
                "stage",
                "urgency",
                "draft",
                "timeline",
                "tenant_fixed",
                "emergency",
                "spend_limit",
                "emergency_reason",
                "emergency_reviewed_evidence",
                "waiting_on",
            )
            records = state.setdefault("portal", {}).setdefault("records", {})
            previous = records.get(item_id, {})
            records[item_id] = {**previous, **{k: item[k] for k in keys if k in item}}
            records[item_id]["revision"] = previous.get("revision", 0) + 1
        publish(state, "portal.item_changed", {"id": item_id, "demo": demo, **event})
        return item

    return request.app.state.store.mutate(write)


@router.post("/trips/propose")
def propose(payload: TripRequest, request: Request, demo: bool = False):
    def write(state):
        root = state.setdefault("portal_demo" if demo else "portal", demo_data() if demo else {})
        data = snapshot(state, demo)
        if payload.start.tzinfo is None or payload.end.tzinfo is None:
            raise ValueError("Availability must include a timezone")
        if len(set(payload.property_ids)) != len(payload.property_ids):
            raise ValueError("Choose each property once")
        prospect = data["prospect"] if demo else root.get("prospects", {}).get(payload.prospect_id)
        if not prospect:
            raise HTTPException(409, "Save prospect availability before proposing a trip")
        start = max(payload.start, datetime.fromisoformat(prospect["start"]))
        end = min(payload.end, datetime.fromisoformat(prospect["end"]))
        cursor, visits = start, []
        for prop_id in payload.property_ids:
            prop = next((p for p in data["properties"] if p["id"] == prop_id), None)
            if prop is None:
                raise KeyError(prop_id)
            if not prop["compliant"] or (prop["occupied"] and not prop["consent"]):
                blocked(
                    f"{prop['name']} needs compliance clearance or tenant consent",
                    "viewing_access",
                    "Select a cleared property or obtain tenant consent",
                )
            if not prop.get("start") or not prop.get("end"):
                raise ValueError("Record the property's viewing window before booking")
            cursor = max(cursor, datetime.fromisoformat(prop["start"]))
            finish = cursor + timedelta(minutes=30)
            if cursor < datetime.fromisoformat(now()) + timedelta(hours=prop["notice_hours"]):
                blocked("Minimum viewing notice is not met", "notice", "Choose a later time")
            if finish > min(end, datetime.fromisoformat(prop["end"])):
                raise ValueError("These viewings and travel do not fit the availability window")
            for trip in data["trips"]:
                if trip["status"] == "Confirmed" and conflicts(
                    cursor, finish, prop_id, prospect["id"], payload.travel_minutes, trip
                ):
                    raise ConflictError(
                        "A viewing or its travel buffer conflicts with a confirmed trip"
                    )
            visits.append(
                dict(
                    property_id=prop_id,
                    property=prop["name"],
                    start=cursor.astimezone(timezone.utc).isoformat(),
                    end=finish.astimezone(timezone.utc).isoformat(),
                )
            )
            cursor = finish + timedelta(minutes=payload.travel_minutes)
        trip = dict(
            id=identifier("trip"),
            prospect=prospect["name"],
            prospect_id=prospect["id"],
            visits=visits,
            travel_minutes=payload.travel_minutes,
            status="Proposed",
            version=1,
        )
        root.setdefault("trips", []).append(trip)
        publish(state, "portal.trip_proposed", {"id": trip["id"], "demo": demo, "actor": "admin"})
        return trip

    return request.app.state.store.mutate(write)


@router.post("/trips/{trip_id}/confirm")
def confirm_trip(trip_id: str, request: Request, demo: bool = False):
    def write(state):
        data = snapshot(state, demo)
        trip = next((t for t in data["trips"] if t["id"] == trip_id), None)
        if trip is None:
            raise KeyError(trip_id)
        if trip["status"] == "Confirmed":
            return trip
        prospect = (
            data["prospect"]
            if demo
            else state.get("portal", {}).get("prospects", {}).get(trip.get("prospect_id"))
        )
        if not prospect:
            raise ConflictError("Prospect availability is no longer available")
        for visit in trip["visits"]:
            prop = next((p for p in data["properties"] if p["id"] == visit["property_id"]), None)
            if prop is None:
                raise ConflictError("A property is no longer available")
            start, end = (
                datetime.fromisoformat(visit["start"]),
                datetime.fromisoformat(visit["end"]),
            )
            if (
                not prop.get("start")
                or not prop.get("end")
                or start
                < max(
                    datetime.fromisoformat(prop["start"]), datetime.fromisoformat(prospect["start"])
                )
                or end
                > min(datetime.fromisoformat(prop["end"]), datetime.fromisoformat(prospect["end"]))
                or start < datetime.fromisoformat(now()) + timedelta(hours=prop["notice_hours"])
            ):
                blocked(
                    "Availability or required notice changed",
                    "viewing_window",
                    "Propose a new trip",
                )
            if not prop["compliant"] or (prop["occupied"] and not prop["consent"]):
                blocked("Viewing rules changed", "viewing_access", "Propose a new trip")
            for other in data["trips"]:
                if other["status"] == "Confirmed" and conflicts(
                    start,
                    end,
                    visit["property_id"],
                    trip.get("prospect_id"),
                    trip["travel_minutes"],
                    other,
                ):
                    raise ConflictError("Another trip has reserved this time. Propose a new trip.")
        trip["status"] = "Confirmed"
        trip["version"] += 1
        publish(state, "portal.trip_confirmed", {"id": trip_id, "demo": demo, "actor": "admin"})
        return trip

    return request.app.state.store.mutate(write)


def conflicts(start, end, property_id, prospect_id, travel_minutes, other):
    """Conflicts include travel between separate itineraries for the same prospect."""
    same_person = other.get("prospect_id") == prospect_id
    for visit in other["visits"]:
        same_property = visit["property_id"] == property_id
        if not same_person and not same_property:
            continue
        buffer = timedelta(
            minutes=max(travel_minutes, other["travel_minutes"])
            if same_person and not same_property
            else 0
        )
        if (
            start < datetime.fromisoformat(visit["end"]) + buffer
            and end > datetime.fromisoformat(visit["start"]) - buffer
        ):
            return True
    return False
