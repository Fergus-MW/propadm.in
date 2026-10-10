"""Hybrid BM25 + vector ranking, reciprocal rank fusion, and graph citations."""

import math
import time
from collections import Counter, defaultdict

from .embeddings import EmbeddingService, cosine, tokens


def citations_for(state, entity_id):
    result = []
    entity = state["entities"][entity_id]
    seen = set()
    for evidence in entity.get("evidence", []):
        key = (evidence.get("document_id"), evidence.get("chunk_id"))
        if key in seen:
            continue
        document = state["documents"].get(key[0])
        chunk = state["chunks"].get(key[1])
        if document and chunk:
            seen.add(key)
            result.append(
                {
                    **evidence,
                    "title": document["title"],
                    "filename": document["filename"],
                    "quote": evidence.get("span", {}).get("text", chunk["text"])[:600],
                }
            )
    return result


class SearchService:
    def __init__(self, store):
        self.store = store
        self.embedder = EmbeddingService()

    def search(self, payload):
        start = time.perf_counter()
        query = payload.get("query", "")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query is required")
        if len(query) > 2000:
            raise ValueError("Search query exceeds 2,000 characters")
        limit = payload.get("limit", 20)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Search limit must be between one and 100")
        state = self.store.snapshot()
        types = payload.get("types") or []
        if not isinstance(types, list) or any(
            type_name not in state["entity_types"] for type_name in types
        ):
            raise ValueError("Search types must be registered type names")
        entities = {
            key: entity
            for key, entity in state["entities"].items()
            if not entity.get("merged_into") and (not types or entity["type"] in types)
        }
        texts = {}
        for key, entity in entities.items():
            texts[key] = " ".join(
                [entity["name"], entity["description"], *entity["aliases"], str(entity["fields"])]
            )
        source_texts = defaultdict(str)
        # Source ranking is separate so broad co-mentions do not swamp direct fields.
        for document in state["documents"].values():
            for mention in document.get("mentions", []):
                key = mention["entity_id"]
                if key in texts:
                    chunk = state["chunks"].get(mention["chunk_id"])
                    if chunk:
                        source_texts[key] += " " + chunk["text"]
        words = {key: tokens(text) for key, text in texts.items()}
        frequencies = {key: Counter(items) for key, items in words.items()}
        n = len(words)
        average = sum(map(len, words.values())) / max(n, 1)
        document_frequencies = Counter(word for items in words.values() for word in set(items))
        lexical = {}
        query_words = tokens(query)
        for key, counts in frequencies.items():
            score = 0.0
            for word in query_words:
                frequency = counts[word]
                df = document_frequencies[word]
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                score += (
                    idf
                    * frequency
                    * 2.2
                    / (frequency + 1.2 * (0.25 + 0.75 * len(words[key]) / max(average, 1)))
                )
            if score > 0:
                lexical[key] = score
        source_lexical = {}
        for key, text in source_texts.items():
            counts = Counter(tokens(text))
            score = sum(math.log1p(counts[word]) for word in query_words)
            if score:
                source_lexical[key] = score
        query_vector = self.embedder.vector(query, query=True)
        owner_entities = defaultdict(set)
        for key in entities:
            owner_entities[key].add(key)
        for document in state["documents"].values():
            for mention in document.get("mentions", []):
                if mention["entity_id"] in entities:
                    owner_entities[mention["chunk_id"]].add(mention["entity_id"])
        for fact in state["facts"].values():
            if fact.get("entity_id") in entities:
                owner_entities[fact["id"]].add(fact["entity_id"])
        semantic = {}
        for embedding in state["embeddings"].values():
            ids = owner_entities.get(embedding["owner"], set())
            if not ids or embedding["model"] != self.embedder.model:
                continue
            score = cosine(query_vector, embedding["vector"])
            if embedding["owner"] not in entities:
                score *= 0.65
            if score > 0:
                for key in ids:
                    semantic[key] = max(semantic.get(key, 0), score)
        ranked = defaultdict(float)
        methods = defaultdict(list)
        for method, scores, weight in [
            ("bm25", lexical, 1.0),
            ("vector", semantic, 1.0),
            ("source_text", source_lexical, 0.35),
        ]:
            ordered = sorted(scores, key=lambda key: (-scores[key], key))
            for position, key in enumerate(ordered, 1):
                ranked[key] += weight / (60 + position)
                methods[key].append(method)
        if payload.get("expand", True):
            direct = dict(ranked)
            seeds = set(sorted(direct, key=lambda key: -direct[key])[: min(limit, 10)])
            for edge in state["edges"].values():
                source, target = edge["source"], edge["target"]
                if source in seeds and target in entities:
                    if target not in direct:
                        ranked[target] = max(ranked[target], direct[source] * 0.15)
                    methods[target].append("graph")
                if target in seeds and source in entities:
                    if source not in direct:
                        ranked[source] = max(ranked[source], direct[target] * 0.15)
                    methods[source].append("graph")
        results = []
        for key in sorted(ranked, key=lambda key: (-ranked[key], key))[:limit]:
            entity = entities[key]
            results.append(
                {
                    "id": key,
                    "type": entity["type"],
                    "name": entity["name"],
                    "description": entity["description"],
                    "score": round(ranked[key], 8),
                    "citations": citations_for(state, key),
                    "matched_by": list(dict.fromkeys(methods[key])),
                }
            )
        return {
            "results": results,
            "query": query,
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "embedding_provider": self.embedder.model,
            "ranking": "bm25+vector+graph-rrf",
        }
