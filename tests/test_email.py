"""Email service: AgentMail send, signed inbound webhooks and API forwarding, all without network."""

import base64
import hashlib
import hmac
import importlib.util
import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app
from propadmin_runtime.config import Settings

SECRET = "whsec_" + base64.b64encode(b"test-webhook-key").decode()
INTERNAL = {"Authorization": f"Bearer {Settings().internal_token}"}


@pytest.fixture
def service(monkeypatch, tmp_path):
    monkeypatch.setenv("PROPADMIN_DATA_PATH", str(tmp_path / "state.json"))
    path = Path(__file__).parents[1] / "services/email/app/main.py"
    spec = importlib.util.spec_from_file_location("email_service_main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    request_headers = []

    def fake(method, url, json=None, **kwargs):
        calls.append((method, url, json))
        request_headers.append(kwargs.get("headers", {}))
        if url.endswith("/messages/send"):
            body = {"message_id": "<out-1@withproperly.com>", "thread_id": "thd_out"}
        elif url.endswith("/reply"):
            body = {"message_id": "<reply-1@withproperly.com>", "thread_id": "thd_out"}
        elif url.startswith("http://agent.test"):
            body = {"run_id": "run_1", "action": "started"}
        else:
            body = {}
        return httpx.Response(200, json=body, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", fake)
    with TestClient(module.build(create_app("email", store=Store(None), seed=True))) as client:
        client.calls = calls
        client.request_headers = request_headers
        yield client


def signed(payload, secret=SECRET):
    body = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    key = base64.b64decode(secret.removeprefix("whsec_"))
    mac = hmac.new(key, f"msg_1.{stamp}.".encode() + body, hashlib.sha256).digest()
    headers = {"svix-id": "msg_1", "svix-timestamp": stamp,
               "svix-signature": "v1," + base64.b64encode(mac).decode()}  # fmt: skip
    return body, headers


INBOUND = {
    "type": "event",
    "event_type": "message.received",
    "event_id": "evt_1",
    "message": {
        "inbox_id": "ops@withproperly.com",
        "thread_id": "thd_in",
        "message_id": "<in-1@example.net>",
        "from": "Aisha Khan <aisha.khan@example.net>",
        "to": ["ops@withproperly.com"],
        "subject": "Boiler still broken",
        "text": "Hi, the boiler is still not working.",
        "timestamp": "2026-10-10T09:00:00Z",
        "labels": ["received"],
    },
}


def test_unconfigured_providers_are_503(service, monkeypatch):
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("EMAIL_SERVICE_URL", raising=False)
    payload = {"to": ["a@example.net"], "subject": "Hi", "body": "Hello"}
    assert service.post("/internal/send", json=payload, headers=INTERNAL).status_code == 503
    with TestClient(create_app(store=Store(None), seed=False)) as api:
        token = api.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        response = api.post(
            "/v1/emails", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 503


def test_send_records_email_entity_with_thread_ids(service, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "key")
    ticket = next(
        e["id"]
        for e in service.app.state.store.snapshot()["entities"].values()
        if e["type"] == "ticket"
    )
    response = service.post(
        "/internal/send",
        json={"to": ["aisha.khan@example.net"], "subject": "Visit booked",
              "body": "Engineer visits **Tuesday**.\nThanks", "entity_ids": [ticket], "run_id": "run_9"},
        headers=INTERNAL,
    )  # fmt: skip
    assert response.status_code == 200, response.text
    method, url, body = service.calls[0]
    assert url == "https://api.agentmail.to/v0/inboxes/ops%40withproperly.com/messages/send"
    assert body == {
        "to": ["aisha.khan@example.net"],
        "subject": "Visit booked",
        "text": "Engineer visits **Tuesday**.\nThanks",  # Markdown stays the plain-text part
        "html": "<p>Engineer visits <strong>Tuesday</strong>.<br>\nThanks</p>\n",
    }
    email = service.app.state.graph.get_entity(response.json()["email_id"])
    assert email["fields"]["thread_id"] == "thd_out"
    assert email["fields"]["message_id"] == "<out-1@withproperly.com>"
    assert email["fields"]["direction"] == "outbound"
    edges = service.app.state.store.snapshot()["edges"].values()
    relations = {(e["relation"], e["target"]) for e in edges if e["source"] == email["id"]}
    assert ("about", ticket) in relations
    assert any(rel == "sent_to" for rel, _ in relations)
    # Unknown entity ids are rejected before anything is sent.
    service.calls.clear()
    bad = {"to": ["x@example.net"], "subject": "S", "body": "B", "entity_ids": ["ticket:nope"]}
    assert service.post("/internal/send", json=bad, headers=INTERNAL).status_code == 422
    assert service.calls == []


def test_delivered_email_survives_extraction_failure_and_retry(service, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "key")
    store = service.app.state.store
    store.mutate(lambda s: s["runs"].update(run_9={
        "id": "run_9", "status": "running", "subjects": [],
    }))

    def fail(*args):
        raise ValueError("Claude evidence quotes are missing or ambiguous in source text")

    monkeypatch.setattr(service.app.state.ingestion, "ingest", fail)
    body = {"to": ["a@example.test"], "subject": "Controlled send", "body": "Hello",
            "run_id": "run_9"}
    first = service.post("/internal/send", json=body, headers=INTERNAL)
    assert first.status_code == 200, first.text
    sent = first.json()
    assert sent["status"] == "sent" and "enrichment failed" in sent["warning"]
    assert service.app.state.graph.get_entity(sent["email_id"])["fields"]["status"] == "sent"
    assert "thd_out" in store.snapshot()["runs"]["run_9"]["subjects"]
    # A different reasoning string is still the same logical communication.
    retry = service.post("/internal/send", json={**body, "reason": "Retry"}, headers=INTERNAL)
    assert retry.status_code == 200 and retry.json()["deduplicated"]
    assert retry.json()["message_id"] == sent["message_id"]
    assert len(service.calls) == 1
    assert service.request_headers[0]["Idempotency-Key"] == sent["idempotency_key"]


def test_receipt_prevents_resend_when_local_recording_fails(service, monkeypatch):
    from services.email.app.delivery import finish

    monkeypatch.setenv("AGENTMAIL_API_KEY", "key")
    # Exercise a persistence outage after the durable provider receipt, then recover.
    body = {"to": ["a@example.test"], "subject": "Receipt", "body": "Hello",
            "idempotency_key": "controlled-receipt"}
    key = "controlled-receipt"
    from services.email.app import main as module
    from services.email.app.delivery import delivery_key, reserve
    _, fingerprint = delivery_key(body, "ops@withproperly.com", "send", {
        "to": body["to"], "subject": body["subject"], "text": body["body"],
        "html": module.email_html(body["body"]),
    })
    reserve(service.app, key, fingerprint)
    sent = {"message_id": "<out-1@withproperly.com>", "thread_id": "thd_out"}
    fields = module.outbound_fields(sent, "ops@withproperly.com", body["to"], "Receipt", "Hello", None)
    result = finish(service.app, key, sent, fields, [], None,
                    lambda *args: (_ for _ in ()).throw(ValueError("write failed")))
    assert result["status"] == "sent" and "Do not resend" in result["warning"]
    recovered = service.post("/internal/send", json=body, headers=INTERNAL)
    assert recovered.status_code == 200 and recovered.json()["email_id"]
    assert service.calls == []  # recording recovered without calling the provider
    changed = service.post("/internal/send", json={**body, "body": "Different"}, headers=INTERNAL)
    assert changed.status_code == 409 and service.calls == []


def test_webhook_verifies_ingests_once_and_notifies_agent(service, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent.test")
    body, headers = signed(INBOUND)
    forged = {**headers, "svix-signature": "v1,AAAA"}
    assert service.post("/webhooks/agentmail", content=body, headers=forged).status_code == 401
    _, wrong = signed(INBOUND, "whsec_" + base64.b64encode(b"other").decode())
    assert service.post("/webhooks/agentmail", content=body, headers=wrong).status_code == 401

    first = service.post("/webhooks/agentmail", content=body, headers=headers)
    assert first.status_code == 200, first.text
    email = service.app.state.graph.get_entity(first.json()["email_id"])
    assert email["fields"]["thread_id"] == "thd_in"
    assert email["fields"]["direction"] == "inbound"
    sender = [
        e for e in service.app.state.store.snapshot()["edges"].values()
        if e["source"] == email["id"] and e["relation"] == "sent_by"
    ]  # fmt: skip
    # Seeded Aisha Khan is resolved by address rather than duplicated.
    assert len(sender) == 1
    people = [
        e["id"] for e in service.app.state.store.snapshot()["entities"].values()
        if "aisha.khan@example.net" in e["fields"].get("emails", [])
    ]  # fmt: skip
    assert people == [sender[0]["target"]]

    agent_calls = [c for c in service.calls if c[1] == "http://agent.test/internal/events"]
    assert len(agent_calls) == 1
    event = agent_calls[0][2]
    assert event["kind"] == "email.received"
    # Sharing a sender or the operations mailbox must not join unrelated agent runs.
    assert event["subjects"] == ["thd_in", email["id"]]

    again = service.post("/webhooks/agentmail", content=body, headers=headers)
    assert again.json() == {"email_id": email["id"], "duplicate": True}
    assert len([c for c in service.calls if c[1].startswith("http://agent.test")]) == 1


@pytest.mark.parametrize("changed_thread", [False, True])
def test_supplier_reply_inherits_ticket_and_routes_using_conversation_evidence(
    service, monkeypatch, changed_thread
):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "key")
    monkeypatch.setenv("AGENTMAIL_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent.test")
    ticket = "ticket:prop-1042"
    sent = service.post("/internal/send", headers=INTERNAL, json={
        "to": ["plumber@example.net"], "subject": "Quote request", "body": "Earliest attendance?",
        "entity_ids": [ticket], "run_id": "repair-run",
    }).json()
    incoming = {**INBOUND, "message": {
        **INBOUND["message"], "from": "Plumber <plumber@example.net>",
        "thread_id": "changed-thread" if changed_thread else sent["thread_id"],
        "in_reply_to": sent["message_id"], "references": [sent["message_id"]],
        "text": "We can attend at 14:00; quote £95 including VAT.",
    }}
    body, headers = signed(incoming)
    response = service.post("/webhooks/agentmail", content=body, headers=headers)
    assert response.status_code == 200, response.text
    received = response.json()["email_id"]
    state = service.app.state.store.snapshot()
    assert any(e["source"] == received and e["target"] == ticket and e["relation"] == "about"
               for e in state["edges"].values())
    event = next(c[2] for c in service.calls if c[1] == "http://agent.test/internal/events")
    assert sent["thread_id"] in event["subjects"] and sent["email_id"] in event["subjects"]

    # Continuing the supplier conversation keeps the ticket link without model input.
    followup = service.post("/internal/reply", headers=INTERNAL, json={
        "email_id": received, "body": "Please confirm the attendance window.",
    })
    assert followup.status_code == 200, followup.text
    assert any(e["source"] == followup.json()["email_id"] and e["target"] == ticket
               and e["relation"] == "about"
               for e in service.app.state.store.snapshot()["edges"].values())

    # Same sender and inbox, but different conversation: no task/ticket inheritance.
    unrelated = {**incoming, "message": {
        **incoming["message"], "message_id": "<unrelated@example.net>",
        "thread_id": "unrelated-thread", "in_reply_to": None, "references": [],
    }}
    body, headers = signed(unrelated)
    separate = service.post("/webhooks/agentmail", content=body, headers=headers).json()
    event = [c[2] for c in service.calls if c[1] == "http://agent.test/internal/events"][-1]
    assert event["subjects"] == ["unrelated-thread", separate["email_id"]]
    assert not any(e["source"] == separate["email_id"] and e["relation"] == "about"
                   for e in service.app.state.store.snapshot()["edges"].values())
