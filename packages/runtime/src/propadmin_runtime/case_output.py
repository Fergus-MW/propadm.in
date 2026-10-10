"""Render case evidence from existing agent messages, plans and audited actions."""

import json
import re

SECTIONS = (
    "Final result",
    "Outputs and decisions",
    "Actions taken",
    "Escalations",
    "Checks and rationale",
    "Conflicts and uncertainty",
    "Failures",
)
CLOSING_INSTRUCTIONS = (
    "When this case attempt ends, use your normal final message to give a concise, "
    "evidence-based conclusion with these exact Markdown headings:\n"
    + "\n".join(f"## {name}" for name in SECTIONS)
    + "\nPut content under every heading. Explicitly say 'None' when no escalation or "
    "failure occurred; say 'Unknown' when you cannot establish that. Include unresolved "
    "work and cite tool results or entity IDs. Distinguish actions actually performed "
    "from proposals and historical events supplied in the input. An escalation is only "
    "delivered if the communication result supports it. Never invent evidence."
)


def closing_sections(message):
    """Recognise labelled sections in an ordinary message, without interpreting claims."""
    sections, current, fence = {}, None, None
    for line in (message or "").splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        if fence is None and line.startswith("## "):
            heading = line[3:].strip()
            current = heading if heading in SECTIONS else None
            if current:
                sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def clear_conclusion(message):
    sections = closing_sections(message)
    return all(sections.get(name) for name in SECTIONS)


def json_block(value):
    content = json.dumps(value, indent=2, ensure_ascii=False)
    fence = "`" * max(3, max((len(m[0]) + 1 for m in re.finditer(r"`+", content)), default=3))
    return f"{fence}json\n{content}\n{fence}\n"


