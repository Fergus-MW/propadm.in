"""Resumable semantic index migration through the authenticated graph gateway.

Build vectors outside CAS writes, preserving the old provider until cutover.
Workflow triplet vectors use a separate index and are never migrated here.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from fastapi import APIRouter, Depends, Request
from propadmin_core.embeddings import embedding_key
from propadmin_core.providers import VertexEmbeddings
from propadmin_core.store import now, publish
from pydantic import BaseModel, Field

from .auth import require_admin

router = APIRouter(prefix="/v1/embeddings", dependencies=[Depends(require_admin)])


class Batch(BaseModel):
    limit: int = Field(default=32, ge=1, le=64)


def pending(state, model):
    sources = {}
    entries = state["embeddings"]
    # Read metadata without cloning every vector in a lazy store snapshot.
    # Callers only replace entries; they never edit these cached values in place.
    for entry in dict.values(entries):
        if entry.get("index"):
            continue
        subject = (entry["owner"], entry["field"])
        if subject not in sources or entry["updated_at"] > sources[subject]["updated_at"]:
            sources[subject] = entry
    todo = []
    for (owner, field), entry in sources.items():
        target = dict.get(entries, embedding_key(owner, field, model))
        if not target or target["text_hash"] != entry["text_hash"] or target["model"] != model:
            todo.append(entry)
    return sources, todo


@lru_cache(maxsize=1)
def target_provider():
    provider = VertexEmbeddings()
    return provider, f"vertex:{provider.model}:{provider.dimension}"


@router.get("/status")
def status(request: Request):
    _, model = target_provider()
    sources, todo = pending(request.app.state.store.snapshot(), model)
    return {"target_model": model, "total": len(sources), "remaining": len(todo),
            "complete": not todo, "active_model": request.app.state.search.embedder.model}


@router.post("/reindex")
def reindex(payload: Batch, request: Request):
    provider, model = target_provider()
    store = request.app.state.store
    _, todo = pending(store.snapshot(), model)
    selected = todo[:payload.limit]
    texts = list(dict.fromkeys(e["text"] for e in selected))
    with ThreadPoolExecutor(max_workers=8) as pool:
        vectors = dict(zip(texts, pool.map(provider.embed, texts), strict=True))

    # /rpc caps request bodies at 4 MiB. Leave room for the double-encoded row
    # metadata, query and event; do not send a transaction the server will reject.
    bounded, size = [], 0
    for entry in selected:
        candidate = {**entry, "vector": vectors[entry["text"]], "model": model}
        row_size = len(json.dumps(json.dumps(candidate)).encode())
        if size + row_size > 2_000_000:
            if not bounded:
                raise ValueError("Embedding source exceeds the migration transaction size limit")
            break
        bounded.append(entry)
        size += row_size
    selected = bounded

    def write(state):
        current, _ = pending(state, model)
        written = 0
        for entry in selected:
            subject = (entry["owner"], entry["field"])
            if current.get(subject, {}).get("text_hash") != entry["text_hash"]:
                continue  # source changed or was deleted while embedding
            key = embedding_key(*subject, model)
            state["embeddings"][key] = {**entry, "id": key, "model": model,
                                       "vector": vectors[entry["text"]], "updated_at": now()}
            written += 1
        _, remaining = pending(state, model)
        publish(state, "embeddings.reindexed", {"model": model, "written": written,
                                               "remaining": len(remaining)})
        return {"target_model": model, "written": written, "remaining": len(remaining),
                "complete": not remaining}

    return store.mutate(write)
