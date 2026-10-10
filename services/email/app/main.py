"""Email service: AgentMail inboxes, send/reply, and signature-verified inbound webhooks.

Every sent or received message becomes an email entity plus a source document via ingestion.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from email.utils import getaddresses
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from propadmin_core import ProviderNotConfigured
from propadmin_core.graph import add_edge
from propadmin_core.store import now
from propadmin_runtime import create_app
from propadmin_runtime.auth import require_internal
from propadmin_runtime.services import call_service

AGENTMAIL_URL = os.getenv("AGENTMAIL_BASE_URL", "https://api.agentmail.to/v0").rstrip("/")


def domain():
    return os.getenv("AGENTMAIL_DOMAIN", "withproperly.com")


def personas():
    return [
        name.strip() for name in os.getenv("AGENTMAIL_INBOXES", "ops").split(",") if name.strip()
    ]


def agentmail(method, path, payload=None):
    key = os.getenv("AGENTMAIL_API_KEY")
    if not key:
        raise ProviderNotConfigured("AgentMail is not configured (AGENTMAIL_API_KEY)")
    response = httpx.request(
        method, AGENTMAIL_URL + path, json=payload, timeout=30,
        headers={"Authorization": f"Bearer {key}"},
    )  # fmt: skip
    if response.status_code >= 400:
        raise HTTPException(502, f"AgentMail returned HTTP {response.status_code}")
    return response.json()


def find_email(state, message_id):
    return next(
        (
            entity
            for entity in state["entities"].values()
            if entity["type"] == "email"
            and not entity.get("merged_into")
            and entity["fields"].get("message_id") == message_id
        ),
        None,
    )


def record_email(app, fields, entity_ids=(), run_id=None):
    """Ingest one message as a document whose records resolve the email and its people."""
    people = getaddresses(
        [f"{fields.get('from_name', '')} <{fields['from_address']}>"]
        + fields.get("to_addresses", [])
        + fields.get("cc_addresses", [])
    )
    text = (
        f"From: {fields['from_address']}\nTo: {', '.join(fields.get('to_addresses', []))}\n"
        f"Subject: {fields['subject']}\nMessage-ID: {fields['message_id']}\n\n{fields['body_full']}"
    )
    records = [
        {
            "type": "email",
            "name": fields["subject"],
            "description": fields["body_text"][:500],
            "fields": fields,
        }
    ] + [
        {"type": "person", "name": name or address, "fields": {"emails": [address]}}
        for name, address in people
        if address
    ]
    job = app.state.ingestion.ingest(
        {
            "filename": f"{fields['message_id'].strip('<>')}.txt",
            "title": fields["subject"],
            "mime": "text/plain",
            "origin": "agentmail",
            "text": text,
            "records": records,
        }
    )
    email = find_email(app.state.store.snapshot(), fields["message_id"])
    for entity_id in entity_ids:
        app.state.graph.link_entities(
            {"source": email["id"], "target": entity_id, "relation": "about"},
            actor=f"agent_run:{run_id}" if run_id else "email",
            reason="Email concerns this entity",
        )
    return email, job


def check_entities(app, entity_ids):
    entities = app.state.store.snapshot()["entities"]
    missing = [key for key in entity_ids if key not in entities]
    if missing:
        raise ValueError(f"Unknown entity ids: {', '.join(missing)}")


def outbound_fields(sent, inbox, to, subject, body, run_id, **extra):
    return {
        "message_id": sent["message_id"],
        "thread_id": sent["thread_id"],
        "channel": "agentmail",
        "mailbox": inbox,
        "direction": "outbound",
        "status": "sent",
        "subject": subject,
        "from_address": inbox,
        "to_addresses": to,
        "sent_at": now(),
        "body_text": body,
        "body_full": body,
        **({"agent_session": run_id} if run_id else {}),
        **extra,
    }


def verify_signature(headers, body):
    """Svix scheme used by AgentMail: HMAC-SHA256 over "id.timestamp.body", base64, "v1,<sig>"."""
    secret = os.getenv("AGENTMAIL_WEBHOOK_SECRET")
    if not secret:
        raise ProviderNotConfigured(
            "AgentMail webhooks are not configured (AGENTMAIL_WEBHOOK_SECRET)"
        )
    try:
        message_id, stamp = headers["svix-id"], headers["svix-timestamp"]
        if abs(time.time() - int(stamp)) > 300:
            raise ValueError("stale timestamp")
        key = base64.b64decode(secret.removeprefix("whsec_"))
        signed = hmac.new(key, f"{message_id}.{stamp}.".encode() + body, hashlib.sha256).digest()
        expected = base64.b64encode(signed).decode()
        if not any(
            hmac.compare_digest(expected, part.partition(",")[2])
            for part in headers["svix-signature"].split()
        ):
            raise ValueError("signature mismatch")
    except (KeyError, ValueError) as exc:
        raise HTTPException(401, "Invalid webhook signature") from exc


def ingest_attachments(app, message):
    """Download each attachment's text and ingest it as a document."""
    result = []
    for item in message.get("attachments") or []:
        meta = agentmail(
            "GET",
            f"/inboxes/{quote(message['inbox_id'], safe='')}/messages/"
            f"{quote(message['message_id'], safe='')}/attachments/{quote(item['attachment_id'], safe='')}",
        )
        mime = meta.get("content_type") or item.get("content_type") or "application/octet-stream"
        # ponytail: text attachments and AgentMail's text_url only; raw bytes are not stored in
        # GCS yet (cloud scope) and binaries without text_url wait for a parser.
        url = meta.get("text_url") or (
            meta.get("download_url") if mime.startswith("text/") else None
        )
        attachment = {"filename": meta.get("filename") or item.get("filename") or "attachment",
                      "mime": mime, "size": meta.get("size", item.get("size", 0))}  # fmt: skip
        if url:
            download = httpx.request("GET", url, timeout=60)
            if download.status_code >= 400:
                raise HTTPException(
                    502, f"Attachment download returned HTTP {download.status_code}"
                )
            if download.text.strip():
                job = app.state.ingestion.ingest(
                    {"filename": attachment["filename"], "title": attachment["filename"],
                     "mime": "text/plain", "origin": "agentmail", "text": download.text}
                )  # fmt: skip
                attachment["document"] = job["document_id"]
        result.append(attachment)
    return result


