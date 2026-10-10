"""API-side email routes and MCP tools; AgentMail itself is only reached by the email service."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .auth import require_admin
from .services import call_service, record_action

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


class SendEmail(BaseModel):
    to: list[str] | str
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=100_000)
    entity_ids: list[str] = []
    run_id: str | None = None


@router.post("/emails")
def send(payload: SendEmail, request: Request):
    return call_service(request.app.state.settings, "email", "/internal/send", payload.model_dump())


def _tool(path, name):
    def handler(app, run_id, args):
        payload = {**args, "run_id": run_id}
        try:
            result = call_service(app.state.settings, "email", path, payload)
        except Exception as error:
            record_action(
                app.state.store, run_id, name, args, reason=args.get("reason", ""), error=str(error)
            )
            raise
        record_action(
            app.state.store,
            run_id,
            name,
            args,
            result,
            args.get("reason", ""),
            result.get("email_id"),
        )
        return result

    return handler


_IDS = {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 50}
_REASON = {"type": "string", "maxLength": 2000}

# MCP tools: {name: {"description", "input_schema", "handler"}}; handler(app, run_id, args) -> dict
TOOLS = {
    "send_email": {
        "description": "Send a new email from the agent's AgentMail inbox. Records it as an email "
        "entity linked to recipients and entity_ids (tickets, companies, people it concerns).",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 320},
                    "minItems": 1,
                },
                "subject": {"type": "string", "minLength": 1, "maxLength": 500},
                "body": {"type": "string", "minLength": 1, "maxLength": 100000},
                "entity_ids": _IDS,
                "reason": _REASON,
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
        "handler": _tool("/internal/send", "send_email"),
    },
    "reply_email": {
        "description": "Reply within the thread of an existing email entity (email_id, e.g. "
        "email:...). reply_all replies to every original recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "maxLength": 200},
                "body": {"type": "string", "minLength": 1, "maxLength": 100000},
                "reply_all": {"type": "boolean"},
                "entity_ids": _IDS,
                "reason": _REASON,
            },
            "required": ["email_id", "body"],
            "additionalProperties": False,
        },
        "handler": _tool("/internal/reply", "reply_email"),
    },
}
