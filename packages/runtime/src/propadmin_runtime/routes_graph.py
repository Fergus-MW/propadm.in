"""Admin graph API and binary/SSE transports, backed by the shared domain layer."""

import asyncio
import json
import struct

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from .auth import require_admin
from .models import Compile, EntityCreate, EntityUpdate, Merge, Rule, Search, Upload

router = APIRouter(prefix="/v1", dependencies=[Depends(require_admin)])


@router.get("/overview")
def overview(request: Request):
    state = request.app.state.store.snapshot()
    entities = [e for e in state["entities"].values() if not e.get("merged_into")]
    counts = {
        kind: sum(e["type"] == kind for e in entities)
        for kind in ("person", "company", "ticket", "email", "call")
    }
    counts.update(
        entities=len(entities),
        edges=len(state["edges"]),
        documents=len(state["documents"]),
        active_runs=sum(r["status"] in {"running", "sleeping"} for r in state["runs"].values()),
    )
    return {
        "counts": counts,
        "recent_actions": sorted(
            state["actions"].values(), key=lambda a: a.get("created_at", ""), reverse=True
        )[:8],
        "runtime": request.app.state.settings.public(),
        "ingestion": list(state["jobs"].values())[-5:],
    }


@router.get("/entities")
def entities(request: Request, type: str | None = None, q: str | None = None):
    return {"items": request.app.state.graph.list_entities(type=type, q=q)}


@router.post("/entities", status_code=201)
def create_entity(payload: EntityCreate, request: Request):
    value = payload.model_dump()
    reason = value.pop("reason")
    return request.app.state.graph.create_entity(value, reason=reason)


@router.get("/entities/graph")
def graph(request: Request, type: str | None = None, include_transactions: bool = False,
          property_id: str | None = None):
    return explorer_graph(request, type=type, include_transactions=include_transactions,
                          property_id=property_id)


def explorer_graph(request, *, type=None, entity_id=None, depth=1,
                   include_transactions=False, property_id=None):
    value = request.app.state.graph.graph(type=type, entity_id=entity_id, depth=depth)
    allowed = set()
    if include_transactions and property_id:
        prop = request.app.state.ledger.get_property(property_id)["id"]
        allowed = {edge["source"] for edge in request.app.state.store.snapshot()["edges"].values()
                   if edge["relation"] == "for" and edge["target"] == prop}
    value["nodes"] = [node for node in value["nodes"]
                      if node["type"] != "transaction" or node["id"] in allowed]
    ids = {node["id"] for node in value["nodes"]}
    value["edges"] = [edge for edge in value["edges"]
                      if edge["source"] in ids and edge["target"] in ids]
    return value


def binary_graph(value):
    nodes, edges = value["nodes"], value["edges"]
    indices = {node["id"]: i for i, node in enumerate(nodes)}
    edges = [edge for edge in edges if edge["source"] in indices and edge["target"] in indices]
    metadata = json.dumps(
        {"nodes": nodes, "edges": edges, "version": value["version"]}, separators=(",", ":")
    ).encode()
    positions = [float(node.get(axis) or 0) for node in nodes for axis in ("layout_x", "layout_y")]
    pairs = [indices[edge[side]] for edge in edges for side in ("source", "target")]
    return (
        b"PGR1"
        + struct.pack("<III", len(metadata), len(nodes), len(edges))
        + metadata
        + struct.pack(f"<{len(positions)}f", *positions)
        + struct.pack(f"<{len(pairs)}I", *pairs)
    )


