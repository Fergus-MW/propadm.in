"""Explicitly approved replies through the existing email adapter, never simulated in live mode."""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from propadmin_core import ConflictError
from propadmin_core.store import now, publish
from pydantic import BaseModel, Field

from .auth import require_admin
from .portal_data import snapshot
from .portal_policy import blocked
from .services import call_service

router = APIRouter(prefix="/v1/portal", dependencies=[Depends(require_admin)])


class PortalReply(BaseModel):
    version: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=10000)
    request_id: UUID


@router.post("/items/{item_id}/send")
def send_reply(item_id: str, payload: PortalReply, request: Request, demo: bool = False):
    request_id = str(payload.request_id)
    text = payload.text.strip()
    if not text:
        raise ValueError("Write a reply before sending")

    def reserve(state):
        item = next((i for i in snapshot(state, demo)["items"] if i["id"] == item_id), None)
        if item is None:
            raise KeyError(item_id)
        receipts = state.setdefault("portal_deliveries", {})
        key = f"{demo}:{item_id}:{request_id}"
        if key in receipts:
            raise ConflictError(
                "This send has already been attempted. Check the email log before retrying."
            )
        if any(
            receipt.get("item_id") == item_id
            and receipt.get("demo") == demo
            and receipt["status"] in {"sending", "unconfirmed"}
            for receipt in receipts.values()
        ):
            raise ConflictError(
                "A previous send is in progress or unconfirmed. Check the email log before sending again."
            )
        if item["version"] != payload.version:
            raise ConflictError("The conversation changed. Refresh and review the reply again.")
        if item["role"] in {"Tenant", "Unknown"} and re.search(
            r"[£$€]|\b(?:GBP|USD|EUR|cost|costs|quote|invoice|spend|landlord details)\b", text, re.I
        ):
            blocked(
                "Tenant replies must not include repair costs or landlord details",
                "tenant_privacy",
                "Remove financial and landlord details before sending",
            )
        if "Fraud check" in item["flags"]:
            blocked(
                "Bank-detail changes require independent phone verification",
                "fraud_check",
                "Verify by a trusted phone number before replying",
            )
        if (
            any(f in item["flags"] for f in {"Human only", "Unlawful request", "Conflict"})
            and item["autonomy"] != 0
        ):
            blocked(
                "Take over before replying to this human-only matter",
                "human_only",
                "Take over, then write a reviewed reply",
            )
        incoming = next(
            (
                m
                for m in reversed(item["messages"])
                if m["direction"] == "inbound" and m["channel"] == "Email"
            ),
            None,
        )
        if not demo and incoming is None:
            raise ValueError(
                "No incoming email is linked. Open the canonical record and link the conversation first."
            )
        # A reservation also advances the revision, preventing a second send with the same record version.
        receipts[key] = dict(
            status="sending",
            at=now(),
            item_id=item_id,
            text=text,
            demo=demo,
            draft_before=item["draft"],
        )
        if demo:
            item["version"] += 1
        else:
            record = (
                state.setdefault("portal", {}).setdefault("records", {}).setdefault(item_id, {})
            )
            record["revision"] = record.get("revision", 0) + 1
        return incoming

    incoming = request.app.state.store.mutate(reserve)
    try:
        result = (
            {"status": "simulated"}
            if demo
            else call_service(
                request.app.state.settings,
                "email",
                "/internal/reply",
                {
                    "email_id": incoming["id"],
                    "body": text,
                    "reply_all": False,
                    "entity_ids": [item_id],
                },
            )
        )
    except Exception:

        def fail(state):
            state["portal_deliveries"][f"{demo}:{item_id}:{request_id}"]["status"] = "unconfirmed"
            publish(state, "portal.send_unconfirmed", {"id": item_id, "request_id": request_id})

        request.app.state.store.mutate(fail)
        # Do not automatically retry a provider timeout: the provider may have sent it.
        raise

    def finish(state):
        state["portal_deliveries"][f"{demo}:{item_id}:{request_id}"].update(
            status="simulated" if demo else "sent", result=result
        )
        event = dict(
            at=now(),
            actor="Property manager",
            action="Reply saved" if demo else "Email reply sent",
        )
        if demo:
            item = next(i for i in state["portal_demo"]["items"] if i["id"] == item_id)
            item["messages"].append(
                dict(
                    id=request_id,
                    author="You",
                    text=text,
                    channel="Email",
                    at=now(),
                    direction="outbound",
                )
            )
            if (
                item["draft"]
                == state["portal_deliveries"][f"{demo}:{item_id}:{request_id}"]["draft_before"]
            ):
                item["draft"] = ""
            item["version"] += 1
            item["timeline"].append(event)
        else:
            record = state["portal"]["records"][item_id]
            if (
                record.get("draft", "")
                == state["portal_deliveries"][f"{demo}:{item_id}:{request_id}"]["draft_before"]
            ):
                record["draft"] = ""
            record["revision"] = record.get("revision", 0) + 1
            record.setdefault("timeline", []).append(event)
        publish(state, "portal.message_sent", {"id": item_id, "demo": demo, **event})
        return result

    return request.app.state.store.mutate(finish)


class DeliveryReview(BaseModel):
    sent: bool
    evidence: str = Field(min_length=3, max_length=4000)


@router.post("/items/{item_id}/delivery-review")
def review_delivery(item_id: str, payload: DeliveryReview, request: Request):
    from datetime import datetime, timedelta

    if not payload.evidence.strip():
        raise ValueError("Record how you verified delivery")

    def write(state):
        pending = [
            r
            for r in state.get("portal_deliveries", {}).values()
            if r["item_id"] == item_id
            and not r.get("demo")
            and r["status"] in {"sending", "unconfirmed"}
        ]
        if not pending:
            raise ValueError("No uncertain delivery to review")
        if any(
            r["status"] == "sending"
            and datetime.fromisoformat(r["at"])
            > datetime.fromisoformat(now()) - timedelta(minutes=5)
            for r in pending
        ):
            raise ConflictError("Delivery is still in progress. Wait for the request to finish.")
        for receipt in pending:
            receipt.update(
                status="verified_sent" if payload.sent else "verified_not_sent",
                evidence=payload.evidence,
            )
        record = state.setdefault("portal", {}).setdefault("records", {}).setdefault(item_id, {})
        record["revision"] = record.get("revision", 0) + 1
        event = dict(
            at=now(), actor="Property manager", action="Delivery reviewed", detail=payload.evidence
        )
        record.setdefault("timeline", []).append(event)
        publish(state, "portal.delivery_reviewed", {"id": item_id, "sent": payload.sent, **event})
        return {"reviewed": True}

    return request.app.state.store.mutate(write)