def build(app):
    internal = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])

    @internal.post("/inboxes/provision")
    def provision():
        # client_id makes AgentMail return the existing inbox on re-runs.
        return {
            "items": [
                agentmail(
                    "POST",
                    "/inboxes",
                    {
                        "username": name,
                        "domain": domain(),
                        "display_name": f"Properly {name}",
                        "client_id": f"propadmin-{name}@{domain()}",
                    },
                )
                for name in personas()
            ]
        }

    @internal.post("/send")
    async def send(request: Request):
        payload = await request.json()
        to = payload.get("to")
        to = [to] if isinstance(to, str) else to
        if not to or not payload.get("subject") or not payload.get("body"):
            raise ValueError("to, subject and body are required")
        entity_ids = payload.get("entity_ids") or []
        check_entities(app, entity_ids)
        inbox = payload.get("inbox") or f"{personas()[0]}@{domain()}"
        sent = agentmail(
            "POST",
            f"/inboxes/{quote(inbox, safe='')}/messages/send",
            {"to": to, "subject": payload["subject"], "text": payload["body"]},
        )
        fields = outbound_fields(
            sent, inbox, to, payload["subject"], payload["body"], payload.get("run_id")
        )
        email, job = record_email(app, fields, entity_ids, payload.get("run_id"))
        return {**sent, "email_id": email["id"], "document_id": job["document_id"]}

    @internal.post("/reply")
    async def reply(request: Request):
        payload = await request.json()
        if not payload.get("body"):
            raise ValueError("body is required")
        original = app.state.graph.get_entity(payload["email_id"])
        if original["type"] != "email" or not original["fields"].get("mailbox"):
            raise ValueError("email_id must be an AgentMail email entity")
        entity_ids = payload.get("entity_ids") or []
        check_entities(app, entity_ids)
        prior = original["fields"]
        inbox, reply_all = prior["mailbox"], bool(payload.get("reply_all"))
        sent = agentmail(
            "POST",
            f"/inboxes/{quote(inbox, safe='')}/messages/{quote(prior['message_id'], safe='')}/reply",
            {"text": payload["body"], "reply_all": reply_all},
        )
        if prior.get("direction") == "outbound":
            to = prior.get("to_addresses", [])
        else:
            to = [prior["from_address"]]
            if reply_all:
                to += [a for a in prior.get("to_addresses", []) + prior.get("cc_addresses", [])
                       if a != inbox]  # fmt: skip
        subject = prior["subject"]
        subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        fields = outbound_fields(
            sent, inbox, to, subject, payload["body"], payload.get("run_id"),
            in_reply_to=prior["message_id"],
            references=prior.get("references", []) + [prior["message_id"]],
        )  # fmt: skip
        email, job = record_email(app, fields, entity_ids, payload.get("run_id"))
        return {**sent, "email_id": email["id"], "document_id": job["document_id"]}

    @app.post("/webhooks/agentmail")
    async def webhook(request: Request):
        body = await request.body()
        verify_signature(request.headers, body)
        event = json.loads(body)
        # ponytail: spam/blocked/unauthenticated variants are ignored, not ingested.
        if event.get("event_type") != "message.received":
            return {"ignored": event.get("event_type")}
        message = event["message"]
        # ponytail: check-then-write; two concurrent deliveries of one message could both pass.
        # Ingestion still resolves them to one entity by message_id; only the agent may hear twice.
        existing = find_email(app.state.store.snapshot(), message["message_id"])
        if existing:
            return {"email_id": existing["id"], "duplicate": True}
        sender = message.get("from") or message.get("from_") or ""
        sender = getaddresses(sender if isinstance(sender, list) else [sender])
        name, address = sender[0] if sender else ("", "")
        attachments = ingest_attachments(app, message)
        text = message.get("text") or message.get("preview") or ""
        fields = {
            "message_id": message["message_id"],
            "thread_id": message["thread_id"],
            "references": message.get("references") or [],
            "channel": "agentmail",
            "mailbox": message["inbox_id"],
            "direction": "inbound",
            "status": "received",
            "subject": message.get("subject") or "(no subject)",
            "from_address": address,
            "from_name": name,
            "to_addresses": [a for _, a in getaddresses(message.get("to") or []) if a],
            "cc_addresses": [a for _, a in getaddresses(message.get("cc") or []) if a],
            "received_at": message.get("timestamp") or now(),
            "body_text": message.get("extracted_text") or text,
            "body_full": text,
            "labels": message.get("labels") or [],
            "attachments": attachments,
        }
        if message.get("in_reply_to"):
            fields["in_reply_to"] = message["in_reply_to"]
        # ponytail: ingested in-process; Pub/Sub fan-out to the ingestion service comes with cloud.
        email, job = record_email(app, fields)

        def link(state):
            for attachment in attachments:
                if attachment.get("document"):
                    add_edge(state, email["id"], attachment["document"], "has_attachment")

        app.state.store.mutate(link)
        try:
            agent = call_service(
                app.state.settings,
                "agent",
                "/internal/events",
                {
                    "kind": "email.received",
                    "subjects": list(dict.fromkeys([fields["thread_id"], *job["entities"]])),
                    "summary": f"Email from {address}: {fields['subject']}",
                    "data": {"email_id": email["id"], "message_id": fields["message_id"],
                             "thread_id": fields["thread_id"], "from": address,
                             "subject": fields["subject"], "body": fields["body_text"][:4000]},
                },
            )  # fmt: skip
        except ProviderNotConfigured:
            agent = None
        except (ValueError, httpx.HTTPError) as error:
            # The email is stored; a failed wake-up must not make AgentMail redeliver forever.
            agent = {"error": str(error)}
        return {"email_id": email["id"], "document_id": job["document_id"], "agent": agent}

    app.include_router(internal)
    return app


app = build(create_app("email"))
