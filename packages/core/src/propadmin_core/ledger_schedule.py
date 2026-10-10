"""Calendar rent accrual with deterministic references and bounded tenancy dates."""

import calendar
from datetime import date, timedelta

from .ledger_rules import iso_date


def month_day(year, month, day):
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def next_month(day, count=1, due_day=None):
    index = day.year * 12 + day.month - 1 + count
    return month_day(index // 12, index % 12 + 1, due_day or day.day)


def statement_period(period):
    if not isinstance(period, str):
        raise ValueError("Statement period must be YYYY-MM or YYYY-MM-DD/YYYY-MM-DD")
    if "/" in period:
        start, end = period.split("/", 1)
        if iso_date(start) > iso_date(end):
            raise ValueError("Statement period end precedes start")
        return start, end
    try:
        start = date.fromisoformat(period + "-01")
    except ValueError as exc:
        raise ValueError("Statement period must be YYYY-MM or YYYY-MM-DD/YYYY-MM-DD") from exc
    return start.isoformat(), (next_month(start) - timedelta(days=1)).isoformat()


def due_dates(fields, as_of):
    if fields.get("status") != "let" or not fields.get("rent_amount_minor"):
        return
    frequency = fields.get("rent_frequency")
    if frequency not in ("weekly", "monthly", "quarterly"):
        raise ValueError("Rent frequency must be weekly, monthly or quarterly")
    due = fields.get("rent_due_day", 1)
    if type(due) is not int or not 1 <= due <= (7 if frequency == "weekly" else 31):
        raise ValueError("Rent due day is 1–7 for weekly or 1–31 for monthly/quarterly rent")
    start = iso_date(fields["tenancy_start"]) if fields.get("tenancy_start") else as_of
    end = min(as_of, iso_date(fields["tenancy_end"])) if fields.get("tenancy_end") else as_of
    if start > end:
        return
    if frequency == "weekly":
        current = start + timedelta(days=(due - 1 - start.weekday()) % 7)
    else:
        current = month_day(start.year, start.month, due)
        if current < start:
            current = next_month(current, due_day=due)
    while current <= end:
        following = (current + timedelta(days=7) if frequency == "weekly" else
                     next_month(current, 3 if frequency == "quarterly" else 1, due))
        yield current, following - timedelta(days=1)
        current = following


def generate_rent(state, ledger, as_of=None):
    today = iso_date(as_of) if as_of else date.today()
    created, touched = [], set()
    for prop in list(state["entities"].values()):
        if prop["type"] != "property" or prop.get("merged_into"):
            continue
        fields = prop["fields"]
        for due, period_end in due_dates(fields, today) or []:
            ref = f"RENT-{fields['ref']}-{due.isoformat()}"
            if any(e["type"] == "transaction" and e["fields"].get("ref") == ref
                   for e in state["entities"].values()):
                continue
            tx = ledger._record(state, {"property_id": prop["id"], "fields": {
                "ref": ref, "kind": "charge", "category": "rent_due",
                "amount_minor": fields["rent_amount_minor"], "effective_date": due.isoformat(),
                "period_start": due.isoformat(), "period_end": period_end.isoformat(),
                "status": "expected", "counterparty_name": "Tenant",
                "description": f"Scheduled {fields['rent_frequency']} rent for {fields['ref']}",
            }, "evidence": prop.get("evidence", [])}, "ledger", defer=True)
            created.append(tx)
            touched.add(prop["id"])
    from .ledger import reconcile, refresh
    for prop in touched:
        reconcile(state, prop)
        refresh(state, prop)
    return {"as_of": today.isoformat(), "created": created, "count": len(created)}
