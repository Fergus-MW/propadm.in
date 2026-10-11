"""One embedding space per configured provider, with text-hash deduplication."""

import hashlib
import math
import os
import re

from .providers import VertexEmbeddings
from .store import now


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.casefold())


def local_vector(text, dimensions=256):
    vector = [0.0] * dimensions
    for word in tokens(text):
        digest = hashlib.sha256(word.encode()).digest()
        index = int.from_bytes(digest[:4], "little") % dimensions
        vector[index] += 1.0
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector] if length else vector


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError("Embedding dimensions differ; rebuild the index after changing providers")
    norm_a, norm_b = math.hypot(*a), math.hypot(*b)
    return math.sumprod(a, b) / (norm_a * norm_b) if norm_a and norm_b else 0.0


class EmbeddingService:
    def __init__(self):
        mode = os.getenv("EMBEDDING_PROVIDER", "local")
        if mode == "local":
            self.provider = None
            self.model = "local-deterministic-hash-v1"
        elif mode == "vertex":
            self.provider = VertexEmbeddings()
            self.model = f"vertex:{self.provider.model}:{self.provider.dimension}"
        else:
            raise ValueError(f"Unknown embedding provider {mode}")

    def vector(self, text, query=False):
        return self.provider.embed(text, query=query) if self.provider else local_vector(text)

    def upsert(self, state, owner, field, text):
        if not text or not isinstance(text, str):
            return
        key = embedding_key(owner, field, self.model)
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        # Keep a staged provider migration current when the source changes.
        # Metadata scans are read-only. Bypass lazy snapshot cloning so a small
        # graph write does not copy every stored vector; replace/delete by key.
        for old_key in [k for k, e in dict.items(state["embeddings"])
                        if e["owner"] == owner and e["field"] == field
                        and not e.get("index") and e["text_hash"] != text_hash]:
            del state["embeddings"][old_key]
        previous = state["embeddings"].get(key)
        if previous and previous["text_hash"] == text_hash and previous["model"] == self.model:
            return previous
        # Share vectors for identical text under the same provider.
        cached = next(
            (
                entry
                for entry in dict.values(state["embeddings"])
                if entry["text_hash"] == text_hash and entry["model"] == self.model
            ),
            None,
        )
        vector = cached["vector"] if cached else self.vector(text)
        entry = {
            "id": key,
            "owner": owner,
            "field": field,
            "text": text,
            "text_hash": text_hash,
            "model": self.model,
            "vector": vector,
            "updated_at": now(),
        }
        state["embeddings"][key] = entry
        return entry

    def entity(self, state, entity):
        owner = entity["id"]
        live_fields = {"description"} if entity.get("description") else set()
        self.upsert(state, owner, "description", entity.get("description", ""))
        registry = state["entity_types"][entity["type"]]["fields"]
        for name, value in entity["fields"].items():
            if not registry[name].get("embed"):
                continue
            values = value if isinstance(value, list) else [value]
            for index, item in enumerate(values):
                field = f"{name}.{index}" if isinstance(value, list) else name
                text = item.get("text", "") if isinstance(item, dict) else item
                if isinstance(text, str) and text:
                    live_fields.add(field)
                    self.upsert(state, owner, field, text)
        stale = [
            key
            for key, entry in dict.items(state["embeddings"])
            if entry["owner"] == owner and entry["field"] not in live_fields
            and not entry.get("index")
        ]
        for key in stale:
            del state["embeddings"][key]


def embedding_key(owner, field, model):
    return hashlib.sha256(f"{owner}\0{field}\0{model}".encode()).hexdigest()
