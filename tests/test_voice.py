"""Voice: provider gating, outbound request shape, inbound brief, signed post-call ingest."""

import hashlib
import hmac
import importlib.util
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_runtime import create_app

spec = importlib.util.spec_from_file_location(
    "voice_routes", Path(__file__).parents[1] / "services/voice/app/voice.py"
)
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)

SECRET = "whsec-test"
TOOL_SECRET = "tool-test"
INTERNAL = {"Authorization": "Bearer propadmin-local-internal-development-only"}


class Reply:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


@pytest.fixture
def client(monkeypatch):
    for name in ("ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "ELEVENLABS_PHONE_NUMBER_ID"):
        monkeypatch.setenv(name, name.lower())
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("ELEVENLABS_TOOL_SECRET", TOOL_SECRET)
    events = []
    monkeypatch.setattr(
        voice,
        "call_service",
        lambda s, n, p, payload, **k: events.append(payload) or {"run_id": "run-1"},
    )
    app = create_app("voice", store=Store(None), seed=True)
    app.include_router(voice.internal)
    app.include_router(voice.webhooks)
    with TestClient(app) as instance:
        instance.events = events
        yield instance


def test_unconfigured_providers_are_503(monkeypatch):
    monkeypatch.delenv("VOICE_SERVICE_URL", raising=False)
    with TestClient(create_app(store=Store(None), seed=True)) as api:
        token = api.post("/v1/auth/login", json={"password": "propadmin-local"}).json()["token"]
        response = api.post(
            "/v1/calls",
            json={"entity_id": "person:aisha-khan", "objective": "Confirm access"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    app = create_app("voice", store=Store(None), seed=True)
    app.include_router(voice.internal)
    with TestClient(app) as instance:
        response = instance.post(
            "/internal/calls",
            json={"entity_id": "person:aisha-khan", "objective": "x"},
            headers=INTERNAL,
        )
        assert response.status_code == 503


def test_outbound_call_request_shape(client, monkeypatch):
    sent = {}

    def post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, json=json)
        return Reply(
            {"success": True, "message": "ok", "conversation_id": "conv_1", "sip_call_id": "sip-1"}
        )

    monkeypatch.setattr(voice.httpx, "post", post)
    response = client.post(
        "/internal/calls",
        json={
            "entity_id": "ticket:prop-1042",
            "objective": "Confirm Tuesday access",
            "brief": "Be brief",
            "run_id": "run-1",
        },
        headers=INTERNAL,
    )
    assert response.status_code == 200, response.text
    assert sent["url"] == "https://api.elevenlabs.io/v1/convai/sip-trunk/outbound-call"
    assert sent["headers"] == {"xi-api-key": "elevenlabs_api_key"}
    body = sent["json"]
    assert body["agent_id"] == "elevenlabs_agent_id"
    assert body["agent_phone_number_id"] == "elevenlabs_phone_number_id"
    assert body["to_number"].startswith("+44")
    variables = body["conversation_initiation_client_data"]["dynamic_variables"]
    assert variables["run_id"] == "run-1" and variables["brief"].startswith("Be brief")
    call = response.json()["call"]
    assert call["fields"]["call_id"] == "conv_1" and call["fields"]["direction"] == "outbound"


def test_initiation_resolves_caller_and_rejects_bad_secret(client):
    url = "/webhooks/elevenlabs/initiation"
    payload = {
        "caller_id": "07700 900101",
        "called_number": "+442000000000",
        "conversation_id": "conv_in",
    }
    assert client.post(url, json=payload, headers={"X-Webhook-Secret": "wrong"}).status_code == 401
    reply = client.post(url, json=payload, headers={"X-Webhook-Secret": TOOL_SECRET}).json()
    assert reply["type"] == "conversation_initiation_client_data"
    assert reply["dynamic_variables"]["contact_name"] == "Aisha Khan"
    assert "Aisha Khan" in reply["dynamic_variables"]["brief"]
    assert reply["dynamic_variables"]["run_id"] == "run-1"
    unknown = client.post(
        url,
        json={"caller_id": "+15550000000", "conversation_id": "conv_x"},
        headers={"X-Webhook-Secret": TOOL_SECRET},
    ).json()
    assert unknown["dynamic_variables"]["brief"] == voice.GENERIC_BRIEF


def signed(body, secret=SECRET):
    t = str(int(time.time()))
    digest = hmac.new(secret.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
    return {"ElevenLabs-Signature": f"t={t},v0={digest}", "Content-Type": "application/json"}


def test_post_call_verifies_signature_updates_call_and_ingests(client):
    client.post(
        "/webhooks/elevenlabs/initiation",
        json={"caller_id": "+447700900101", "conversation_id": "conv_2"},
        headers={"X-Webhook-Secret": TOOL_SECRET},
    )
    body = json.dumps(
        {
            "type": "post_call_transcription",
            "event_timestamp": 1739537297,
            "data": {
                "agent_id": "a",
                "conversation_id": "conv_2",
                "status": "done",
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Hello Aisha Khan, about PROP-1042.",
                        "time_in_call_secs": 0,
                    },
                    {
                        "role": "user",
                        "message": "Tuesday after 17:00 works.",
                        "time_in_call_secs": 3,
                    },
                ],
                "metadata": {"start_time_unix_secs": 1739537297, "call_duration_secs": 22},
                "analysis": {"transcript_summary": "Access agreed for Tuesday evening."},
                "conversation_initiation_client_data": {"dynamic_variables": {"run_id": "run-1"}},
            },
        }
    )
    url = "/webhooks/elevenlabs/post-call"
    assert client.post(url, content=body, headers=signed(body, "wrong")).status_code == 401
    response = client.post(url, content=body, headers=signed(body))
    assert response.status_code == 200, response.text
    result = response.json()
    call = client.app.state.graph.get_entity(result["call_id"])
    assert call["fields"]["status"] == "completed" and call["fields"]["duration_s"] == 22
    assert call["fields"]["summary"] == "Access agreed for Tuesday evening."
    assert "Caller: Tuesday after 17:00 works." in call["fields"]["transcript_text"]
    document = client.app.state.graph.get_document(result["document_id"])
    assert document["origin"] == "elevenlabs"
    relations = {(e["relation"], e["target"]) for e in call["edges"]}
    assert ("derived_from", result["document_id"]) in relations
    assert ("with", "person:aisha-khan") in relations
    assert "ticket:prop-1042" in document["entities"]
    ended = client.events[-1]
    assert ended["kind"] == "call.ended" and ended["data"]["run_id"] == "run-1"


def test_server_tool_scoped_to_session_and_read_tools_take_no_reason(client):
    url, headers = "/tools/voice/get_entity", {"X-Webhook-Secret": TOOL_SECRET}
    body = {"run_id": "run-1", "id": "person:aisha-khan"}
    assert client.post(url, json=body, headers={"X-Webhook-Secret": SECRET}).status_code == 401
    assert client.post(url, json=body, headers=headers).status_code == 403
    client.app.state.store.mutate(
        lambda state: state.setdefault("mcp_sessions", {}).update(
            {"run-1": {"session_id": "run-1", "revoked": False}}
        )
    )
    response = client.post(url, json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Aisha Khan"


def test_sip_international_caller_without_plus_is_recognised(client):
    reply = client.post('/webhooks/elevenlabs/initiation',
        json={'caller_id': '447700900101', 'conversation_id': 'conv_digits'},
        headers={'X-Webhook-Secret': TOOL_SECRET})
    assert reply.status_code == 200
    assert reply.json()['dynamic_variables']['contact_name'] == 'Aisha Khan'
    call = voice.call_entity(client.app.state.store.snapshot(), 'conv_digits')
    assert call['fields']['from_number'] == '+447700900101'


def test_signed_initiation_failure_settles_call_and_repeated_webhook_is_deduplicated(client):
    client.post('/webhooks/elevenlabs/initiation',
        json={'caller_id': '447700900101', 'conversation_id': 'conv_failed'},
        headers={'X-Webhook-Secret': TOOL_SECRET})
    body = json.dumps({'type': 'call_initiation_failure', 'event_timestamp': int(time.time()),
                      'data': {'conversation_id': 'conv_failed', 'failure_reason': 'busy'}})
    path = '/webhooks/elevenlabs/post-call'
    assert client.post(path, content=body, headers=signed(body, 'wrong')).status_code == 401
    response = client.post(path, content=body, headers=signed(body))
    assert response.status_code == 200, response.text
    call = client.app.state.graph.get_entity(response.json()['call_id'])
    assert call['fields']['status'] == 'busy' and call['fields']['ended_at']
    events = len(client.events)
    repeated = client.post(path, content=body, headers=signed(body))
    assert repeated.json()['deduplicated']
    assert len(client.events) == events
