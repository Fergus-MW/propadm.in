"""Match conversation evidence without joining unrelated messages by sender or mailbox."""


def related_emails(state, fields):
    references = set(fields.get("references") or [])
    if fields.get("in_reply_to"):
        references.add(fields["in_reply_to"])
    return [
        entity
        for entity in state["entities"].values()
        if entity["type"] == "email"
        and not entity.get("merged_into")
        and entity["fields"].get("mailbox") == fields.get("mailbox")
        and (
            bool(fields.get("thread_id"))
            and entity["fields"].get("thread_id") == fields["thread_id"]
            or entity["fields"].get("message_id") in references
        )
    ]


def conversation_context(state, fields):
    """Keep supplier responses linked to the ticket and routable even if thread ids change."""
    related = related_emails(state, fields)
    email_ids = {entity["id"] for entity in related}
    subjects = email_ids | {e["fields"]["thread_id"] for e in related if e["fields"].get("thread_id")}
    entity_ids = {
        edge["target"]
        for edge in state["edges"].values()
        if edge["source"] in email_ids and edge["relation"] == "about"
    }
    return sorted(subjects), sorted(entity_ids)
