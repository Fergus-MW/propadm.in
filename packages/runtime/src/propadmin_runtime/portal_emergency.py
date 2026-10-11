"""Human-controlled make-safe exceptions, scoped to the current source evidence."""

import hashlib
import json
import re

DANGER = (
    r"gas smell|smell of gas|eggy smell|burning|smoke|fire|sparks|flooding|"
    r"ceiling (?:is )?(?:sagging|falling|coming down)|can[’']?t lock|cannot lock|"
    r"carbon monoxide alarm|change the locks|water (?:near|in) (?:electrics|lights|sockets)"
)


def has_danger(evidence):
    # Remove explicit denials, retaining any later positive report of the same hazard.
    denial = (
        r"\b(?:no|not a|without(?: any)?)(?: signs? of| evidence of)?\s+(?:"
        + DANGER + r")(?:\s*(?:,|or|and)\s+(?:" + DANGER + r"))*\b"
    )
    evidence = re.sub(denial, "", evidence, flags=re.I)
    return bool(re.search(r"\b(?:" + DANGER + r")\b", evidence, re.I))


def evidence_key(entity, messages):
    fields = entity["fields"]
    evidence = {
        "description": entity.get("description", ""),
        "title": fields.get("title", entity.get("name", "")),
        "urgency": fields.get("urgency"),
        "tags": sorted(fields.get("tags", [])),
        "messages": sorted((m["id"], m["text"]) for m in messages if m["direction"] == "inbound"),
    }
    return hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()


def activate(item, reason):
    # This authorises a manager's make-safe workflow, never autonomous dispatch.
    item.update(
        emergency=True,
        urgency="Emergency",
        stage=1,
        autonomy=0,
        approved=False,
        tenant_fixed=False,
        emergency_reason=reason,
        emergency_reviewed_evidence=None,
        waiting_on="On-call manager · arrange make-safe and notify landlord",
    )
    item["flags"] = list(
        dict.fromkeys(
            [
                *[f for f in item["flags"] if f not in {"Needs your OK", "Waiting on landlord"}],
                "Emergency",
            ]
        )
    )


def end_emergency(item):
    # A safety resolution is scoped to these facts. New inbound evidence reopens review.
    item.update(
        emergency=False,
        urgency="Urgent",
        stage=2,
        autonomy=0,
        approved=False,
        tenant_fixed=False,
        emergency_reviewed_evidence=item.get("emergency_evidence"),
        waiting_on="Property manager · assess follow-up repair and spend authority",
    )
    item["flags"] = [f for f in item["flags"] if f != "Emergency"]
