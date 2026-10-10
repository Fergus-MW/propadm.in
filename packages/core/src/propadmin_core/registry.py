"""Data-defined entity schemas and strict field normalisation."""

import copy
import math
import re
from datetime import date, datetime

CATEGORIES = [
    "plumbing",
    "heating",
    "electrical",
    "damp/mould",
    "structural",
    "appliances",
    "pests",
    "access/security",
    "other",
]


def field(type="string", *, enum=None, unique=False, embed=None, required=False, **metadata):
    result = {
        "type": type,
        "required": required,
        "unique_key": unique,
        "embed": ("text" in type) if embed is None else embed,
    }
    result.update(metadata)
    if type in {"int", "option<int>"}:
        result.setdefault("maximum", 2**53 - 1)
        result.setdefault("minimum", -(2**53 - 1))
    if enum:
        result["enum"] = enum
    return result


# Agent workflow records are written by agents and admins, never extracted from sources.
NOT_PRIMARY = {"skill", "skill_version", "workflow_issue", "skill_change_proposal",
               "workflow_case", "workflow_event", "workflow_transition", "workflow_evaluation",
               "workflow_triplet", "media_asset"}


def primary_types(state):
    """Types ingestion extracts from sources; admins toggle each type's `primary` flag."""
    return {
        key for key, definition in state["entity_types"].items()
        if definition.get("primary", key not in NOT_PRIMARY)
    }


