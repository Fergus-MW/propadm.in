"""Portal projections. Demo scenarios are isolated from canonical graph records."""

import re
from datetime import datetime, timedelta, timezone

from .portal_emergency import evidence_key, has_danger
from .portal_tanner import tanner_items

STAGES = [
    "Reported",
    "Collecting details",
    "Triaged",
    "Landlord approval",
    "Finding a contractor",
    "Scheduled",
    "Confirmed by tenant",
    "On the way",
    "In progress",
    "Fixed?",
    "Report sent",
    "Closed",
]
EMERGENCY_STAGES = [
    "Reported",
    "Emergency confirmed",
    "Safety steps sent",
    "Make-safe dispatched",
    "On the way",
    "Made safe",
]
HUMAN_FLAGS = {"Human only", "Fraud check", "Unlawful request", "Conflict"}


def stamp(minutes=0):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def demo_data():
    records = []
    examples = [
        (
            "gas",
            "Gas smell in the kitchen",
            "12 Elm Road",
            "Priya Shah",
            "Tenant",
            "Emergency",
            4,
            ["Emergency"],
            "There has been a strange eggy smell by the boiler since this morning. It is getting stronger.",
            180,
            300,
        ),
        (
            "boiler",
            "Boiler repair needs approval",
            "8 Willow Close",
            "Sam Taylor",
            "Tenant",
            "Urgent",
            3,
            ["Needs your OK", "Waiting on landlord"],
            "The boiler has stopped producing hot water. I can be home Tuesday evening.",
            900,
            300,
        ),
        (
            "locks",
            "Landlord requests a lock change",
            "24 Brook Street",
            "Alex Morgan",
            "Landlord",
            "Emergency",
            0,
            ["Human only", "Unlawful request", "Emergency"],
            "Can I just change the locks while the tenant is out? They are behind on rent.",
            0,
            300,
        ),
        (
            "bank",
            "New contractor bank details",
            "6 Park Avenue",
            "West London Repairs",
            "Contractor",
            "Routine",
            2,
            ["Fraud check", "Human only"],
            "Please pay our next invoice to a new account. Details attached.",
            420,
            500,
        ),
        (
            "tap",
            "Kitchen tap dripping",
            "15 Ash Gardens",
            "Jamie Reed",
            "Tenant",
            "Routine",
            5,
            [],
            "The kitchen tap is dripping. Here is a close-up of the washer. Thursday morning works for me.",
            95,
            300,
        ),
    ]
    for key, title, address, person, role, urgency, stage, flags, message, cost, limit in examples:
        emergency = urgency == "Emergency" and key != "locks"
        records.append(
            dict(
                id=f"demo-{key}",
                title=title,
                property=address,
                person=person,
                role=role,
                urgency=urgency,
                stage=stage,
                emergency=emergency,
                flags=flags,
                autonomy=1
                if HUMAN_FLAGS.intersection(flags)
                else 3
                if key in {"tap", "gas"}
                else 2,
                version=1,
                demo=True,
                source_id=None,
                reported_at=stamp(-24),
                due_at=stamp(35 if urgency == "Emergency" else 120),
                estimate=cost,
                spend_limit=limit,
                approved=False,
                contractor="Dave Wilson · Heating" if key == "gas" else "Not assigned",
                eta="14 min" if key == "gas" else None,
                waiting_on="On-call manager" if urgency == "Emergency" else "Property manager",
                messages=[
                    dict(
                        id=f"message-{key}",
                        author=person,
                        text=message,
                        channel="Email",
                        at=stamp(-24),
                        direction="inbound",
                    )
                ],
                draft="Thanks for letting us know. We are reviewing the next steps and will keep you updated."
                if key == "boiler"
                else "",
                confidence="High" if key == "gas" else "Medium",
                reasons=["Review the report and verify access before the next step."],
                facts=[],
                timeline=[
                    dict(
                        at=stamp(-24),
                        actor="Workspace setup",
                        action="Record created",
                    )
                ],
                handover="Review the reported risk and contact the responsible person.",
            )
        )
    start = datetime.now(timezone.utc).replace(
        hour=17, minute=0, second=0, microsecond=0
    ) + timedelta(days=3)
    properties = [
        dict(
            id=f"demo-home-{i}",
            name=name,
            rent=rent,
            occupied=i == 0,
            consent=i != 0,
            compliant=True,
            notice_hours=24,
            start=start.isoformat(),
            end=(start + timedelta(hours=3)).isoformat(),
        )
        for i, (name, rent) in enumerate(
            [("12 Elm Road", 1800), ("8 Willow Close", 1650), ("15 Ash Gardens", 1750)]
        )
    ]
    return dict(
        items=[*records, *tanner_items()],
        properties=properties,
        trips=[],
        settings={"paused": False},
        prospect=dict(
            id="demo-prospect",
            name="Maya Patel",
            budget=1900,
            start=start.isoformat(),
            end=(start + timedelta(hours=3)).isoformat(),
        ),
    )


