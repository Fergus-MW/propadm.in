"""API-side voice routes and MCP tools. Owned by the voice service build."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .auth import require_admin
from .services import call_service, record_action

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


class CallRequest(BaseModel):
    entity_id: str = Field(min_length=1, max_length=500)
    objective: str = Field(min_length=1, max_length=4000)
    run_id: str | None = None


@router.post("/calls")
def place_call(payload: CallRequest, request: Request):
    """Forward to the voice service; with no VOICE_SERVICE_URL this is an explicit 503."""
    return call_service(
        request.app.state.settings, "voice", "/internal/calls", payload.model_dump()
    )


def place_call_tool(app, run_id, args):
    try:
        result = call_service(
            app.state.settings, "voice", "/internal/calls", {**args, "run_id": run_id}
        )
    except Exception as error:
        record_action(
            app.state.store,
            run_id,
            "place_call",
            args,
            None,
            args.get("objective", ""),
            args.get("entity_id"),
            str(error),
        )
        raise
    record_action(
        app.state.store,
        run_id,
        "place_call",
        args,
        result,
        args.get("objective", ""),
        args.get("entity_id"),
    )
    return result


# MCP tools: {name: {"description", "input_schema", "handler"}}; handler(app, run_id, args) -> dict
TOOLS = {
    "place_call": {
        "description": (
            "Place an outbound phone call through the ElevenLabs voice agent. The callee is the "
            "entity (or its linked person) with a phone number; the brief is added to a graph-built "
            "call brief. The transcript and outcome return to this session when the call ends."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "maxLength": 500},
                "objective": {"type": "string", "maxLength": 4000},
                "brief": {"type": "string", "maxLength": 20000},
            },
            "required": ["entity_id", "objective"],
            "additionalProperties": False,
        },
        "handler": place_call_tool,
    }
}
