"""ANSWER.md, REASONING.md and trace.json from a run record. Nothing here is hand-written per case."""

import json
from datetime import datetime, timezone

from .stack import STAFF_EMAIL

COMMS = {"send_email", "reply_email", "place_call"}
PLAN = {"create_plan", "update_step", "add_step", "revise_plan", "get_plan"}
READS = {"search", "get_entity", "traverse", "get_document", "query_graph", "get_skill", "list_workflow_issues",
         "find_providers", "get_provider", "get_property", "get_ledger", "get_balances", "get_unallocated"}


def result_of(call):
    response = call.get("response", {})
    if "error" in response:
        error = response["error"]
        return "ERROR", str(error.get("message", error) if isinstance(error, dict) else error)[:500]
    result = response.get("result", {})
    content = result.get("structuredContent") or {}
    if result.get("isError"):
        text = "".join(c.get("text", "") for c in result.get("content", []) if isinstance(c, dict))
        detail = content.get("error") if isinstance(content, dict) else None
        return "ERROR", str(detail or text or "tool error")[:500]
    if isinstance(content, dict) and content.get("mode") == "SIMULATED":
        return "SIMULATED", content.get("note", "sandboxed, not delivered")
    return "OK", ""


def args(call):
    return call["request"].get("arguments") or {}


def staff_involvement(calls):
    evidence = []
    for call in calls:
        name, a = call["request"].get("name"), args(call)
        if name in {"send_email", "reply_email"} and STAFF_EMAIL in json.dumps(a):
            evidence.append(f"Emailed agency staff: {a.get('subject', '(reply)')}")
        if name in {"update_entity", "upsert_entity"} and any(
                "staff" in str(tag) for tag in (a.get("fields") or {}).get("tags", [])):
            evidence.append(f"Tagged {a.get('id')} {', '.join(str(t) for t in a['fields']['tags'])}")
        if name == "add_note" and "STAFF DECISION" in str(a.get("note", "")).upper():
            evidence.append(f"Handover note on {a.get('id')}")
    return evidence


def action_line(call):
    name, a = call["request"].get("name"), args(call)
    if name in {"send_email"}:
        return f"Email to {', '.join(a.get('to', []))}: {a.get('subject', '')}"
    if name == "reply_email":
        return f"Reply in thread {a.get('email_id')}"
    if name == "place_call":
        return f"Call {a.get('entity_id')}: {a.get('objective', '')}"
    if name in {"update_entity", "upsert_entity"}:
        return f"Update {a.get('id') or a.get('type')}: {', '.join(sorted((a.get('fields') or {}).keys()))}"
    if name == "add_note":
        return f"Note on {a.get('id')}"
    if name == "sleep":
        return f"Wait: {a.get('reason', '')} (wake on {', '.join(a.get('wake_on', []) or ['timer'])})"
    return f"{name}: {json.dumps(a, ensure_ascii=False)[:160]}"


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def answer_md(record):
    lines = [f"# Case {record['answer_id']}: {record['title']}", "",
             f"Run: **{record['execution']}** · Path: **{record['mode']}** · "
             f"Model: {record.get('model', 'claude-sonnet-5-5')} · Generated {record['finished']}", ""]
    if record["mode"] == "fallback":
        lines += ["> The live agent run did not complete, so this answer comes from the fallback path: the "
                  "same system prompt and skills in one direct model call. Its actions are proposals and "
                  "were not executed.", ""]
    lines += ["## Decision", "", record.get("decision") or "_The agent produced no final message._", ""]
    calls = record.get("calls", [])
    staff = staff_involvement(calls) if record["mode"] == "live" else record.get("staff", [])
    lines += ["## Escalation to staff", ""]
    lines += [f"- {item}" for item in staff] if staff else ["None. The agent handled the case without staff."]
    lines += ["", "## Actions taken", ""]
    acted = [c for c in calls if c["request"].get("name") not in READS | PLAN]
    if record["mode"] == "fallback":
        acted = []
        lines += [f"- Proposed: {a}" for a in record.get("proposed", [])] or ["None proposed."]
    elif acted:
        lines += ["| # | Action | Result |", "| --- | --- | --- |"]
        for i, call in enumerate(acted, 1):
            status, note = result_of(call)
            lines.append(f"| {i} | {cell(action_line(call))} | {status}{' - ' + cell(note) if note else ''} |")
        lines += ["", "SIMULATED means the sandboxed provider recorded the message; nothing was delivered."]
    else:
        lines.append("No actions. The agent read the case and took no external or record-changing step.")
    messages = [c for c in acted if c["request"].get("name") in COMMS]
    if messages:
        lines += ["", "## Messages", ""]
        for call in messages:
            a = args(call)
            head = f"**{call['request']['name']}** to {', '.join(a.get('to', [])) or a.get('entity_id') or a.get('email_id')}"
            body = a.get("body") or f"Objective: {a.get('objective', '')}\n\nBrief: {a.get('brief', '')}"
            lines += [head + (f": {a['subject']}" if a.get("subject") else ""), "", "```text", body.strip(), "```", ""]
    failures = [(c["request"].get("name"), result_of(c)[1]) for c in calls if result_of(c)[0] == "ERROR"]
    lines += ["", "## What failed", ""]
    lines += [f"- {name}: {cell(note)}" for name, note in failures] or ["Nothing failed."]
    if record.get("error"):
        lines.append(f"- Run error: {record['error']}")
    ticket = record.get("ticket") or {}
    lines += ["", "## Final state", "",
              f"- Ticket status: {ticket.get('status', 'unknown')}, urgency: {ticket.get('urgency', 'unset')}, "
              f"tags: {', '.join(ticket.get('tags', []) or ['none'])}"]
    for step in (record.get("plan") or {}).get("steps", []):
        lines.append(f"- Plan step [{step['status']}]: {step['title']}" + (f" ({step['note']})" if step.get("note") else ""))
    return "\n".join(lines).rstrip() + "\n"