def graph_items(state):
    items = []
    entities = state["entities"]
    overrides = state.get("portal", {}).get("records", {})
    for entity in entities.values():
        if entity["type"] != "ticket" or entity.get("merged_into"):
            continue
        fields = entity["fields"]
        related_ids = set()
        for edge in state["edges"].values():
            if edge.get("source") == entity["id"]:
                related_ids.add(edge.get("target"))
            if edge.get("target") == entity["id"]:
                related_ids.add(edge.get("source"))
        related = [entities[i] for i in related_ids if i in entities]
        emails = [e for e in related if e["type"] == "email"]
        property_record = next((e for e in related if e["type"] == "property"), None)
        person = next((e for e in related if e["type"] == "person"), None)
        urgency = str(fields.get("urgency", "Routine")).title()
        flags = list(fields.get("tags", []))
        if urgency in {"Emergency", "Critical"}:
            urgency = "Emergency"
            flags.append("Emergency")
        if fields.get("visits_count", 0) >= 3:
            flags.extend(["Repeat fault", "Human only"])
        stage = {
            "reported": 0,
            "triaged": 2,
            "scheduled": 5,
            "in progress": 8,
            "awaiting parts": 8,
            "resolved": 9,
            "closed": 11,
        }.get(fields.get("status"), 0)
        messages = [
            dict(
                id=e["id"],
                author=e["fields"].get("from_name") or e["fields"].get("from_address", "Unknown"),
                text=e["fields"].get("body_full") or e["fields"].get("body_text", ""),
                channel="Email",
                at=e["fields"].get("sent_at") or e["fields"].get("received_at"),
                direction=e["fields"].get("direction", "inbound"),
            )
            for e in emails
        ]
        messages.sort(key=lambda m: m["at"] or "")
        incoming = next(
            (
                e
                for e in reversed(
                    sorted(emails, key=lambda e: e["fields"].get("received_at") or "")
                )
                if e["fields"].get("direction") == "inbound"
            ),
            None,
        )
        if incoming:
            sender = incoming["fields"].get("from_address", "").lower()
            person = next(
                (
                    e
                    for e in entities.values()
                    if e["type"] == "person"
                    and not e.get("merged_into")
                    and sender
                    and sender
                    in [str(address).lower() for address in e["fields"].get("emails", [])]
                ),
                None,
            )
        if not messages:
            messages = [
                dict(
                    id=entity["id"],
                    author="Ticket record",
                    text=entity.get("description", ""),
                    channel="Graph",
                    at=fields.get("reported_at"),
                    direction="inbound",
                )
            ]
        evidence = " ".join(
            [entity.get("description", ""), fields.get("title", ""), *[m["text"] for m in messages]]
        )
        if has_danger(evidence):
            urgency = "Emergency"
            flags.append("Emergency")
        if re.search(
            r"formal complaint|legal threat|council|tribunal|evict|change the locks|breathing space|domestic abuse|harassment|liability dispute",
            evidence,
            re.I,
        ):
            flags.append("Human only")
        if re.search(
            r"(?:new|change|changed|update).{0,25}bank|bank.{0,25}(?:new|change|changed|update)",
            evidence,
            re.I,
        ):
            flags.extend(["Fraud check", "Human only"])
        if re.search(r"\b(?:baby|elderly|pregnant|disabled|medical equipment)\b", evidence, re.I):
            flags.extend(["Vulnerable occupant", "Human only"])
            if urgency != "Emergency":
                urgency = "Urgent"
        item = dict(
            id=entity["id"],
            source_id=entity["id"],
            title=fields.get("title") or entity["name"],
            property=property_record["name"]
            if property_record
            else fields.get("location_detail") or "Property not linked",
            person=person["name"] if person else "Contact not linked",
            role=next(
                (
                    role.title()
                    for role in person["fields"].get("roles", [])
                    if role in {"tenant", "landlord", "contractor", "prospect"}
                ),
                "Unknown",
            )
            if person
            else "Unknown",
            urgency=urgency,
            flags=list(dict.fromkeys(flags)),
            stage=stage,
            emergency=False,
            autonomy=1 if HUMAN_FLAGS.intersection(flags) else 3,
            version=entity["version"],
            demo=False,
            reported_at=fields.get("reported_at"),
            due_at=None,
            estimate=fields.get("cost_estimate"),
            spend_limit=None,
            approved=False,
            contractor="Not linked",
            eta=None,
            waiting_on="Review record",
            messages=messages,
            draft="",
            confidence="Unknown",
            reasons=["Projected from the canonical ticket; no AI assessment inferred."],
            facts=[dict(id=entity["id"], label="Canonical ticket")],
            timeline=[],
            handover=fields.get("reasoning") or entity.get("description", ""),
        )
        overlay = overrides.get(entity["id"], {})
        item.update(overlay)
        item["emergency_evidence"] = evidence_key(entity, messages)
        if (
            not item["emergency"]
            and overlay.get("emergency_reviewed_evidence") == item["emergency_evidence"]
        ):
            flags = [f for f in flags if f != "Emergency"]
            item["flags"] = [f for f in item["flags"] if f != "Emergency"]
        # Current evidence can raise safety flags even after a manager edited portal metadata.
        item["flags"] = list(
            dict.fromkeys(
                [
                    *item["flags"],
                    *[
                        f
                        for f in flags
                        if f in HUMAN_FLAGS or f in {"Emergency", "Vulnerable occupant"}
                    ],
                ]
            )
        )
        if "Emergency" in item["flags"]:
            item["urgency"] = "Emergency"
            if not item["emergency"]:
                item["autonomy"] = min(item["autonomy"], 1)
                if item["stage"] >= 9:
                    item.update(stage=2, tenant_fixed=False, approved=False)
                item["waiting_on"] = "On-call manager · review suspected danger now"
        elif "Vulnerable occupant" in item["flags"] and item["urgency"] == "Routine":
            item["urgency"] = "Urgent"
        if HUMAN_FLAGS.intersection(item["flags"]):
            item["autonomy"] = min(item["autonomy"], 1)
        # Preserve live evidence, and combine graph revisions with portal revisions for conflict checks.
        item["version"] = entity["version"] + overlay.get("revision", 0)
        pending_delivery = next(
            (
                r
                for r in state.get("portal_deliveries", {}).values()
                if r["item_id"] == item["id"]
                and not r.get("demo")
                and r["status"] in {"sending", "unconfirmed"}
            ),
            None,
        )
        item["delivery_status"] = pending_delivery["status"] if pending_delivery else None
        if pending_delivery:
            item["flags"] = list(dict.fromkeys([*item["flags"], "Needs your OK"]))
        items.append(item)
    return items


def snapshot(state, demo=False):
    if demo:
        data = state.get("portal_demo")
        if data is None:
            return dict(
                items=[],
                properties=[],
                trips=[],
                settings={"paused": False},
                prospect=None,
                demo=True,
            )
        return {**data, "demo": True}
    portal = state.get("portal", {})
    properties = []
    people = []
    for entity in state["entities"].values():
        if entity.get("merged_into"):
            continue
        if entity["type"] == "property":
            prop = dict(
                id=entity["id"],
                name=entity["name"],
                rent=None,
                occupied=True,
                consent=False,
                compliant=False,
                notice_hours=24,
                start=None,
                end=None,
            )
            prop.update(portal.get("viewing_rules", {}).get(entity["id"], {}))
            properties.append(prop)
        if entity["type"] == "person":
            people.append(dict(id=entity["id"], name=entity["name"]))
    return dict(
        items=graph_items(state),
        properties=properties,
        people=people,
        prospects=list(portal.get("prospects", {}).values()),
        trips=portal.get("trips", []),
        settings=portal.get("settings", {"paused": False}),
        prospect=None,
        demo=False,
    )
