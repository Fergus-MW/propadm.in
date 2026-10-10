"""Signed expiring admin/session tokens, plus authenticated service callbacks."""

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import HTTPException, Request


def issue_token(settings, actor="admin", lifetime=43200):
    payload = json.dumps(
        {"actor": actor, "exp": int(time.time()) + lifetime}, separators=(",", ":")
    ).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(settings.token_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_token(settings, token):
    try:
        body, supplied = token.split(".")
        expected = hmac.new(
            settings.token_secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ValueError("Invalid signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload["exp"] <= time.time() or not isinstance(payload["actor"], str):
            raise ValueError("Expired token")
        return payload["actor"]
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(401, "Invalid or expired token") from exc


def bearer(request):
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "Sign in to continue")
    return header[7:]


def require_admin(request: Request):
    actor = verify_token(request.app.state.settings, bearer(request))
    if actor != "admin":
        raise HTTPException(403, "Admin access required")
    return actor


def require_session(request: Request):
    actor = verify_token(request.app.state.settings, bearer(request))
    if not actor.startswith("agent_run:"):
        raise HTTPException(403, "Session token required")
    run_id = actor.removeprefix("agent_run:")
    grant = request.app.state.store.snapshot().get("mcp_sessions", {}).get(run_id)
    if not grant or grant.get("revoked"):
        raise HTTPException(403, "MCP access grant is not active")
    return run_id


def require_internal(request: Request):
    token = bearer(request)
    settings = request.app.state.settings
    if hmac.compare_digest(token, settings.internal_token):
        return "service"
    audience = os.getenv("SERVICE_BASE_URL")
    account = os.getenv("INTERNAL_CALLER_SERVICE_ACCOUNT")
    if audience and account:
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2.id_token import verify_oauth2_token

            claims = verify_oauth2_token(token, GoogleRequest(), audience=audience)
            if claims.get("email") == account and claims.get("email_verified"):
                return account
        except (ValueError, ImportError):
            pass
    raise HTTPException(403, "Service authentication required")
