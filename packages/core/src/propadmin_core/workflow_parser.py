"""Lossless case parsing; summaries and final outcomes never enter replay context."""

import hashlib
import re
from datetime import datetime, timezone

PARSER_VERSION = "property-history-v1"
EVENT = re.compile(r"^## (.+?) UTC — event (\d+)\s*$", re.M)
ATTACHMENT = re.compile(r"\[[^\]]+\]\((attachments/[^)]+)\)")


def section(text, name):
    match = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match[1].strip() if match else ""


def metadata(text, name):
    match = re.search(rf"^- \*\*{re.escape(name)}:\*\* (.+)$", text, re.M)
    return match[1].strip() if match else ""


def parse_case(dataset, case_ref, sources):
    """Validate the complete source manifest before the server persists anything."""
    by_path = {item["path"]: item for item in sources}
    if len(by_path) != len(sources):
        raise ValueError("Duplicate source paths")
    for path in by_path:
        if path.startswith("/") or ".." in path.split("/") or "\\" in path:
            raise ValueError("Source paths must stay inside the case folder")
    if not {"index.md", "history.md"} <= by_path.keys():
        raise ValueError("Each case needs index.md and history.md")
    index, history = by_path["index.md"]["text"], by_path["history.md"]["text"]
    title = re.search(r"^# Case (\d+): (.+)$", index, re.M)
    if not title or title[1] != case_ref:
        raise ValueError("Case reference does not match index.md")
    matches = list(EVENT.finditer(history))
    total = re.search(r"^Total events: (\d+)\s*$", history, re.M)
    if not matches or not total or int(total[1]) != len(matches):
        raise ValueError("History event count does not match its declaration")
    events, previous = [], None
    for ordinal, match in enumerate(matches, 1):
        if int(match[2]) != ordinal:
            raise ValueError("History ordinals must be consecutive, starting at one")
        timestamp = datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if previous and timestamp < previous:
            raise ValueError("History must be chronological; equal timestamps retain file order")
        previous = timestamp
        end = matches[ordinal].start() if ordinal < len(matches) else len(history)
        raw = history[match.start():end]
        anchor = re.search(r'\n<a id="event-\d+"></a>\s*$', raw)
        if anchor:
            end = match.start() + anchor.start()
            raw = history[match.start():end]
        channel, sender, recipient = (metadata(raw, name) for name in ("Channel", "From", "To"))
        if not all((channel, sender, recipient)):
            raise ValueError(f"Event {ordinal} is missing channel/from/to metadata")
        body = re.split(r"^- \*\*To:\*\* .+\n", raw, maxsplit=1, flags=re.M)[-1].strip()
        # Notes, holds and system updates are controllable actions. Incoming messages/calls
        # are observations; the model cannot recreate a tenant/contractor's future reply.
        external = channel in {"Email", "SMS", "Call"} and sender.casefold() not in {
            "northbridge lettings", "northbridge lettings system", "agency / system",
        }
        events.append({
            "ordinal": ordinal, "occurred_at": timestamp.isoformat(), "channel": channel,
            "sender": sender, "recipient": recipient, "body": body, "raw_text": raw,
            "kind": "external_observation" if external else "agent_action",
            "char_start": match.start(), "char_end": end,
            "attachments": list(dict.fromkeys(ATTACHMENT.findall(body))),
        })
    referenced = set(ATTACHMENT.findall(index + "\n" + history))
    if referenced - by_path.keys():
        raise ValueError(f"Missing attachments: {sorted(referenced - by_path.keys())}")
    request, address = section(index, "Initial request"), metadata(index, "Property")
    if not request or not address:
        raise ValueError("Initial request and property are required")
    initial = (
        f"Case {case_ref}: {title[2]}\nProperty: {address}\n"
        f"Source role: {metadata(index, 'Source role')}\nCreated: {metadata(index, 'Created')}\n\n"
        f"Initial request:\n{request}"
    )
    revision = hashlib.sha256(
        (dataset + "\0" + case_ref + "\0" + "\n".join(
            f"{path}:{by_path[path]['sha256']}" for path in sorted(by_path)
        )).encode()
    ).hexdigest()
    split = "holdout" if int(hashlib.sha256(case_ref.encode()).hexdigest()[:8], 16) % 5 == 0 else "training"
    skills = ["property-case-resolution", "resolve-maintenance-email", "contractor-invoice"]
    if any(term in title[2].casefold() for term in ("check-out", "checkout", "check out")):
        skills.append("checkout-works")
    return {
        "dataset": dataset, "case_ref": case_ref, "name": title[2], "revision": revision,
        "split": split, "initial_context": initial, "initial_request": request,
        "property_address": address, "source_role": metadata(index, "Source role"),
        "overview": section(index, "Overview"), "outcome": section(index, "Outcome"),
        "skills": skills, "events": events, "sources": sources,
    }
