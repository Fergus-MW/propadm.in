"""Ledger/provider tools attached to the single graph MCP gateway."""

from .tools_agent import schema, text

ID = text(300)
FIELDS = {"type": "object", "additionalProperties": True}
EVIDENCE = {"type": "array", "items": {"type": "object", "additionalProperties": True}}
TRANSACTION = {
    "property_id": ID, "fields": FIELDS, "paid_by": ID, "paid_to": ID, "ticket_id": ID,
    "evidence": EVIDENCE, "source_file": ID, "settles": ID, "adjustment_deltas": FIELDS,
    "skill": ID,
}
CANONICAL = {
    "id": ID, "name": text(500), "description": {"type": "string", "maxLength": 20000},
    "fields": FIELDS, "version": {"type": "integer", "minimum": 1, "maximum": 2**53 - 1},
    "evidence": EVIDENCE,
}


def run(app, session, name, args):
    actor = f"agent_run:{session}"
    ledger, providers = app.state.ledger, app.state.providers
    if name == "get_property":
        from .routes_ledger import enrich_property

        return enrich_property(app, args["property"])
    if name == "get_ledger":
        return ledger.get_ledger(args["property"], args.get("from"), args.get("to"), args.get("category"))
    if name == "get_balances":
        return ledger.get_balances(args["subject"])
    if name == "get_unallocated":
        return {"items": ledger.unallocated()}
    if name == "record_transaction":
        from propadmin_core.graph import add_edge
        from propadmin_core.ledger import record_in_state

        from .tools_agent import skill_record

        values = dict(args)
        skill = values.pop("skill", None)

        def record(state):
            workflow = skill_record(state, skill) if skill else None
            result = record_in_state(state, values, actor=actor)
            if workflow and result["id"] in state["entities"]:
                edge = add_edge(state, result["id"], workflow["id"], "followed_skill")
                edge["skill_version"] = workflow["current_version"]
            return result

        return app.state.store.mutate(record)
    if name == "reverse_transaction":
        return reverse_with_workflow(app, args["tx"], args["reason"], actor=actor,
                                     skill=args.get("skill"), session=session)
    if name == "allocate":
        return ledger.allocate(args["tx"], args["property"], actor=actor,
                               category=args.get("category"), kind=args.get("kind"))
    if name == "settle":
        return ledger.settle(args["payment"], args["charge"], args.get("amount_minor"), actor=actor)
    if name == "generate_statement":
        from .statements import generate_statement

        return generate_statement(app, args["subject"], args["period"])
    if name == "find_providers":
        values = dict(args)
        if "property" in values:
            values["property_id"] = values.pop("property")
        return {"items": providers.find_providers(**values)}
    if name == "get_provider":
        return providers.get_provider(args["id"])
    if name in {"upsert_provider", "upsert_offering"}:
        values = dict(args)
        id = values.pop("id", None)
        provider_id = values.pop("provider", None)
        if name == "upsert_provider":
            return providers.upsert_provider(values, id=id, actor=actor)
        return providers.upsert_offering(values, provider_id, id=id, actor=actor)
    if name == "record_quote":
        return providers.record_quote(args["provider"], args["ticket"], {"fields": args["fields"]}, actor=actor)
    if name == "accept_quote":
        return providers.accept_quote(args["quote"], actor=actor)
    if name == "set_provider_status":
        return providers.set_provider_status(args["provider"], args["status"], args["reason"], actor=actor)
    raise ValueError("Unknown ledger tool")


