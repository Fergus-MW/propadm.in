"""Shared control checks at the single agent gateway and portal mutation boundary."""

from fastapi import HTTPException

from .portal_data import HUMAN_FLAGS, graph_items


def blocked(reason, rule, alternative):
    raise HTTPException(403, detail={"reason": reason, "rule": rule, "alternative": alternative})


def check_agent_control(state, run_id, name, args):
    # Read/plan tools remain available so the agent can explain its paused work.
    safe = {
        "get_portal_item",
        "draft_portal_reply",
        "search",
        "get_entity",
        "traverse",
        "get_document",
        "query_graph",
        "get_plan",
        "get_skill",
        "list_workflow_issues",
        "sleep",
        "create_plan",
        "update_step",
        "add_step",
        "revise_plan",
        "report_workflow_issue",
        "propose_skill_change",
    }
    if name in safe:
        return
    if state.get("portal", {}).get("settings", {}).get("paused"):
        blocked(
            "Automation is paused by a property manager",
            "global_pause",
            "Wait for a manager to resume automation",
        )
    subjects = set(state["runs"].get(run_id, {}).get("subjects", []))
    for key in (
        "id",
        "item_id",
        "entity_id",
        "email_id",
        "ticket_id",
        "source",
        "target",
        "target_id",
    ):
        if isinstance(args.get(key), str):
            subjects.add(args[key])
    subjects.update(args.get("entity_ids", []))

    def referenced_ids(value):
        if isinstance(value, dict):
            for nested in value.values():
                yield from referenced_ids(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from referenced_ids(nested)
        elif isinstance(value, str) and value in state["entities"]:
            yield value

    subjects.update(referenced_ids(args))
    # Include directly linked tickets when the tool targets a message or person.
    original_subjects = subjects.copy()
    for edge in state["edges"].values():
        if edge.get("source") in original_subjects or edge.get("target") in original_subjects:
            subjects.update([edge.get("source"), edge.get("target")])
    for item in graph_items(state):
        if item["id"] not in subjects:
            continue
        body = args.get("body", args)
        fields = body.get("fields", {}) if isinstance(body, dict) else {}
        category = state["entities"][item["id"]].get("fields", {}).get("category")
        is_repair = bool(category and category != "other")
        target_status = fields.get("status") if isinstance(fields, dict) else None
        if (
            is_repair
            and target_status in {"scheduled", "in progress"}
            and not item["approved"]
            and item["urgency"] != "Emergency"
        ):
            if (
                item["estimate"] is None
                or item["spend_limit"] is None
                or item["estimate"] > item["spend_limit"]
            ):
                blocked(
                    "Scheduling requires verified spend authority",
                    "spend_limit",
                    "Request a manager's approval through the portal",
                )
        if is_repair and target_status in {"resolved", "closed"} and not item.get("tenant_fixed"):
            blocked(
                "The tenant has not confirmed the fix",
                "completion",
                "Request tenant confirmation before completing the repair",
            )
        if item["autonomy"] < 3 or HUMAN_FLAGS.intersection(item["flags"]):
            blocked(
                "This item needs a human decision",
                "human_control",
                "Use the portal to review or hand back this item",
            )