def default_types():
    urgency = field(enum=["emergency", "urgent", "routine"])
    intent = field(
        enum=["report_issue", "update", "scheduling", "quote_or_invoice", "complaint", "other"]
    )
    types = {
        "person": {
            "roles": field(
                "array<string>", enum=["tenant", "landlord", "contractor", "staff", "other"]
            ),
            "emails": field("array<string>", unique=True),
            "phones": field("array<string>", unique=True),
            "address": field("text"),
            "availability": field("text"),
            "preferred_contact": field(enum=["email", "phone", "sms"]),
            "notes": field("array<text>"),
        },
        "company": {
            "type": field(enum=["contractor", "supplier", "managing agent", "landlord", "other"]),
            "domains": field("array<string>", unique=True),
            "emails": field("array<string>"),
            "phones": field("array<string>"),
            "trades": field("array<string>", enum=CATEGORIES),
            "address": field("text"),
            "coverage_area": field("text"),
            "notes": field("array<text>"),
        },
        "ticket": {
            "ref": field(unique=True),
            "title": field("text"),
            "location_detail": field("text"),
            "category": field(enum=CATEGORIES),
            "urgency": urgency,
            "status": field(
                enum=[
                    "reported",
                    "triaged",
                    "scheduled",
                    "in progress",
                    "awaiting parts",
                    "resolved",
                    "closed",
                ]
            ),
            "tags": field("array<string>"),
            "reported_at": field("datetime"),
            "resolved_at": field("option<datetime>"),
            "scheduled_visit_at": field("option<datetime>"),
            "first_visit_at": field("option<datetime>"),
            "visits_count": field("option<int>", minimum=1),
            "tenant_feedback_rating": field("option<decimal>", minimum=1, maximum=5),
            "cost_estimate": field("option<decimal>"),
            "cost_actual": field("option<decimal>"),
            "access_instructions": field("text"),
            "resolution": field("text"),
            "final_answer": field("text"),
            "reasoning": field("text"),
            "notes": field("array<text>"),
        },
        "email": {
            "message_id": field(unique=True),
            "thread_id": field(),
            "in_reply_to": field("option<string>"),
            "references": field("array<string>"),
            "channel": field(enum=["synthetic_env", "agentmail"]),
            "mailbox": field("option<string>"),
            "direction": field(enum=["inbound", "outbound"]),
            "status": field(enum=["received", "sent", "failed", "bounced"]),
            "subject": field("text"),
            "from_address": field(),
            "from_name": field(),
            "to_addresses": field("array<string>"),
            "cc_addresses": field("array<string>"),
            "bcc_addresses": field("array<string>"),
            "reply_to_address": field("option<string>"),
            "sent_at": field("datetime"),
            "received_at": field("datetime"),
            "body_text": field("text"),
            "body_full": field("text"),
            "summary": field("text"),
            "action_items": field("array<text>"),
            "intent": intent,
            "urgency": urgency,
            "sentiment": field(enum=["positive", "neutral", "negative"]),
            "language": field(),
            "attachments": field("array<object>"),
            "labels": field("array<string>"),
            "is_spam": field("bool"),
            "agent_session": field("option<string>"),
            "raw_uri": field(),
        },
        "call": {
            "call_id": field(unique=True),
            "provider": field(enum=["elevenlabs", "synthetic_env"]),
            "direction": field(enum=["inbound", "outbound"]),
            "from_number": field(),
            "to_number": field(),
            "agent_number": field("option<string>"),
            "started_at": field("datetime"),
            "answered_at": field("datetime"),
            "ended_at": field("datetime"),
            "duration_s": field("int"),
            "status": field(enum=["completed", "voicemail", "no_answer", "busy", "failed"]),
            "end_reason": field("option<string>"),
            "objective": field("text"),
            "call_brief": field("text"),
            "transcript": field("array<object>", embed=True),
            "transcript_text": field("text"),
            "summary": field("text"),
            "outcome": field("text"),
            "action_items": field("array<text>"),
            "intent": intent,
            "urgency": urgency,
            "sentiment": field(enum=["positive", "neutral", "negative"]),
            "language": field(),
            "tool_calls": field("array<object>"),
            "recording_uri": field("option<string>"),
            "agent_session": field("option<string>"),
        },
    }
    extra = {
        "skill": {
            "slug": field(unique=True),
            "source": field(enum=["custom", "anthropic"]),
            "status": field(enum=["active", "deprecated"]),
            "api_skill_id": field("option<string>"),
        },
        "skill_version": {
            "version": field("int"),
            "content": field("text"),
            "change_summary": field("text"),
            "created_by": field(),
            "api_version_id": field("option<string>"),
            "published_at": field("datetime"),
        },
        "workflow_issue": {
            "title": field("text"),
            "evidence": field("text"),
            "category": field(),
            "severity": field(enum=["low", "medium", "high", "critical"]),
            "status": field(),
            "occurrences": field("int"),
        },
        "skill_change_proposal": {
            "proposed_content": field("text"),
            "diff": field("text"),
            "reasoning": field("text"),
            "expected_effect": field("text"),
            "risks": field("text"),
            "status": field(),
            "review_notes": field("text"),
            "reviewed_by": field(),
            "reviewed_at": field("option<datetime>"),
        },
    }
    types.update(extra)
    from .registry_addendum import addendum_types

    result = {
        name: {"id": name, "name": name.replace("_", " ").title(), "fields": fields, "version": 1}
        for name, fields in types.items()
    }
    result.update(addendum_types(field))
    from .workflow_registry import workflow_types

    result.update(workflow_types(field))
    result["media_asset"] = {
        "id": "media_asset", "name": "Media asset", "version": 1, "primary": False,
        "fields": {"raw_sha256": field(unique=True), "mime": field(),
                   "source_document": field(), "gcs_uri": field(),
                   "description_model": field(), "token_usage": field("object")},
    }
    return result


