"""Typed Addendum A relationships and their small, validated metadata schemas."""

import math
from datetime import date, datetime

from .store import ConflictError

ENDPOINTS = {
    "owns": ({"person", "company"}, {"property"}),
    "tenant_of": ({"person"}, {"property"}),
    "manages": ({"company"}, {"property"}),
    "at": ({"ticket"}, {"property"}),
    "same_building": ({"property"}, {"property"}),
    "offers": ({"service_provider"}, {"service_offering"}),
    "contact": ({"service_provider"}, {"person"}),
    "registered_as": ({"service_provider"}, {"company"}),
    "covers": ({"service_provider"}, {"property"}),
    "preferred_for": ({"service_provider"}, {"property"}),
    "assigned_to": ({"ticket"}, {"service_provider"}),
}
ATTRIBUTES = {
    "owns": {"share_pct"},
    "tenant_of": {"from", "to", "is_lead_tenant"},
    "contact": {"role"},
}


def _day(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date or datetime")
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date or datetime") from exc


def validate_relationship(state, source, target, relation, attributes=None):
    source_type = state["entities"][source]["type"]
    target_type = state["entities"][target]["type"]
    expected = ENDPOINTS.get(relation)
    if expected and (source_type not in expected[0] or target_type not in expected[1]):
        raise ValueError(f"Invalid endpoint types for {relation}")
    if attributes is None:
        attributes = {}
    if not isinstance(attributes, dict) or set(attributes) - ATTRIBUTES.get(relation, set()):
        raise ValueError(f"Unknown relationship attributes for {relation}")
    result = dict(attributes)
    current = next(
        (
            edge
            for edge in state["edges"].values()
            if edge["source"] == source
            and edge["target"] == target
            and edge["relation"] == relation
            and not edge.get("rule")
        ),
        None,
    )
    if current:
        result = {
            **{key: current[key] for key in ATTRIBUTES.get(relation, set()) if key in current},
            **result,
        }
    if relation == "owns":
        share = result.setdefault("share_pct", 100)
        if (
            isinstance(share, bool)
            or not isinstance(share, (int, float))
            or not math.isfinite(share)
            or not 0 < share <= 100
        ):
            raise ValueError(
                "Ownership share_pct must be finite and greater than zero, at most 100"
            )
        other_shares = sum(
            edge.get("share_pct", 100)
            for edge in state["edges"].values()
            if edge["relation"] == "owns" and edge["target"] == target and edge is not current
        )
        if other_shares + share > 100 + 1e-9:
            raise ValueError("Ownership shares for one property cannot total more than 100")
    if relation == "tenant_of":
        start, end = _day(result.get("from"), "from"), _day(result.get("to"), "to")
        if start and end and start > end:
            raise ValueError("Tenancy end must not precede start")
        result.setdefault("is_lead_tenant", False)
        if type(result["is_lead_tenant"]) is not bool:
            raise ValueError("is_lead_tenant must be boolean")
    if relation == "contact":
        role = result.get("role")
        if role is not None and (not isinstance(role, str) or not role.strip() or len(role) > 200):
            raise ValueError("Contact role must be a non-empty string up to 200 characters")
        if role:
            result["role"] = role.strip()
    if relation == "at" and any(
        edge["source"] == source and edge["relation"] == "at" and edge["target"] != target
        for edge in state["edges"].values()
    ):
        raise ConflictError("A ticket can refer to exactly one property")
    if relation == "offers" and any(
        edge["target"] == target and edge["relation"] == "offers" and edge["source"] != source
        for edge in state["edges"].values()
    ):
        raise ConflictError("A service offering belongs to one provider")
    return result
