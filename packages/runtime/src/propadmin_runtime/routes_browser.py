"""API-side browser routes and MCP tools. Owned by the browser service build."""

from fastapi import APIRouter, Depends, Request
from propadmin_core import publish
from propadmin_core.store import identifier, now
from pydantic import Field

from . import credentials as vault
from .auth import require_admin
from .models import Input
from .services import call_service, record_action

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])

PUBLIC = ("id", "name", "username", "allowed_domains", "has_totp", "created_at", "updated_at")


class CredentialIn(Input):
    id: str | None = None  # set to rotate an existing credential
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=1, max_length=2000)
    totp_seed: str | None = Field(default=None, max_length=200)
    allowed_domains: list[str] = Field(min_length=1, max_length=20)


def public(record):
    return {key: record.get(key) for key in PUBLIC}


@router.get("/credentials")
def list_credentials(request: Request):
    records = request.app.state.store.snapshot()["credentials"].values()
    return {"items": [public(record) for record in records]}


@router.post("/credentials")
def save_credential(payload: CredentialIn, request: Request):
    app = request.app
    domains = sorted({vault.normalise_domain(domain) for domain in payload.allowed_domains})
    if payload.totp_seed:
        try:
            vault.totp(payload.totp_seed)
        except ValueError:
            raise ValueError("TOTP seed must be base32") from None
    existing = app.state.store.snapshot()["credentials"]
    if payload.id and payload.id not in existing:
        raise KeyError(payload.id)
    credential_id = payload.id or identifier("credential")
    # Secret first: a failed vault write leaves no metadata pointing at nothing.
    vault.put_secret(
        app.state.settings,
        credential_id,
        {"password": payload.password, "totp_seed": payload.totp_seed},
    )

    def write(state):
        record = state["credentials"].get(credential_id, {"id": credential_id, "created_at": now()})
        record.update(
            name=payload.name,
            username=payload.username,
            allowed_domains=domains,
            has_totp=bool(payload.totp_seed),
            updated_at=now(),
        )
        state["credentials"][credential_id] = record
        publish(state, "credential.saved", {"id": credential_id})
        return public(record)

    return app.state.store.mutate(write)


@router.delete("/credentials/{credential_id}")
def delete_credential(credential_id: str, request: Request):
    app = request.app
    if credential_id not in app.state.store.snapshot()["credentials"]:
        raise KeyError(credential_id)
    vault.delete_secret(app.state.settings, credential_id)

    def write(state):
        state["credentials"].pop(credential_id, None)
        publish(state, "credential.deleted", {"id": credential_id})
        return {"id": credential_id, "deleted": True}

    return app.state.store.mutate(write)


def _tool(name, path, description, properties, required=()):
    def handler(app, run_id, args):
        try:
            result = call_service(
                app.state.settings,
                "browser",
                f"/internal/sessions/{run_id}/{path}",
                args,
                timeout=180,
            )
        except Exception as exc:
            record_action(app.state.store, run_id, name, args, error=str(exc))
            raise
        logged = {key: value for key, value in result.items() if key != "screenshot"}
        record_action(app.state.store, run_id, name, args, result=logged)
        return result

    schema = {"type": "object", "properties": properties, "required": list(required)}
    return name, {"description": description, "input_schema": schema, "handler": handler}


_TEXT = {"type": "string"}

# MCP tools: {name: {"description", "input_schema", "handler"}}; handler(app, run_id, args) -> dict
TOOLS = dict(
    [
        _tool(
            "browser_open",
            "open",
            "Start a browser session at a URL; profile is a credential id whose saved login "
            "should be restored. Returns page text and a JPEG screenshot (base64).",
            {"url": _TEXT, "profile": _TEXT},
            ("url",),
        ),
        _tool(
            "browser_act",
            "act",
            "Perform one natural-language action on the page, e.g. 'click Book a visit'.",
            {"instruction": _TEXT},
            ("instruction",),
        ),
        _tool(
            "browser_extract",
            "extract",
            "Extract structured data from the current page matching a JSON schema.",
            {"instruction": _TEXT, "schema": {"type": "object"}},
            ("instruction", "schema"),
        ),
        _tool(
            "browser_login",
            "login",
            "Log in with a stored credential id. Values are filled server-side and only on "
            "the credential's allowed domains; you only get the outcome.",
            {"credential": _TEXT},
            ("credential",),
        ),
        _tool("browser_screenshot", "screenshot", "Screenshot the current page as evidence.", {}),
        _tool("browser_close", "close", "End the browser session and save its login.", {}),
    ]
)