def normalise(value, spec, name):
    kind = spec["type"]
    if kind.startswith("option<"):
        if value is None:
            return None
        return normalise(value, {**spec, "type": kind[7:-1]}, name)
    if kind.startswith("array<"):
        if not isinstance(value, list):
            raise ValueError(f"{name} must be an array")
        result = [normalise(item, {**spec, "type": kind[6:-1]}, name) for item in value]
        return list({repr(item): item for item in result}.values())
    if kind in ("text", "string"):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        value = value.strip()
        if name in (
            "emails",
            "domains",
            "from_address",
            "to_addresses",
            "cc_addresses",
            "bcc_addresses",
        ):
            value = value.lower()
        if name in ("phones", "from_number", "to_number", "phone_main", "phone_emergency"):
            value = re.sub(r"[\s().-]", "", value)
            if value.startswith("00"):
                value = "+" + value[2:]
            if value.startswith("0"):
                value = "+44" + value[1:]
            if value and not re.fullmatch(r"\+[1-9]\d{6,14}", value):
                raise ValueError(f"{name} must be an E.164 phone number")
        if name == "postcode":
            value = re.sub(r"\s+", "", value.upper())
            if not re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}", value):
                raise ValueError("postcode must be a UK postcode")
            value = value[:-3] + " " + value[-3:]
        if name == "postcode_districts":
            value = value.upper().strip()
            if not re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?", value):
                raise ValueError("postcode_districts must contain exact postcode districts")
        if spec.get("enum") and value not in spec["enum"]:
            raise ValueError(f"{name} must be one of {spec['enum']}")
        return value
    if kind == "bool":
        if type(value) is not bool:
            raise ValueError(f"{name} must be boolean")
    elif kind in ("int", "decimal", "float", "number"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        if kind == "int" and not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if kind == "int" and abs(value) > 2**53 - 1:
            raise ValueError(f"{name} must be a safe integer")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if "minimum" in spec and value < spec["minimum"]:
            raise ValueError(f"{name} must be at least {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            raise ValueError(f"{name} must be at most {spec['maximum']}")
    elif kind == "date":
        if not isinstance(value, str):
            raise ValueError(f"{name} must be an ISO date")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO date") from exc
    elif kind == "datetime":
        if not isinstance(value, str):
            raise ValueError(f"{name} must be an ISO datetime")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an ISO datetime") from exc
    elif kind == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be an object")
        if spec.get("properties"):
            schema = spec["properties"]
            if set(value) - set(schema):
                raise ValueError(f"Unknown structured fields in {name}")
            value = {key: normalise(item, schema[key], key) for key, item in value.items()}
            for key, child in schema.items():
                if child.get("required") and value.get(key) in (None, "", []):
                    raise ValueError(f"{name}.{key} is required")
        if name == "transcript":
            allowed = {"turn", "speaker_role", "person", "text", "start_ms", "end_ms"}
            if set(value) - allowed or not isinstance(value.get("text"), str):
                raise ValueError("Transcript turns require text and declared turn fields")
        if name == "attachments":
            allowed = {"filename", "mime", "size", "gcs_uri", "document"}
            if set(value) - allowed:
                raise ValueError("Unknown attachment field")
    else:
        raise ValueError(f"Unsupported registry type {kind}")
    return copy.deepcopy(value)


def validate_fields(state, type_name, fields, *, allow_read_only=False):
    if type_name not in state["entity_types"]:
        raise ValueError(f"Unknown entity type: {type_name}")
    schema = state["entity_types"][type_name]["fields"]
    unknown = set(fields) - set(schema)
    if unknown:
        raise ValueError(f"Unknown fields for {type_name}: {', '.join(sorted(unknown))}")
    if not allow_read_only:
        protected = [key for key in fields if schema[key].get("read_only")]
        if protected:
            raise ValueError(f"Derived fields are read-only: {', '.join(protected)}")
    result = {key: normalise(value, schema[key], key) for key, value in fields.items()}
    for key, spec in schema.items():
        if spec.get("required") and (key not in result or result[key] in ("", None, [])):
            raise ValueError(f"{key} is required")
    return result


def hard_keys(state, entity):
    schema = state["entity_types"][entity["type"]]["fields"]
    result = set()
    for name, value in entity.get("fields", {}).items():
        if schema.get(name, {}).get("unique_key"):
            for item in value if isinstance(value, list) else [value]:
                if item:
                    result.add((name, str(item).casefold()))
    fields = entity.get("fields", {})
    for names in state["entity_types"][entity["type"]].get("composite_keys", []):
        values = [fields.get(name) for name in names]
        if all(value not in (None, "", []) for value in values):
            result.add(
                (
                    "composite:" + "+".join(names),
                    "|".join(str(value).casefold() for value in values),
                )
            )
    for key, value in entity.get("external_ids", {}).items():
        if value:
            result.add((f"external:{key}", str(value).casefold()))
    return result