def reverse_with_workflow(app, tx_id, reason, *, actor="admin", skill=None, session=None):
    from propadmin_core.graph import add_edge, create_in_state

    from .tools_agent import report_workflow_issue, skill_record

    state = app.state.store.snapshot()
    workflows = ({skill_record(state, skill)["id"]} if skill else
                 {edge["target"] for edge in state["edges"].values()
                  if edge["source"] == tx_id and edge["relation"] == "followed_skill"})
    for workflow in workflows:
        skill_record(state, workflow)
    result = app.state.ledger.reverse_transaction(tx_id, reason, actor=actor)
    for workflow in workflows:
        issue = report_workflow_issue(app, session or actor, {
            "skill": workflow, "category": "wrong_step", "severity": "high",
            "title": "Ledger correction caused by following this skill",
            "description": reason, "evidence": f"Original {tx_id}; reversal {result['id']}: {reason}",
            "related_entities": [tx_id, result["id"]],
        })

        def link_issue(state):
            if issue["id"] not in state["entities"]:
                create_in_state(state, {"id": issue["id"], "type": "workflow_issue",
                                       "name": issue["title"], "description": reason,
                                       "fields": {"title": issue["title"], "evidence": issue["evidence"][-1]["text"],
                                                  "category": "wrong_step", "severity": "high",
                                                  "status": "open", "occurrences": issue["occurrences"]}},
                                actor, "Ledger reversal workflow review")
            add_edge(state, issue["id"], workflow, "about_skill")
            add_edge(state, issue["id"], tx_id, "about")
            add_edge(state, issue["id"], result["id"], "about")

        app.state.store.mutate(link_issue)
    return result


def entry(name, description, properties, required=(), read=False):
    return {
        "description": description,
        "input_schema": schema(properties, required),
        "annotations": {"readOnlyHint": read, "destructiveHint": False,
                        "idempotentHint": read, "openWorldHint": False},
        "handler": lambda app, session, args: run(app, session, name, args),
    }


TOOLS = {
    "get_property": entry("get_property", "Property with owners, tenants, tickets and balances.",
                          {"property": ID}, ["property"], True),
    "get_ledger": entry("get_ledger", "Date-ordered ledger, evidence and running GBP balances.",
                        {"property": ID, "from": text(10), "to": text(10), "category": text(100)},
                        ["property"], True),
    "get_balances": entry("get_balances", "Property or weighted landlord position, in GBP pence.",
                          {"subject": ID}, ["subject"], True),
    "get_unallocated": entry("get_unallocated", "Staged source lines awaiting one property assignment.",
                             {}, [], True),
    "record_transaction": entry("record_transaction", "Append a validated financial record; never send money.",
                                TRANSACTION, ["fields"]),
    "reverse_transaction": entry("reverse_transaction", "Append a same-amount/category reversal; preserve the original.",
                                 {"tx": ID, "reason": text(2000), "skill": ID}, ["tx", "reason"]),
    "allocate": entry("allocate", "Assign a staged candidate; supply category/kind when classification is unresolved.",
                      {"tx": ID, "property": ID, "category": text(80),
                       "kind": {"type": "string", "enum": ["charge", "payment", "transfer", "adjustment"]}},
                      ["tx", "property"]),
    "settle": entry("settle", "Match cleared payments to charges, supporting partial settlement.",
                    {"payment": ID, "charge": ID,
                     "amount_minor": {"type": "integer", "minimum": 1, "maximum": 2**53-1}},
                    ["payment", "charge"]),
    "generate_statement": entry("generate_statement", "Create a property/landlord PDF stored as a source file.",
                                {"subject": ID, "period": text(7)}, ["subject", "period"]),
    "find_providers": entry("find_providers", "Rank qualified providers by coverage, urgency, quality and sourced prices.",
                            {"trade": text(100), "property": ID, "postcode": text(20),
                             "urgency": text(30), "service": text(200), "q": text(200),
                             "min_rating": {"type": "number", "minimum": 1, "maximum": 5}}, [], True),
    "get_provider": entry("get_provider", "Provider offerings, evidence, credentials, jobs, quotes and spend.",
                          {"id": ID}, ["id"], True),
    "upsert_provider": entry("upsert_provider", "Create or version-update a provider with source evidence.",
                             CANONICAL, ["fields"]),
    "upsert_offering": entry("upsert_offering", "Store a provider service price and confirmation date with evidence.",
                             {**CANONICAL, "provider": ID}, ["provider", "fields"]),
    "record_quote": entry("record_quote", "Record provider quote scope, price, timing and evidence.",
                          {"provider": ID, "ticket": ID, "fields": FIELDS}, ["provider", "ticket", "fields"]),
    "accept_quote": entry("accept_quote", "Assign a qualified provider and append expected expense; no payment.",
                          {"quote": ID}, ["quote"]),
    "set_provider_status": entry("set_provider_status", "Set preferred, approved, trial, suspended or do_not_use with reason.",
                                 {"provider": ID, "status": text(50), "reason": text(2000)},
                                 ["provider", "status", "reason"]),
}