@router.get("/entities/graph.bin")
def graph_binary(
    request: Request, type: str | None = None, entity_id: str | None = None, depth: int = 1,
    include_transactions: bool = False, property_id: str | None = None,
):
    if not 0 <= depth <= 5:
        raise ValueError("Traversal depth must be between 0 and 5")
    return Response(
        binary_graph(explorer_graph(request, type=type, entity_id=entity_id, depth=depth,
                                    include_transactions=include_transactions, property_id=property_id)),
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


def event_batch(store, since):
    state = store.snapshot()
    events = state["events"]
    if since > state["version"] or (events and since < events[0]["version"] - 1):
        return "reset", {"version": state["version"], "reason": "Snapshot required"}
    return "delta", {
        "events": [e for e in events if e["version"] > since],
        "version": state["version"],
    }


async def stream_events(request, since=0, run_id=None):
    cursor = since
    heartbeat = 0
    while not await request.is_disconnected():
        kind, batch = event_batch(request.app.state.store, cursor)
        cursor = batch["version"]
        if run_id and kind == "delta":
            batch["events"] = [
                e
                for e in batch["events"]
                if e.get("payload", {}).get("run_id") == run_id
                or e.get("payload", {}).get("id") == run_id
                or e.get("payload", {}).get("session") == run_id
            ]
        if kind == "reset" or batch.get("events"):
            yield f"event: {kind}\nid: {cursor}\ndata: {json.dumps(batch)}\n\n"
        else:
            heartbeat += 1
            if heartbeat % 60 == 0:
                yield ": keep-alive\n\n"
        await asyncio.sleep(0.25)


@router.get("/entities/graph/stream")
async def graph_stream(request: Request, since: int = 0):
    cursor = request.headers.get("last-event-id", str(since))
    try:
        cursor = max(0, int(cursor))
    except ValueError:
        raise HTTPException(400, "Invalid event cursor") from None
    return StreamingResponse(
        stream_events(request, cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/entities/{entity_id}")
def entity(entity_id: str, request: Request):
    return request.app.state.graph.get_entity(entity_id)


@router.patch("/entities/{entity_id}")
def update_entity(entity_id: str, payload: EntityUpdate, request: Request):
    value = payload.model_dump(exclude_none=True)
    reason = value.pop("reason")
    return request.app.state.graph.update_entity(entity_id, value, reason=reason)


@router.post("/entities/{entity_id}/merge")
def merge_entity(entity_id: str, payload: Merge, request: Request):
    return request.app.state.graph.merge_entities(
        entity_id,
        payload.target_id,
        reason=payload.reason,
        version=payload.version,
        target_version=payload.target_version,
    )


@router.get("/entities/{entity_id}/graph")
def entity_graph(entity_id: str, request: Request, depth: int = 1):
    if not 0 <= depth <= 5:
        raise ValueError("Traversal depth must be between 0 and 5")
    return request.app.state.graph.graph(depth=depth, entity_id=entity_id)


@router.get("/documents")
def documents(request: Request):
    return {"items": request.app.state.graph.list_documents()}


@router.get("/documents/{document_id}")
def document(document_id: str, request: Request):
    return request.app.state.graph.get_document(document_id)


@router.get("/entity-types")
def entity_types(request: Request):
    return {"items": request.app.state.graph.entity_types()}


@router.post("/entity-types")
@router.patch("/entity-types")
def save_entity_type(payload: dict, request: Request):
    return request.app.state.graph.save_entity_type(payload)


@router.get("/edge-rules")
def rules(request: Request):
    return {"items": request.app.state.rules.list_rules()}


@router.post("/edge-rules")
def save_rule(payload: Rule, request: Request):
    return request.app.state.rules.save_rule(payload.model_dump(exclude_none=True))


@router.post("/edge-rules/compile")
def compile_rule(payload: Compile, request: Request):
    return request.app.state.rules.compile(payload.prompt)


@router.patch("/edge-rules/{rule_id}")
def edit_rule(rule_id: str, payload: Rule, request: Request):
    return request.app.state.rules.save_rule(
        {**payload.model_dump(exclude_none=True), "id": rule_id}
    )


@router.post("/edge-rules/{rule_id}/preview")
def preview_rule(rule_id: str, request: Request):
    return request.app.state.rules.preview(rule_id)


@router.post("/edge-rules/{rule_id}/recompute")
def recompute_rule(rule_id: str, request: Request):
    return request.app.state.rules.recompute(rule_id)


@router.post("/search")
def search(payload: Search, request: Request):
    return request.app.state.search.search(payload.model_dump())


@router.post("/ingest/upload", status_code=201)
def ingest(payload: Upload, request: Request):
    return request.app.state.ingestion.ingest(payload.model_dump())


@router.post("/ingest/sync")
def sync(request: Request):
    from propadmin_core import seed_demo

    seed_demo(request.app.state.store)
    return {"status": "complete", "message": "Synthetic demo sources are available"}


@router.get("/ingest/jobs")
def ingestion_jobs(request: Request):
    return {"items": list(request.app.state.store.snapshot()["jobs"].values())}


@router.get("/ingest/jobs/{job_id}")
def ingestion_job(job_id: str, request: Request):
    return request.app.state.store.snapshot()["jobs"][job_id]
