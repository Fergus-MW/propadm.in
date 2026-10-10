"""Portal context and draft proposals on the existing single agent MCP endpoint."""

from propadmin_core import ConflictError
from propadmin_core.store import now, publish

from .portal_data import snapshot


def get_item(app, run_id, args):
    item = next(
        (i for i in snapshot(app.state.store.snapshot())["items"] if i["id"] == args["item_id"]),
        None,
    )
    if item is None:
        raise KeyError(args["item_id"])
    return item


def draft_reply(app, run_id, args):
    if not args["source_ids"] or not args["reasons"]:
        raise ValueError("Provide evidence and reasons for the draft")

    def write(state):
        item = next((i for i in snapshot(state)["items"] if i["id"] == args["item_id"]), None)
        if item is None:
            raise KeyError(args["item_id"])
        if item["version"] != args["version"]:
            raise ConflictError("The manager or source record changed. Read the portal item again.")
        facts = []
        for source_id in args["source_ids"]:
            source = state["entities"].get(source_id)
            if not source or source.get("merged_into"):
                raise ValueError("Every cited fact must refer to an existing canonical entity")
            facts.append({"id": source_id, "label": source["name"]})
        record = state.setdefault("portal", {}).setdefault("records", {}).setdefault(item["id"], {})
        if item["autonomy"] == 0 and item["draft"]:
            raise ConflictError("A human has a saved draft on this paused item; do not replace it")
        record.update(
            draft=args["text"],
            confidence=args["confidence"],
            reasons=args["reasons"],
            facts=facts,
            revision=record.get("revision", 0) + 1,
        )
        # A proposal always awaits review; low confidence cannot silently retain Autopilot.
        record["autonomy"] = min(item["autonomy"], 2)
        if args["confidence"] == "Low":
            record["flags"] = list(dict.fromkeys([*item["flags"], "Low confidence"]))
        record.setdefault("timeline", []).append(
            dict(
                at=now(),
                actor=f"AI · {run_id}",
                action="Draft proposed",
                detail="Awaiting human review",
            )
        )
        publish(state, "portal.ai_drafted", {"id": item["id"], "run_id": run_id})
        return next(i for i in snapshot(state)["items"] if i["id"] == item["id"])

    return app.state.store.mutate(write)


TEXT = {"type": "string", "minLength": 1, "maxLength": 10000}
ID = {"type": "string", "minLength": 1, "maxLength": 500}
TOOLS = {
    "get_portal_item": {
        "description": "Read a manager portal ticket, current version, controls, evidence, draft and timeline before proposing a reply.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": ID},
            "required": ["item_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
        "handler": get_item,
    },
    "draft_portal_reply": {
        "description": "Propose a reply for a property manager to edit and approve. Never sends a message. Cite canonical entity IDs and explain the proposal. Allowed while an item is paused, but cannot overwrite a human's saved draft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": ID,
                "version": {"type": "integer", "minimum": 1, "maximum": 2**53 - 1},
                "text": TEXT,
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "reasons": {"type": "array", "items": TEXT, "minItems": 1, "maxItems": 5},
                "source_ids": {"type": "array", "items": ID, "minItems": 1, "maxItems": 20},
            },
            "required": ["item_id", "version", "text", "confidence", "reasons", "source_ids"],
            "additionalProperties": False,
        },
        "handler": draft_reply,
    },
}
