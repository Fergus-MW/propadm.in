"""GBP ledger validation and exact arithmetic; recording never initiates a payment."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

BALANCES = ("tenant_balance_minor", "landlord_balance_minor", "deposit_held_minor")
CATEGORY_RULES = {
    "rent_due": ("charge", (1, 0, 0)),
    "rent_received": ("payment", (-1, 1, 0)),
    "tenant_recharge": ("charge", (1, 0, 0)),
    "deposit_received": ("payment", (0, 0, 1)),
    "deposit_deduction": ("transfer", (0, 1, -1)),
    "deposit_returned": ("payment", (0, 0, -1)),
    "management_fee": ("charge", (0, -1, 0)),
    "expense": (("charge", "payment"), (0, -1, 0)),
    "service_charge": ("payment", (0, -1, 0)),
    "ground_rent": ("payment", (0, -1, 0)),
    "utility": ("payment", (0, -1, 0)),
    "council_tax": ("payment", (0, -1, 0)),
    "insurance": ("payment", (0, -1, 0)),
    "compliance": ("payment", (0, -1, 0)),
    "landlord_contribution": ("payment", (0, 1, 0)),
    "landlord_payout": ("payment", (0, -1, 0)),
    "refund": ("payment", (1, 0, 0)),
    "adjustment": ("adjustment", (0, 0, 0)),
}
STATUSES = {"expected": 0, "pending": 1, "cleared": 2, "reconciled": 3}


def iso_date(value, name="date"):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO date")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date") from exc


def positive(value, name="amount_minor"):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive integer GBP pence")
    return value


def rounded(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def validate_economics(fields):
    category = fields.get("category")
    if category not in CATEGORY_RULES:
        raise ValueError("Unknown transaction category")
    expected_kind = CATEGORY_RULES[category][0]
    if fields.get("kind") not in (
        expected_kind if isinstance(expected_kind, tuple) else (expected_kind,)
    ):
        raise ValueError(f"Invalid kind for {category}")
    positive(fields.get("amount_minor"))
    if fields.get("currency", "GBP") != "GBP":
        raise ValueError("Only GBP transactions are supported")
    status = fields.get("status", "cleared")
    if status not in STATUSES:
        raise ValueError("Record corrections with reversing entries; void is not writable")
    iso_date(fields.get("effective_date"), "effective_date")
    for key in ("period_start", "period_end"):
        if fields.get(key):
            iso_date(fields[key], key)
    if fields.get("period_start") and fields.get("period_end"):
        if fields["period_end"] < fields["period_start"]:
            raise ValueError("Rent period end precedes its start")
    confidence = fields.get("confidence", 1.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be numeric")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between zero and one")
    if category == "adjustment":
        deltas = fields.get("adjustment_deltas", {})
        if not isinstance(deltas, dict) or set(deltas) - set(BALANCES):
            raise ValueError("Adjustments require declared balance deltas")
        if not deltas or not any(deltas.values()) or not fields.get("notes"):
            raise ValueError("Adjustments require nonzero deltas and a reason in notes")
        if any(type(v) is not int or abs(v) > fields["amount_minor"] for v in deltas.values()):
            raise ValueError("Adjustment deltas must be signed pence within amount_minor")
    elif fields.get("adjustment_deltas"):
        raise ValueError("Only adjustments may declare balance deltas")


def economic_effect(fields):
    if fields.get("status") == "void":
        return dict.fromkeys(BALANCES, 0)
    if fields["kind"] == "payment" and fields["status"] in ("expected", "pending"):
        return dict.fromkeys(BALANCES, 0)
    if fields["category"] == "expense" and fields["kind"] == "charge":
        return dict.fromkeys(BALANCES, 0)
    if fields["category"] == "adjustment":
        return {key: fields.get("adjustment_deltas", {}).get(key, 0) for key in BALANCES}
    return {
        key: sign * fields["amount_minor"]
        for key, sign in zip(BALANCES, CATEGORY_RULES[fields["category"]][1])
    }
