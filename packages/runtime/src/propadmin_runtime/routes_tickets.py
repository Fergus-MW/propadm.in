"""Authenticated Markdown exports of a ticket's persisted completion fields."""

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from propadmin_core.ticket_completion import COMPLETED_STATUSES, validate_completion

from .auth import require_admin

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


class CompletionFile(str, Enum):
    answer = "answer.md"
    reasoning = "reasoning.md"


class MarkdownResponse(PlainTextResponse):
    media_type = "text/markdown"


@router.get("/tickets/{ticket_id}/exports/{filename}", response_class=MarkdownResponse)
def export_completion(ticket_id: str, filename: CompletionFile, request: Request):
    ticket = request.app.state.graph.get_entity(ticket_id)
    if ticket["type"] != "ticket" or ticket.get("merged_into"):
        raise KeyError(ticket_id)
    fields = ticket["fields"]
    if fields.get("status") not in COMPLETED_STATUSES:
        raise HTTPException(409, "Complete this ticket before exporting its answer or reasoning")
    validate_completion("ticket", fields)
    key = "final_answer" if filename == CompletionFile.answer else "reasoning"
    return MarkdownResponse(
        fields[key] + "\n",
        headers={
            "Content-Disposition": f'attachment; filename="{filename.value}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