def reasoning_md(record):
    lines = [f"# Reasoning for case {record['answer_id']}", "", "## What the system received", ""]
    lines += [f"- `{f['file']}`: {f['status']}, {f['bytes']} bytes" for f in record["files"]]
    lines += [f"- {record['events']} history events; latest timestamp {record.get('case_time') or 'unknown'}", ""]
    calls = record.get("calls", [])
    skills = [args(c).get("skill") for c in calls if c["request"].get("name") == "get_skill"]
    lines += ["## Skills consulted", "", ", ".join(skills) if skills else "None", ""]
    plan = record.get("plan") or {}
    if plan:
        lines += ["## Plan", "", f"Goal: {plan.get('goal', '')}", ""]
        for step in plan.get("steps", []):
            lines.append(f"- [{step['status']}] {step['title']}")
            for key in ("note", "evidence"):
                if step.get(key):
                    lines.append(f"  - {key}: {cell(step[key])[:600]}")
        lines.append("")
    if record["mode"] == "fallback":
        lines += ["## Model reasoning (fallback)", "", record.get("reasoning", ""), ""]
    lines += ["## Agent messages", ""]
    lines += [f"{i}. {m.strip()}" for i, m in enumerate(record.get("messages", []), 1)] or ["None."]
    lines += ["", "## Tool trace", ""]
    for i, call in enumerate(calls, 1):
        status, note = result_of(call)
        lines.append(f"{i}. `{call['request'].get('name')}` {cell(json.dumps(args(call), ensure_ascii=False))[:300]} "
                     f"-> {status}{' ' + cell(note)[:200] if note else ''}")
    if not calls:
        lines.append("No tool calls.")
    return "\n".join(lines).rstrip() + "\n"


RESPONSE_LIMIT = 4000


def compact(record):
    """Full requests and messages; each tool response capped (skill texts and the case file repeat)."""
    calls = []
    for call in record.get("calls", []):
        text = json.dumps(call.get("response", {}), ensure_ascii=False, default=str)
        response = call.get("response", {}) if len(text) <= RESPONSE_LIMIT else {
            "truncated": f"{len(text)} characters; first {RESPONSE_LIMIT} kept", "head": text[:RESPONSE_LIMIT]}
        calls.append({**call, "response": response})
    return {**record, "calls": calls}


def write(record, out_dir):
    """Always leaves ANSWER.md, REASONING.md and trace.json, even if rendering fails."""
    folder = out_dir / record["answer_id"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "trace.json").write_text(json.dumps(compact(record), indent=1, ensure_ascii=False, default=str))
    for name, render in (("ANSWER.md", answer_md), ("REASONING.md", reasoning_md)):
        try:
            text = render(record)
        except Exception as error:  # the raw trace is still written; say so plainly
            text = (f"# Case {record['answer_id']}\n\nRendering this file failed ({type(error).__name__}: "
                    f"{error}). The complete run record is in trace.json.\n\nDecision recorded by the agent:\n\n"
                    f"{record.get('decision') or 'none'}\n")
        (folder / name).write_text(text)


def index_md(rows):
    lines = ["# Answers", "", f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
             "`python -m reality_claude`. Each folder holds ANSWER.md, REASONING.md and the full trace.", "",
             "| Case | Title | Run | Path | Staff | Actions | Failures | Seconds |",
             "| --- | --- | --- | --- | --- | ---: | ---: | ---: |"]
    for r in sorted(rows, key=lambda r: int(r["answer_id"]) if r["answer_id"].isdigit() else r["answer_id"]):
        lines.append(f"| [{r['answer_id']}]({r['answer_id']}/ANSWER.md) | {cell(r['title'])[:60]} | {r['execution']} | "
                     f"{r['mode']} | {'yes' if r['staff'] else 'no'} | {r['actions']} | {r['failures']} | {r['seconds']} |")
    return "\n".join(lines) + "\n"
