"""Durable delivery receipts and provider idempotency, independent of extraction."""

import hashlib
import json
import re
import time
import uuid

from fastapi import HTTPException
from propadmin_core.store import now, publish


def delivery_key(payload, inbox, operation, content):
    fingerprint = hashlib.sha256(json.dumps(
        [inbox, operation, content], sort_keys=True, ensure_ascii=False,
    ).encode()).hexdigest()
    supplied = payload.get("idempotency_key")
    if supplied is not None:
        if not isinstance(supplied, str) or not re.fullmatch(r"[A-Za-z0-9._~-]{1,256}", supplied):
            raise ValueError("Invalid email idempotency_key")
        key = supplied
    elif payload.get("run_id"):
        # Ignore reasons/entity links: a retry of the same communication is one send.
        key = hashlib.sha256(f"{payload['run_id']}:{fingerprint}".encode()).hexdigest()
    else:
        key = uuid.uuid4().hex
    return key, fingerprint


def reserve(app, key, fingerprint):
    def write(state):
        deliveries = state.setdefault("email_deliveries", {})
        prior = deliveries.get(key)
        if prior:
            if prior["fingerprint"] != fingerprint:
                raise HTTPException(409, "Email idempotency_key already identifies different content")
            # AgentMail retains keys for 24h. An uncertain old attempt must not resend.
            if not prior.get("sent") and time.time() - prior["reserved_at"] >= 86400:
                raise HTTPException(409, "Unconfirmed email delivery requires reconciliation")
            return prior
        deliveries[key] = {"fingerprint": fingerprint, "reserved_at": time.time()}
        return deliveries[key]

    return app.state.store.mutate(write)


def accept(app, key, sent, fields, run_id):
    def write(state):
        receipt = state["email_deliveries"][key]
        receipt.update(sent=sent, fields=fields, accepted_at=now())
        run = state["runs"].get(run_id)
        if run and run["status"] in {"queued", "running", "sleeping"}:
            run["subjects"] = sorted(set(run["subjects"]) | {sent["thread_id"]})
            run["updated_at"] = now()
            publish(state, "agent_run.subjects", {"run_id": run_id, "subjects": run["subjects"]})
        publish(state, "email.sent", {"message_id": sent["message_id"], "thread_id": sent["thread_id"]})

    app.state.store.mutate(write)


def finish(app, key, sent, fields, entity_ids, run_id, record_email):
    result = {**sent, "status": "sent", "idempotency_key": key}
    try:
        # Store receipt and claim the thread BEFORE fallible model enrichment.
        accept(app, key, sent, fields, run_id)
        email, job = record_email(app, fields, entity_ids, run_id)
        result.update(email_id=email["id"], document_id=job["document_id"])
        if job.get("delivery_warning"):
            result["warning"] = job["delivery_warning"]
        app.state.store.mutate(lambda state: state["email_deliveries"][key].update(result=result))
    except Exception:
        # Provider acceptance is irreversible. Never describe it as a failed send.
        result["warning"] = "Email sent; local recording is incomplete. Do not resend."
        app.state.telemetry.emit("email.recording_failed", result, severity="ERROR")
    return result
