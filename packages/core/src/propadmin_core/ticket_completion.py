"""Ticket completion contract and honest backfill of historical records."""

import copy

from .store import now, publish

COMPLETED_STATUSES = frozenset({"resolved", "closed"})
COMPLETION_FIELDS = ("final_answer", "reasoning")
COMPLETION_INSTRUCTIONS = (
    "Before setting a ticket to resolved or closed, write both fields.final_answer and "
    "fields.reasoning as Markdown in the same update. final_answer states the answer or "
    "query result, or whether the instruction was executed; if not, state why. reasoning "
    "is a detailed, evidence-based explanation: document every observable step in order, "
    "sources and record/tool-result references, actions attempted, results, verification, "
    "failures, skipped actions and their reasons, and remaining limitations. Explain how "
    "that evidence supports the final outcome. Be as thorough as the available evidence "
    "allows; do not truncate the audit trail or invent steps. Provide an explanation for "
    "the reader, not hidden model thoughts or private chain-of-thought."
)


def validate_completion(type_name, fields):
    if type_name != "ticket":
        return
    for key in COMPLETION_FIELDS:
        fields.setdefault(key, "")
        if fields.get("status") in COMPLETED_STATUSES and not fields[key].strip():
            raise ValueError(f"Completed tickets require a non-empty {key}")


def upgrade_ticket_completion(state, definitions, embedder):
    """Preserve custom schemas and outcomes; never reconstruct unrecorded deliberations."""
    schema = state["entity_types"]["ticket"]
    schema_changed = False
    for key in COMPLETION_FIELDS:
        spec = definitions["ticket"]["fields"][key]
        if schema["fields"].get(key) != spec:
            schema["fields"][key] = copy.deepcopy(spec)
            schema_changed = True
    if schema_changed:
        schema["version"] += 1
    changed = schema_changed
    for ticket in state["entities"].values():
        if ticket["type"] != "ticket":
            continue
        fields = ticket["fields"]
        before = copy.deepcopy(fields)
        for key in COMPLETION_FIELDS:
            fields.setdefault(key, "")
        if fields.get("status") in COMPLETED_STATUSES:
            if not fields["final_answer"].strip():
                fields["final_answer"] = fields.get("resolution", "").strip() or (
                    "No final answer was recorded for this historical completed ticket. "
                    "Whether the requested instruction was executed, and its result, "
                    "cannot be established from a completion status alone."
                )
            if not fields["reasoning"].strip():
                fields["reasoning"] = (
                    "# Historical completion record\n\n"
                    "This ticket predates the required completion fields. An original "
                    "explanation and complete sequence of steps were not recorded.\n\n"
                    f"- Ticket: `{ticket['id']}`\n"
                    f"- Recorded status: {fields['status']}\n"
                    f"- Recorded completion time: {fields.get('resolved_at') or 'Not recorded'}\n\n"
                    "The final answer preserves the existing resolution where available. "
                    "This backfill does not independently verify that outcome or infer "
                    "unrecorded actions. Consult the ticket's evidence and activity history "
                    "for any surviving source records."
                )
        if fields != before:
            ticket.update(version=ticket["version"] + 1, updated_at=now())
            embedder.entity(state, ticket)
            changed = True
    if changed:
        publish(state, "registry.upgraded", {"feature": "ticket_completion"})
    return changed
