"""Property ledgers and provider directory: recorded financial events only."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import Field

from .auth import require_admin, require_internal
from .models import EntityCreate, EntityUpdate, Input

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])
internal = APIRouter(prefix="/internal", dependencies=[Depends(require_internal)])


class TransactionWrite(Input):
    property_id: str | None = None
    fields: dict[str, Any]
    paid_by: str | None = None
    paid_to: str | None = None
    ticket_id: str | None = None
    evidence: list[str | dict[str, Any]] = Field(default_factory=list)
    source_file: str | None = None
    settles: str | list[dict[str, Any]] | None = None
    adjustment_deltas: dict[str, int] | None = None


class Reason(Input):
    reason: str = Field(min_length=1, max_length=2000)


class Status(Reason):
    status: str


class Allocation(Input):
    property_id: str
    category: str | None = None
    kind: Literal["charge", "payment", "transfer", "adjustment"] | None = None


class Settlement(Input):
    charge_id: str
    amount_minor: int | None = Field(default=None, strict=True, gt=0)


class OfferingWrite(Input):
    name: str | None = None
    description: str = ""
    fields: dict[str, Any]
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    version: int | None = Field(default=None, ge=1)


class QuoteWrite(Input):
    provider_id: str
    ticket_id: str
    fields: dict[str, Any]


class Relationship(Input):
    source: str
    target: str
    relation: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=2000)


@router.post("/relationships", status_code=201)
def link_relationship(payload: Relationship, request: Request):
    value = payload.model_dump()
    reason = value.pop("reason")
    return request.app.state.graph.link_entities(value, reason=reason)


def enrich_property(app, ref):
    result = app.state.ledger.get_property(ref)
    state = app.state.store.snapshot()
    for key, relation in (("owners", "owns"), ("tenants", "tenant_of"),
                          ("managing_companies", "manages"), ("open_tickets", "at"),
                          ("emails", "about"), ("calls", "about")):
        rows = []
        for edge in result["edges"]:
            if edge["target"] != result["id"] or edge["relation"] != relation:
                continue
            item = state["entities"].get(edge["source"])
            if not item:
                continue
            if key == "open_tickets" and (item["type"] != "ticket" or
                                         item["fields"].get("status") in {"resolved", "closed"}):
                continue
            if key in {"emails", "calls"} and item["type"] != key[:-1]:
                continue
            rows.append({**item, "relationship": edge})
        result[key] = rows
    return result


@router.get("/properties")
def properties(request: Request, q: str | None = None, status: str | None = None):
    return {"items": [row for row in request.app.state.ledger.properties()
                      if (not q or q.casefold() in str(row).casefold())
                      and (not status or row["fields"].get("status") == status)]}


@router.get("/properties/{property_id}")
def property_detail(property_id: str, request: Request):
    return enrich_property(request.app, property_id)


@router.get("/properties/{property_id}/ledger")
def ledger(property_id: str, request: Request, from_date: str | None = Query(None, alias="from"),
           to_date: str | None = Query(None, alias="to"), category: str | None = None):
    return request.app.state.ledger.get_ledger(property_id, from_date, to_date, category)


@router.get("/properties/{property_id}/balances")
def balances(property_id: str, request: Request):
    return request.app.state.ledger.get_balances(property_id)


@router.get("/landlords")
def landlords(request: Request):
    state = request.app.state.store.snapshot()
    owners = {edge["source"] for edge in state["edges"].values() if edge["relation"] == "owns"}
    rows = []
    for key in sorted(owners):
        item = state["entities"].get(key)
        if item and item["type"] in {"person", "company"} and not item.get("merged_into"):
            balance = request.app.state.ledger.get_balances(key)
            rows.append({**item, "balances": balance, "property_count": len(balance["properties"])})
    return {"items": rows}


@router.get("/landlords/{landlord_id}/statement")
def landlord_statement(landlord_id: str, period: str, request: Request):
    result = request.app.state.ledger.statement(landlord_id, period)
    if result["subject"]["type"] not in {"person", "company"}:
        raise ValueError("Landlord statement requires a person or company")
    for row in result["properties"]:
        row.update(id=row["property"]["id"], name=row["property"]["name"], type="property")
        row["balances"] = row["closing_balances"]
    result["landlord"] = result["subject"]
    return result


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, request: Request):
    import base64
    import re

    document = request.app.state.store.snapshot()["documents"][document_id]
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", document["filename"])
    content = (base64.b64decode(document["raw_content_base64"])
               if document.get("raw_content_base64") else document["text"].encode())
    mime = document["mime"] if document.get("raw_content_base64") else "text/plain; charset=utf-8"
    return Response(content, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "Cache-Control": "no-store"})


@router.get("/statements/{subject}")
def statement(subject: str, period: str, request: Request, format: Literal["pdf", "json"] = "pdf"):
    if format == "json":
        return request.app.state.ledger.statement(subject, period)
    from .statements import generate_statement, statement_bytes

    result = generate_statement(request.app, subject, period)
    return Response(statement_bytes(request.app, result["document_id"]), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"',
                             "Cache-Control": "no-store"})


@router.get("/ledger/unallocated")
def unallocated(request: Request):
    return {"items": request.app.state.ledger.unallocated()}


@router.post("/transactions", status_code=201)
def record_transaction(payload: TransactionWrite, request: Request):
    return request.app.state.ledger.record_transaction(payload.model_dump(exclude_none=True))


@router.post("/transactions/{transaction_id}/reverse", status_code=201)
def reverse_transaction(transaction_id: str, payload: Reason, request: Request):
    from .tools_ledger import reverse_with_workflow

    return reverse_with_workflow(request.app, transaction_id, payload.reason)


@router.post("/transactions/{transaction_id}/status")
def transaction_status(transaction_id: str, payload: Status, request: Request):
    return request.app.state.ledger.promote_status(transaction_id, payload.status, reason=payload.reason)


@router.post("/transactions/{transaction_id}/allocate")
def allocate(transaction_id: str, payload: Allocation, request: Request):
    return request.app.state.ledger.allocate(transaction_id, payload.property_id,
                                             category=payload.category, kind=payload.kind)


@router.post("/transactions/{transaction_id}/settle")
def settle(transaction_id: str, payload: Settlement, request: Request):
    return request.app.state.ledger.settle(transaction_id, payload.charge_id, payload.amount_minor)


@router.get("/providers")
def providers(request: Request, trade: str | None = None, property_id: str | None = None,
              postcode: str | None = None, urgency: str | None = None, service: str | None = None,
              status: str | None = None, q: str | None = None, min_rating: float | None = None):
    return {"items": request.app.state.providers.find_providers(
        trade=trade, property_id=property_id, postcode=postcode, urgency=urgency,
        service=service, status=status, q=q, min_rating=min_rating)}


@router.get("/providers/{provider_id}")
def provider_detail(provider_id: str, request: Request):
    return request.app.state.providers.get_provider(provider_id)


@router.post("/providers", status_code=201)
def create_provider(payload: EntityCreate, request: Request):
    if payload.type != "service_provider":
        raise ValueError("Provider type must be service_provider")
    value = payload.model_dump(exclude_none=True)
    value.pop("reason", None)
    return request.app.state.providers.upsert_provider(value)


@router.patch("/providers/{provider_id}")
def update_provider(provider_id: str, payload: EntityUpdate, request: Request):
    value = payload.model_dump(exclude_none=True)
    value.pop("reason", None)
    return request.app.state.providers.upsert_provider(value, id=provider_id)


@router.post("/providers/{provider_id}/status")
def provider_status(provider_id: str, payload: Status, request: Request):
    return request.app.state.providers.set_provider_status(provider_id, payload.status, payload.reason)


@router.post("/providers/{provider_id}/offerings", status_code=201)
def create_offering(provider_id: str, payload: OfferingWrite, request: Request):
    return request.app.state.providers.upsert_offering(
        payload.model_dump(exclude_none=True), provider_id)


@router.patch("/providers/{provider_id}/offerings/{offering_id}")
def update_offering(provider_id: str, offering_id: str, payload: OfferingWrite, request: Request):
    return request.app.state.providers.upsert_offering(
        payload.model_dump(exclude_none=True), provider_id, id=offering_id)


@router.post("/quotes", status_code=201)
def record_quote(payload: QuoteWrite, request: Request):
    return request.app.state.providers.record_quote(payload.provider_id, payload.ticket_id,
                                                   {"fields": payload.fields})


@router.post("/quotes/{quote_id}/accept")
def accept_quote(quote_id: str, request: Request):
    return request.app.state.providers.accept_quote(quote_id)


@internal.post("/rent-schedule")
def rent_schedule(request: Request, as_of: str | None = None):
    return request.app.state.ledger.generate_rent_due(as_of)