def render_attempt(attempt, events, issues, receipt):
    answer = [f"## Attempt {attempt}"]
    final_results = []
    reasoning = [f"## Attempt {attempt}", "### What the system received"]
    received = [e for e in events if e["event"] == "run.created"]
    if received:
        for event in received:
            reasoning += [
                f"Recorded input: `{event['event_id']}`",
                json_block(event["payload"])
                if "payload" in event
                else "Unknown: the recorded input payload could not be retrieved.",
            ]
    else:
        reasoning += [
            "Unknown: no run.created evidence confirms receipt by the agent.",
            "Submitted manifest input (receipt by the agent is unconfirmed):",
            json_block({k: receipt[k] for k in ("goal", "subjects", "input") if k in receipt}),
        ]

    # An attempt normally has one run. Retain each run if execution produced more.
    run_ids = list(dict.fromkeys(e["run_id"] for e in events if e.get("run_id"))) or [None]
    for index, run_id in enumerate(run_ids):
        run_events = [
            e for e in events if e.get("run_id") == run_id or (index == 0 and not e.get("run_id"))
        ]
        terminal = [e for e in run_events if e["event"] == "run.finished"]
        snapshots = [e for e in run_events if e["event"] in {"run.finished", "run.snapshot"}]
        snapshot = snapshots[-1] if snapshots else {}
        state = snapshot.get("payload", {})
        message = state.get("final_message", "")
        sections = closing_sections(message)
        if run_id:
            answer += [f"Run: `{run_id}`; state evidence: `{snapshot.get('event_id', 'missing')}`"]
            reasoning += [
                f"Run: `{run_id}`; state evidence: `{snapshot.get('event_id', 'missing')}`"
            ]
        if terminal and clear_conclusion(message):
            final_results += [sections["Final result"]]
        else:
            final_results += [
                "No clear final conclusion was recorded for a finished run. "
                "A run status alone does not establish that the case was resolved."
            ]
            if message:
                reasoning += ["### Last recorded message (conclusion unconfirmed)", message]
        final_results += [
            f"Attempt: `{attempt}`; run: `{run_id or 'not recorded'}`. "
            "Outcome is agent-stated; supporting evidence follows below."
        ]
        if terminal:
            for event in terminal:
                final_results += [
                    f"Execution status: **{event.get('payload', {}).get('status', 'unknown')}** "
                    f"(trace `{event['event_id']}`)."
                ]
        else:
            final_results += [
                "Execution result: unknown / incomplete; no terminal record retrieved."
            ]
        if issues:
            final_results += ["Evidence is incomplete; see the evidence gaps below."]
        for heading in ("Outputs and decisions", "Actions taken", "Escalations"):
            answer += [
                f"### {heading}",
                "Agent-stated:",
                sections.get(heading) or "Not recorded; unknown. No claim of 'none' can be made.",
            ]
            if heading == "Actions taken":
                actions = state.get("actions", [])
                answer += ["Recorded action audit (results/errors determine what happened):"]
                answer += [
                    json_block(actions)
                    if actions
                    else "No audited actions appear in the retrieved state; see tool trace below."
                ]
            if heading == "Escalations":
                answer += [
                    "Delivery is established only by the corresponding action/tool result; "
                    "an agent statement or proposed escalation alone does not establish delivery."
                ]

        reasoning += [
            "### What it checked",
            "Agent-stated checks and rationale:",
            sections.get("Checks and rationale") or "Not recorded; unknown.",
            "Recorded plan, including step notes, evidence and retained revisions:",
            json_block(state["plan"]) if state.get("plan") else "No plan recorded.",
            "### Conflicts and uncertainty",
            sections.get("Conflicts and uncertainty") or "Not recorded; unknown.",
        ]
        plan = state.get("plan") or {}
        unresolved = [s for s in plan.get("steps", []) if s.get("status") != "done"]
        if unresolved:
            reasoning += ["Unfinished or skipped plan steps:", json_block(unresolved)]
        reasoning += [
            "### Failures",
            "Agent-stated:",
            sections.get("Failures") or "Not recorded; unknown.",
        ]
        failures = []
        for event in run_events:
            payload = event.get("payload", {})
            if payload.get("error"):
                failures.append({"event_id": event["event_id"], "error": payload["error"]})
        failures += [
            {"action_id": a.get("id"), "error": a["error"]}
            for a in state.get("actions", [])
            if a.get("error")
        ]
        reasoning += [
            "Observed execution failures (retained even if the agent states 'none'):",
            json_block(failures)
            if failures
            else "None recorded in the retrieved execution evidence. "
            "This does not rule out failures in missing evidence.",
        ]

    answer += ["### Tool execution record", "Every recorded call, including checks and retries:"]
    reasoning += [
        "### Tool checks and supporting evidence",
        "Full timestamped inputs/outputs are in trace.jsonl; IDs below reference it.",
    ]
    starts = {
        e["operation_id"]: e
        for e in events
        if e["event"] == "operation.started"
        and e.get("payload", {}).get("name", "").startswith("execute_tool ")
    }
    ends = {e["operation_id"]: e for e in events if e["event"] == "operation.finished"}
    for operation, start in starts.items():
        end = ends.get(operation)
        payload = end.get("payload", {}) if end else {}
        result = "failed" if payload.get("error") else ("returned" if end else "result missing")
        if end and ("payload" not in end or end.get("evidence_error")):
            result = "result unavailable"
        line = (
            f"- {start['timestamp']} — {start['payload']['name']}: {result}; "
            f"input `{start['event_id']}`, output `{end['event_id'] if end else 'missing'}`."
        )
        answer.append(line)
        reasoning.append(line)
        args = start["payload"].get("input", {}).get("arguments", {})
        if isinstance(args, dict):
            rationale = {k: args[k] for k in ("reason", "note", "evidence") if args.get(k)}
            if rationale:
                reasoning.append(json_block(rationale))
    if not starts:
        answer += ["No tool-call start records were retrieved."]
        reasoning += ["No tool-call start records were retrieved."]
    if receipt.get("runner_status"):
        answer += [f"Batch runner status: **{receipt['runner_status']}**"]
    reasoning += [
        "### Batch runner failures",
        json_block(receipt.get("runner_errors", []))
        if receipt.get("runner_errors")
        else "None recorded in the supplied receipt.",
    ]
    for target in (answer, reasoning):
        target += (
            ["### Evidence gaps", *[f"- {issue}" for issue in issues]]
            if issues
            else [
                "### Evidence gaps",
                "Known completeness checks passed; see ../export.json for scope.",
            ]
        )
    return "\n\n".join(answer), "\n\n".join(reasoning), "\n\n".join(final_results)
