"""Portal tests cover durable controls, isolation, safety boundaries and scheduling races."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app
from propadmin_runtime.portal_policy import check_agent_control


@pytest.fixture
def client():
    with TestClient(create_app(store=Store())) as client:
        token = client.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


def demo(client):
    response = client.post("/v1/portal/demo")
    assert response.status_code == 200
    return response.json()


def command(client, item, action, text="", value="", demo=True):
    return client.post(
        f"/v1/portal/items/{item['id']}/command?demo={str(demo).lower()}",
        json={"version": item["version"], "action": action, "text": text, "value": value},
    )


def test_demo_is_opt_in_isolated_persistent_and_authenticated(client):
    assert client.get("/v1/portal?demo=true").json()["items"] == []
    before = client.get("/v1/portal").json()
    data = demo(client)
    assert len(data["items"]) == 7
    assert client.get("/v1/portal").json() == before
    item = data["items"][1]
    response = command(client, item, "takeover")
    assert response.json()["autonomy"] == 0
    assert command(client, item, "approve").status_code == 409
    assert demo(client)["items"][1]["autonomy"] == 0
    assert client.get("/v1/portal", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_spend_completion_emergency_and_always_human_guards(client):
    data = demo(client)
    boiler = data["items"][1]
    blocked = command(client, boiler, "stage", "Contractor available", "Scheduled")
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["rule"] == "spend_limit"
    assert command(client, boiler, "stage", "", "Scheduled").status_code == 422
    approved = command(client, boiler, "approve", "Landlord approval recorded by phone").json()
    assert approved["approved"] and approved["stage"] == 4
    scheduled = command(
        client, approved, "stage", "Booking confirmed by both parties", "Scheduled"
    ).json()
    assert scheduled["stage"] == 5
    assert command(client, scheduled, "stage", "Close early", "Closed").status_code == 403
    fixed = command(client, scheduled, "stage", "Contractor report received", "Fixed?").json()
    confirmed = command(client, fixed, "confirm_fix", "Tenant confirmed by phone").json()
    assert command(client, confirmed, "stage", "Reports delivered", "Closed").status_code == 200
    for item in data["items"][2:4]:
        taken = command(client, item, "takeover").json()
        assert command(client, taken, "handback").status_code == 403
        assert command(client, taken, "approve").status_code == 403
    gas = data["items"][0]
    assert (
        command(client, gas, "stage", "Engineer confirmed make safe", "Made safe").status_code
        == 200
    )


def test_live_takeover_blocks_agent_mutations_but_not_reads(client):
    item = client.get("/v1/portal").json()["items"][0]
    taken = command(client, item, "takeover", demo=False)
    assert taken.status_code == 200
    state = client.app.state.store.snapshot()
    with pytest.raises(HTTPException) as error:
        check_agent_control(state, "test", "update_entity", {"id": item["id"]})
    assert error.value.status_code == 403
    check_agent_control(state, "test", "get_entity", {"id": item["id"]})
    client.patch("/v1/portal/settings", json={"paused": True})
    with pytest.raises(HTTPException):
        check_agent_control(client.app.state.store.snapshot(), "test", "send_email", {})
    client.patch("/v1/portal/settings", json={"paused": False})
    check_agent_control(client.app.state.store.snapshot(), "test", "send_email", {})


def test_demo_reply_privacy_version_and_idempotency(client):
    item = demo(client)["items"][1]
    path = f"/v1/portal/items/{item['id']}/send?demo=true"
    payload = {
        "version": item["version"],
        "text": "The repair costs £900",
        "request_id": str(uuid4()),
    }
    assert client.post(path, json=payload).status_code == 403
    payload["text"] = "Thanks. We will confirm the visit with you."
    assert client.post(path, json=payload).json()["status"] == "simulated"
    assert client.post(path, json=payload).status_code == 409
    record = client.get("/v1/portal?demo=true").json()["items"][1]
    assert record["messages"][-1]["text"] == payload["text"]
    assert not client.app.state.store.snapshot().get("portal", {}).get("records")


def test_trip_checks_consent_fit_duplicate_and_confirmation_race(client):
    data = demo(client)
    payload = {
        "property_ids": ["demo-home-0"],
        "start": data["prospect"]["start"],
        "end": data["prospect"]["end"],
        "travel_minutes": 15,
    }
    path = "/v1/portal/trips/propose?demo=true"
    assert client.post(path, json=payload).status_code == 403
    payload["property_ids"] = ["demo-home-1", "demo-home-1"]
    assert client.post(path, json=payload).status_code == 422
    payload["property_ids"] = ["demo-home-1", "demo-home-2"]
    first = client.post(path, json=payload).json()
    second = client.post(path, json=payload).json()
    assert len(first["visits"]) == 2
    assert client.post(f"/v1/portal/trips/{first['id']}/confirm?demo=true").status_code == 200
    assert client.post(f"/v1/portal/trips/{first['id']}/confirm?demo=true").status_code == 200
    assert client.post(f"/v1/portal/trips/{second['id']}/confirm?demo=true").status_code == 409
    assert client.post(path, json=payload).status_code == 409
    assert client.post("/v1/portal/trips/propose", json=payload).status_code == 409


def test_live_viewings_require_evidence_and_revalidate_on_confirm(client):
    from datetime import datetime, timedelta, timezone

    data = client.get("/v1/portal").json()
    person, prop = data["people"][0], data["properties"][0]
    start = datetime.now(timezone.utc) + timedelta(days=3)
    window = {
        "start": start.isoformat(),
        "end": (start + timedelta(hours=3)).isoformat(),
        "evidence": "Email confirmation and certificate review",
    }
    assert (
        client.put(
            "/v1/portal/prospects/availability",
            json={"person_id": person["id"], "budget": 2000, **window},
        ).status_code
        == 200
    )
    path = f"/v1/portal/properties/{prop['id']}/viewing-rules"
    rules = {"occupied": True, "consent": True, "compliant": True, "notice_hours": 24, **window}
    assert client.put(path, json=rules).status_code == 200
    payload = {
        "prospect_id": person["id"],
        "property_ids": [prop["id"]],
        "start": window["start"],
        "end": window["end"],
        "travel_minutes": 15,
    }
    proposed = client.post("/v1/portal/trips/propose", json=payload)
    assert proposed.status_code == 200, proposed.text
    trip = proposed.json()
    # Withdrawing consent after proposal must prevent confirmation.
    client.put(path, json={**rules, "consent": False})
    assert client.post(f"/v1/portal/trips/{trip['id']}/confirm").status_code == 403
    client.put(path, json=rules)
    assert client.post(f"/v1/portal/trips/{trip['id']}/confirm").status_code == 200
    assert client.get("/v1/portal").json()["trips"][0]["status"] == "Confirmed"
    assert client.get("/v1/portal?demo=true").json()["trips"] == []


def test_negated_gas_smell_does_not_escalate_but_bank_change_does(client):
    items = client.get("/v1/portal").json()["items"]
    item = next(i for i in items if i["id"] == "ticket:prop-1042")
    assert item["urgency"] != "Emergency"
    entity = client.get(f"/v1/entities/{item['id']}").json()
    client.patch(
        f"/v1/entities/{item['id']}",
        json={
            "version": entity["version"],
            "description": "Please change the bank details for our next payment.",
        },
    )
    item = next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item["id"])
    assert "Fraud check" in item["flags"] and item["autonomy"] == 1
    taken = command(client, item, "takeover", demo=False).json()
    assert taken["autonomy"] == 0
    assert command(client, taken, "handback", demo=False).status_code == 403


def test_shared_progress_is_scoped_redacted_revocable_and_expires(client):
    from propadmin_runtime.auth import issue_token

    item = demo(client)["items"][1]
    shares = {}
    for audience in ("tenant", "landlord"):
        response = client.post(
            f"/v1/portal/items/{item['id']}/share?demo=true", json={"audience": audience}
        )
        assert response.status_code == 200
        shares[audience] = response.json()
    tenant = client.get(
        "/v1/portal/shared", headers={"Authorization": f"Bearer {shares['tenant']['token']}"}
    )
    assert tenant.status_code == 200
    assert tenant.headers["cache-control"] == "no-store"
    assert not {
        "estimate",
        "spend_limit",
        "messages",
        "timeline",
        "handover",
        "person",
        "draft",
    }.intersection(tenant.json())
    landlord = client.get(
        "/v1/portal/shared", headers={"Authorization": f"Bearer {shares['landlord']['token']}"}
    ).json()
    assert landlord["estimate"] == 900
    assert (
        client.get(
            "/v1/portal", headers={"Authorization": f"Bearer {shares['tenant']['token']}"}
        ).status_code
        == 403
    )
    assert (
        client.get("/v1/portal/shared").status_code == 403
    )  # admin token cannot substitute a share token
    expired = issue_token(
        client.app.state.settings, actor=f"repair:{shares['tenant']['id']}", lifetime=-1
    )
    assert (
        client.get("/v1/portal/shared", headers={"Authorization": f"Bearer {expired}"}).status_code
        == 401
    )
    client.delete(f"/v1/portal/shares/{shares['tenant']['id']}")
    assert (
        client.get(
            "/v1/portal/shared", headers={"Authorization": f"Bearer {shares['tenant']['token']}"}
        ).status_code
        == 404
    )


def test_live_email_reply_uses_existing_adapter_and_does_not_retry(client, monkeypatch):
    from propadmin_runtime import portal_messages

    item = next(
        i
        for i in client.get("/v1/portal").json()["items"]
        if any(m["channel"] == "Email" for m in i["messages"])
    )
    calls = []

    def delivery(settings, service, path, payload):
        calls.append((service, path, payload))
        return {"status": "sent", "email_id": "email:sent"}

    monkeypatch.setattr(portal_messages, "call_service", delivery)
    payload = {
        "version": item["version"],
        "text": "We will confirm the repair appointment shortly.",
        "request_id": str(uuid4()),
    }
    path = f"/v1/portal/items/{item['id']}/send"
    assert client.post(path, json=payload).status_code == 200
    assert len(calls) == 1 and calls[0][:2] == ("email", "/internal/reply")
    assert calls[0][2]["reply_all"] is False
    assert client.post(path, json=payload).status_code == 409
    assert len(calls) == 1


def test_agent_drafts_have_sources_require_review_and_preserve_human_control(client):
    from propadmin_runtime.tools_portal import draft_reply, get_item

    item = client.get("/v1/portal").json()["items"][0]
    args = {
        "item_id": item["id"],
        "version": item["version"],
        "text": "We are reviewing your repair.",
        "confidence": "Low",
        "reasons": ["Access time needs confirmation"],
        "source_ids": [item["id"]],
    }
    drafted = draft_reply(client.app, "test-run", args)
    assert drafted["autonomy"] == 2
    assert "Low confidence" in drafted["flags"]
    assert drafted["facts"][0]["id"] == item["id"]
    with pytest.raises(Exception, match="changed"):
        draft_reply(client.app, "test-run", args)
    taken = command(client, drafted, "takeover", demo=False).json()
    with pytest.raises(Exception, match="human has a saved draft"):
        draft_reply(client.app, "test-run", {**args, "version": taken["version"]})
    assert get_item(client.app, "test-run", {"item_id": item["id"]})["draft"] == args["text"]


def test_uncertain_email_delivery_needs_evidence_before_retry(client, monkeypatch):
    from propadmin_core import ProviderNotConfigured
    from propadmin_runtime import portal_messages

    item = next(
        i
        for i in client.get("/v1/portal").json()["items"]
        if any(m["channel"] == "Email" for m in i["messages"])
    )

    def fail(*args):
        raise ProviderNotConfigured("Email provider unavailable")

    monkeypatch.setattr(portal_messages, "call_service", fail)
    path = f"/v1/portal/items/{item['id']}"
    reply = {
        "version": item["version"],
        "text": "Please confirm a visit time.",
        "request_id": str(uuid4()),
    }
    assert client.post(path + "/send", json=reply).status_code == 503
    latest = next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item["id"])
    assert latest["delivery_status"] == "unconfirmed"
    assert (
        client.post(
            path + "/send", json={**reply, "version": latest["version"], "request_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/delivery-review",
            json={"sent": False, "evidence": "Provider log confirms no delivery"},
        ).status_code
        == 200
    )
    latest = next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item["id"])
    assert latest["delivery_status"] is None


def test_travel_buffer_between_separate_trips():
    from datetime import datetime, timezone

    from propadmin_runtime.routes_portal import conflicts

    other = {
        "prospect_id": "person:1",
        "travel_minutes": 15,
        "visits": [
            {
                "property_id": "property:1",
                "start": "2026-10-13T17:00:00+00:00",
                "end": "2026-10-13T17:30:00+00:00",
            }
        ],
    }
    assert conflicts(
        datetime(2026, 10, 13, 17, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 13, 18, tzinfo=timezone.utc),
        "property:2",
        "person:1",
        15,
        other,
    )
    assert not conflicts(
        datetime(2026, 10, 13, 17, 45, tzinfo=timezone.utc),
        datetime(2026, 10, 13, 18, 15, tzinfo=timezone.utc),
        "property:2",
        "person:1",
        15,
        other,
    )


def test_emergency_override_bypasses_only_make_safe_and_survives_pause(client):
    item = demo(client)["items"][1]
    client.patch("/v1/portal/settings?demo=true", json={"paused": True})
    assert command(client, item, "emergency_override").status_code == 422
    active = command(client, item, "emergency_override", "Tenant confirms water in sockets").json()
    assert active["emergency"] and active["stage"] == 1 and active["autonomy"] == 0
    assert not active["approved"] and "Waiting on landlord" not in active["flags"]
    assert command(client, item, "emergency_override", "Stale evidence").status_code == 409
    assert command(client, active, "urgency", "Downgrade", "Routine").status_code == 403
    assert command(client, active, "handback").status_code == 403
    assert command(client, active, "reopen").status_code == 422
    assert command(client, active, "emergency_stand_down", "Attempt bypass").status_code == 422
    dispatched = command(
        client, active, "stage", "Qualified contractor accepted", "Make-safe dispatched"
    ).json()
    assert dispatched["stage"] == 3  # Over-limit quote did not block make-safe.
    safe = command(
        client, dispatched, "stage", "Engineer confirmed safe by phone", "Made safe"
    ).json()
    assert not safe["emergency"] and safe["urgency"] == "Urgent" and safe["stage"] == 2
    assert not safe["approved"] and not safe["tenant_fixed"]
    assert (
        command(client, safe, "stage", "Permanent repair booking", "Scheduled").status_code == 403
    )
    assert client.get("/v1/portal?demo=true").json()["settings"]["paused"]
    assert safe["timeline"][-1]["detail"] == "Made safe — Engineer confirmed safe by phone"
    assert safe["timeline"][-1]["value"] == "Made safe"


def test_live_emergency_resolution_is_scoped_to_evidence_and_reopens_on_new_danger(client):
    item_id = "ticket:prop-1042"

    def report(text):
        entity = client.get(f"/v1/entities/{item_id}").json()
        response = client.patch(
            f"/v1/entities/{item_id}",
            json={
                "version": entity["version"],
                "description": text,
            },
        )
        assert response.status_code == 200

    def current():
        return next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item_id)

    report("There is water in sockets. The tenant cannot complete a form.")
    item = current()
    assert item["urgency"] == "Emergency" and not item["emergency"]
    assert item["autonomy"] == 1
    with pytest.raises(HTTPException):
        check_agent_control(
            client.app.state.store.snapshot(), "test", "send_email", {"ticket_id": item_id}
        )
    client.patch("/v1/portal/settings", json={"paused": True})
    active = command(
        client, item, "emergency_override", "Tenant confirmed immediate danger", demo=False
    ).json()
    assert current()["emergency"] and active["autonomy"] == 0
    safe = command(
        client,
        active,
        "stage",
        "Electrician has isolated affected circuit",
        "Made safe",
        demo=False,
    ).json()
    assert current()["urgency"] == "Urgent" and "Emergency" not in current()["flags"]
    assert safe["emergency_reviewed_evidence"]

    # A prior closed state must not hide newly reported danger from the queue.
    def close_projection(state):
        state["portal"]["records"][item_id].update(stage=11, tenant_fixed=True, approved=True)

    client.app.state.store.mutate(close_projection)
    report("The ceiling is coming down now, after the electrical problem was isolated.")
    assert current()["urgency"] == "Emergency" and not current()["emergency"]
    assert current()["stage"] == 2 and not current()["tenant_fixed"]
    reviewed = command(
        client,
        current(),
        "emergency_stand_down",
        "On-call manager inspected; no immediate danger remains",
        demo=False,
    ).json()
    assert reviewed["urgency"] == "Urgent" and current()["urgency"] == "Urgent"
    assert client.get("/v1/portal").json()["settings"]["paused"]


def test_emergency_urgency_enters_workflow_without_bypassing_fraud_or_privacy(client):
    item = demo(client)["items"][3]
    active = command(
        client, item, "urgency", "Immediate danger separately confirmed", "Emergency"
    ).json()
    assert active["emergency"] and active["autonomy"] == 0
    assert "Fraud check" in active["flags"] and "Human only" in active["flags"]
    assert active["timeline"][-1]["action"] == "emergency_override"
    path = f"/v1/portal/items/{item['id']}/send?demo=true"
    assert (
        client.post(
            path,
            json={
                "version": active["version"],
                "text": "Bank details updated",
                "request_id": str(uuid4()),
            },
        ).status_code
        == 403
    )
    assert command(client, active, "handback").status_code == 403


def test_vulnerability_raises_urgency_after_an_earlier_routine_override(client):
    item_id = "ticket:prop-1042"
    item = next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item_id)
    assert (
        command(client, item, "urgency", "Initial assessment", "Routine", demo=False).status_code
        == 200
    )
    entity = client.get(f"/v1/entities/{item_id}").json()
    client.patch(
        f"/v1/entities/{item_id}",
        json={
            "version": entity["version"],
            "description": "The heating is still off. An elderly occupant uses medical equipment.",
        },
    )
    item = next(i for i in client.get("/v1/portal").json()["items"] if i["id"] == item_id)
    assert item["urgency"] == "Urgent" and "Vulnerable occupant" in item["flags"]
    assert "Human only" in item["flags"] and item["autonomy"] <= 1


def test_tanner_script_is_linked_isolated_and_loading_preserves_edits(client):
    data = demo(client)
    shower, leak = [
        next(i for i in data["items"] if i["id"] == key)
        for key in ("demo-pro-1042", "demo-pro-1043")
    ]
    assert shower["approved"] and shower["estimate"] == 64.99 and shower["spend_limit"] == 50
    assert shower["urgency"] == "Routine" and not shower["emergency"]
    assert leak["emergency"] and leak["estimate"] == 180 and leak["stage"] == 3
    assert not leak["tenant_fixed"]
    assert shower["related_items"][0]["id"] == leak["id"]
    assert leak["related_items"][0]["id"] == shower["id"]
    messages = {m["id"]: m for item in (shower, leak) for m in item["messages"]}
    assert len(messages) == 14
    assert {m["channel"] for m in messages.values()} == {"Email", "SMS", "Call transcript"}
    assert messages["tanner-email-3"]["attachments"] == ["shower_head.jpg"]
    taken = command(client, shower, "takeover").json()
    again = demo(client)
    assert len(again["items"]) == 7
    assert next(i for i in again["items"] if i["id"] == shower["id"])["version"] == taken["version"]
    assert not any(
        i["id"].startswith("demo-pro-") for i in client.get("/v1/portal").json()["items"]
    )
    assert not client.app.state.store.snapshot().get("portal_deliveries")
