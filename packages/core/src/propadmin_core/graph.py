"""Validated canonical graph writes with concurrency, merge history and provenance."""

import copy
import math
import re

from .embeddings import EmbeddingService
from .graph_relationships import validate_relationship
from .registry import default_types, hard_keys, normalise, primary_types, validate_fields
from .store import ConflictError, identifier, now, publish
from .ticket_completion import COMPLETION_FIELDS, validate_completion


def reject_derived_fields(state, type_name, fields):
    schema = state["entity_types"].get(type_name, {}).get("fields", {})
    protected = {
        "property": {"tenant_balance_minor", "landlord_balance_minor", "deposit_held_minor"},
        "service_provider": {
            "jobs_completed",
            "avg_response_hours",
            "first_time_fix_rate",
            "avg_job_cost_minor",
            "rating",
        },
    }.get(type_name, set())
    if set(fields) & protected or any(schema.get(key, {}).get("read_only") for key in fields):
        raise ValueError("Derived fields are read-only")


def protect_ledger_edge(state, edge):
    if any(
        state["entities"].get(edge[key], {}).get("type") == "transaction"
        for key in ("source", "target")
    ):
        raise ValueError("Ledger relationships must be changed through the ledger")


def record_change(state, action, actor, reason, before, after):
    key = identifier("change")
    state["changes"][key] = {
        "id": key,
        "action": action,
        "actor": actor,
        "reason": reason,
        "entity_id": (after or before or {}).get("id"),
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(after),
        "created_at": now(),
    }
    action_id = identifier("action")
    state["actions"][action_id] = {
        "id": action_id,
        "kind": action,
        "actor": actor,
        "reason": reason,
        "change_id": key,
        "entity_id": (after or before or {}).get("id"),
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(after),
        "status": "completed",
        "created_at": now(),
        "reversible": not (
            action.startswith("ledger.") or (after or before or {}).get("type") == "transaction"
        ),
    }
    publish(state, action, {"id": (after or before or {}).get("id"), "change_id": key})
    return key


def assert_unique(state, entity, exclude=None):
    keys = hard_keys(state, entity)
    for other in state["entities"].values():
        if other["id"] == exclude or other.get("merged_into") or other["type"] != entity["type"]:
            continue
        shared = keys & hard_keys(state, other)
        if shared:
            raise ConflictError(
                f"Identity key already belongs to {other['id']}; resolve or merge first"
            )


def create_in_state(state, payload, actor="admin", reason="", embedder=None, *, ledger=False):
    type_name = payload.get("type", "")
    if type_name == "transaction" and not ledger:
        raise ValueError("Transactions must be recorded through the ledger")
    if not ledger:
        reject_derived_fields(state, type_name, payload.get("fields", {}))
    if not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError("Entity name is required")
    fields = validate_fields(state, type_name, payload.get("fields", {}), allow_read_only=ledger)
    validate_completion(type_name, fields)
    if type_name == "property":
        for key in ("tenant_balance_minor", "landlord_balance_minor", "deposit_held_minor"):
            fields.setdefault(key, 0)
    slug = re.sub(r"[^a-z0-9]+", "-", payload["name"].casefold()).strip("-")[:70]
    entity_id = payload.get("id") or f"{type_name}:{slug}"
    if not isinstance(entity_id, str) or not re.fullmatch(
        r"[a-z][a-z0-9_]*:[a-zA-Z0-9_-]+", entity_id
    ):
        raise ValueError("Entity id must be type:slug")
    if not entity_id.startswith(type_name + ":"):
        raise ValueError("Entity id must use its registered type prefix")
    if entity_id in state["entities"]:
        if payload.get("id"):
            raise ConflictError(f"{entity_id} already exists")
        entity_id = identifier(type_name)
    aliases = normalise(payload.get("aliases", []), {"type": "array<string>"}, "aliases")
    description = normalise(payload.get("description", ""), {"type": "text"}, "description")
    external_ids = payload.get("external_ids", {})
    if not isinstance(external_ids, dict) or any(
        not isinstance(v, str) for v in external_ids.values()
    ):
        raise ValueError("external_ids must map system names to string identifiers")
    stamp = now()
    entity = {
        "id": entity_id,
        "type": type_name,
        "name": payload["name"].strip(),
        "description": description,
        "aliases": aliases,
        "fields": fields,
        "external_ids": copy.deepcopy(external_ids),
        "version": 1,
        "created_at": stamp,
        "updated_at": stamp,
        "merged_into": None,
        "description_pinned": actor == "admin",
        "layout_x": float(payload.get("layout_x", 0)),
        "layout_y": float(payload.get("layout_y", 0)),
        "evidence": copy.deepcopy(payload.get("evidence", [])),
    }
    assert_unique(state, entity)
    state["entities"][entity_id] = entity
    (embedder or EmbeddingService()).entity(state, entity)
    record_change(state, "entity.created", actor, reason, None, entity)
    return entity


def update_in_state(state, entity_id, payload, actor="admin", reason="", embedder=None):
    current = state["entities"][entity_id]
    if current["type"] == "transaction":
        raise ValueError("Transactions are immutable; use a reversal or ledger status promotion")
    reject_derived_fields(state, current["type"], payload.get("fields", {}))
    if current.get("merged_into"):
        raise ConflictError(f"Entity merged into {current['merged_into']}")
    if payload.get("version") != current["version"]:
        raise ConflictError(f"Stale entity version; current version is {current['version']}")
    allowed = {
        "version",
        "name",
        "description",
        "aliases",
        "fields",
        "external_ids",
        "layout_x",
        "layout_y",
        "description_pinned",
        "evidence",
    }
    if set(payload) - allowed:
        raise ValueError("Unknown entity update fields")
    updated = copy.deepcopy(current)
    for key in (
        "name",
        "description",
        "aliases",
        "external_ids",
        "layout_x",
        "layout_y",
        "description_pinned",
    ):
        if key in payload:
            updated[key] = copy.deepcopy(payload[key])
    if not isinstance(updated["name"], str) or not updated["name"].strip():
        raise ValueError("Entity name is required")
    updated["description"] = normalise(updated["description"], {"type": "text"}, "description")
    updated["aliases"] = normalise(updated["aliases"], {"type": "array<string>"}, "aliases")
    if not isinstance(updated["external_ids"], dict) or any(
        not isinstance(v, str) for v in updated["external_ids"].values()
    ):
        raise ValueError("external_ids must map string identifiers")
    if type(updated["description_pinned"]) is not bool:
        raise ValueError("description_pinned must be boolean")
    for position in ("layout_x", "layout_y"):
        if (
            isinstance(updated[position], bool)
            or not isinstance(updated[position], (int, float))
            or not math.isfinite(updated[position])
        ):
            raise ValueError("Graph positions must be finite numbers")
    updated["fields"] = validate_fields(
        state,
        current["type"],
        {**current["fields"], **payload.get("fields", {})},
        allow_read_only=True,
    )
    validate_completion(current["type"], updated["fields"])
    if actor == "admin" and "description" in payload:
        updated["description_pinned"] = True
    if "evidence" in payload:
        updated["evidence"] = copy.deepcopy(payload["evidence"])
    updated.update(version=current["version"] + 1, updated_at=now())
    assert_unique(state, updated, exclude=entity_id)
    state["entities"][entity_id] = updated
    (embedder or EmbeddingService()).entity(state, updated)
    record_change(state, "entity.updated", actor, reason, current, updated)
    return updated


def add_edge(state, source, target, relation, *, rule=None, version=None, score=1.0, evidence=None):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", relation):
        raise ValueError("Relation must be a lowercase identifier")
    key = f"edge:{source}|{relation}|{target}|{rule or 'manual'}"
    edge = {
        "id": key,
        "source": source,
        "target": target,
        "relation": relation,
        "rule": rule,
        "rule_version": version,
        "score": score,
        "evidence": evidence or [],
        "computed_at": now(),
    }
    state["edges"][key] = edge
    return edge


class GraphService:
    def __init__(self, store):
        self.store = store
        self.embedder = EmbeddingService()

    def _propagate(self, state):
        from .rules import recompute_enabled

        recompute_enabled(state)

    def list_entities(self, type=None, q=None):
        entities = self.store.snapshot()["entities"].values()
        return sorted(
            [
                item
                for item in entities
                if not item.get("merged_into")
                and (not type or item["type"] == type)
                and (not q or q.casefold() in str(item).casefold())
            ],
            key=lambda x: x["name"],
        )

    def get_entity(self, id):
        def view(state):
            return {
                **state["entities"][id],
                "edges": [e for e in state["edges"].values() if id in (e["source"], e["target"])],
                "timeline": sorted(
                    [c for c in state["changes"].values() if c.get("entity_id") == id],
                    key=lambda c: c["created_at"],
                    reverse=True,
                ),
            }

        return self.store.read(view)

    def create_entity(self, payload, actor="admin", reason=""):
        def create(state):
            result = create_in_state(state, payload, actor, reason, self.embedder)
            self._propagate(state)
            return result

        return self.store.mutate(create)

    def update_entity(self, id, payload, actor="admin", reason=""):
        def update(state):
            result = update_in_state(state, id, payload, actor, reason, self.embedder)
            self._propagate(state)
            return result

        return self.store.mutate(update)

    def merge_entities(
        self, id, target_id, actor="admin", reason="", *, version=None, target_version=None
    ):
        if id == target_id:
            raise ValueError("Cannot merge an entity into itself")

        def merge(state):
            source, target = state["entities"][id], state["entities"][target_id]
            if source["type"] == "transaction" or target["type"] == "transaction":
                raise ValueError("Ledger transactions cannot be merged")
            if source["type"] == "property" and any(
                e["relation"] == "for"
                and e["target"] in (id, target_id)
                and state["entities"].get(e["source"], {}).get("type") == "transaction"
                for e in state["edges"].values()
            ):
                raise ValueError("Properties with ledger history cannot be merged")
            if version is not None and source["version"] != version:
                raise ConflictError("Source entity changed; reload before merging")
            if target_version is not None and target["version"] != target_version:
                raise ConflictError("Target entity changed; reload before merging")
            if source["type"] != target["type"]:
                raise ValueError("Merged entities must have the same type")
            if source.get("merged_into") or target.get("merged_into"):
                raise ConflictError("Cannot merge an already merged entity")
            before = copy.deepcopy(target)
            source_before = copy.deepcopy(source)
            # Target scalar values win; history preserves conflicting source values.
            for key, value in source["fields"].items():
                if key not in target["fields"]:
                    target["fields"][key] = copy.deepcopy(value)
                elif isinstance(value, list):
                    target["fields"][key] = list(
                        {repr(v): v for v in target["fields"][key] + value}.values()
                    )
            target["external_ids"] = {**source["external_ids"], **target["external_ids"]}
            validate_completion(target["type"], target["fields"])
            target["aliases"] = list(
                dict.fromkeys(target["aliases"] + source["aliases"] + [source["name"]])
            )
            target["evidence"] += source.get("evidence", [])
            target.update(version=target["version"] + 1, updated_at=now())
            source.update(merged_into=target_id, version=source["version"] + 1, updated_at=now())
            assert_unique(state, target, exclude=target_id)
            for edge in list(state["edges"].values()):
                if id in (edge["source"], edge["target"]):
                    del state["edges"][edge["id"]]
                    a = target_id if edge["source"] == id else edge["source"]
                    b = target_id if edge["target"] == id else edge["target"]
                    if a != b:
                        add_edge(
                            state,
                            a,
                            b,
                            edge["relation"],
                            rule=edge.get("rule"),
                            version=edge.get("rule_version"),
                            score=edge.get("score", 1),
                            evidence=edge.get("evidence"),
                        )
            for document in state["documents"].values():
                document["entities"] = list(
                    dict.fromkeys(
                        target_id if key == id else key for key in document.get("entities", [])
                    )
                )
                for mention in document.get("mentions", []):
                    if mention["entity_id"] == id:
                        mention["entity_id"] = target_id
            for fact in state["facts"].values():
                if fact.get("entity_id") == id:
                    fact["entity_id"] = target_id
            for resolution in state["resolutions"].values():
                if resolution.get("entity_id") == id:
                    resolution["entity_id"] = target_id
            self.embedder.entity(state, target)
            for key in [key for key, item in state["embeddings"].items() if item["owner"] == id]:
                del state["embeddings"][key]
            record_change(state, "entity.merged", actor, reason, before, target)
            record_change(state, "entity.redirected", actor, reason, source_before, source)
            publish(state, "entity.merged", {"source": id, "target": target_id})
            self._propagate(state)
            return target

        return self.store.mutate(merge)

    def link_entities(self, payload, actor="admin", reason=""):
        def link(state):
            source, target = payload["source"], payload["target"]
            for id in (source, target):
                if id not in state["entities"] or state["entities"][id].get("merged_into"):
                    raise KeyError(id)
            protect_ledger_edge(state, {"source": source, "target": target})
            attributes = validate_relationship(
                state, source, target, payload["relation"], payload.get("attributes")
            )
            edge = add_edge(
                state, source, target, payload["relation"], evidence=payload.get("evidence")
            )
            edge.update(attributes)
            record_change(state, "edge.created", actor, reason, None, edge)
            return edge

        return self.store.mutate(link)

    def unlink_entities(self, id, actor="admin", reason=""):
        def unlink(state):
            edge = state["edges"][id]
            protect_ledger_edge(state, edge)
            if edge.get("rule"):
                raise ValueError("Rule-generated edges must be changed through their rule")
            del state["edges"][id]
            record_change(state, "edge.deleted", actor, reason, edge, None)
            return {"id": id, "deleted": True}

        return self.store.mutate(unlink)

    def graph(self, depth=1, entity_id=None, type=None):
        if not isinstance(depth, int) or not 0 <= depth <= 5:
            raise ValueError("Graph depth must be between zero and five")
        state = self.store.snapshot()
        all_nodes = {
            key: value for key, value in state["entities"].items() if not value.get("merged_into")
        }
        if entity_id:
            if entity_id not in all_nodes:
                raise KeyError(entity_id)
            ids = {entity_id}
            for _ in range(depth):
                ids |= {
                    endpoint
                    for edge in state["edges"].values()
                    if edge["source"] in ids or edge["target"] in ids
                    for endpoint in (edge["source"], edge["target"])
                }
        else:
            ids = set(all_nodes)
        nodes = [
            node
            for key, node in all_nodes.items()
            if key in ids and (not type or node["type"] == type)
        ]
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge
            for edge in state["edges"].values()
            if edge["source"] in node_ids and edge["target"] in node_ids
        ]
        return {"nodes": nodes, "edges": edges, "version": state["version"]}

    def list_documents(self):
        return sorted(
            self.store.snapshot()["documents"].values(), key=lambda d: d["created_at"], reverse=True
        )

    def get_document(self, id):
        state = self.store.snapshot()
        document = state["documents"][id]
        document["chunks"] = [state["chunks"][key] for key in document.get("chunks", [])]
        document["facts"] = [state["facts"][key] for key in document.get("facts", [])]
        return document

    def entity_types(self):
        state = self.store.snapshot()
        primary = primary_types(state)
        return [{**t, "primary": key in primary} for key, t in state["entity_types"].items()]

    def save_entity_type(self, payload):
        def save(state):
            key = payload.get("id")
            if not key or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
                raise ValueError("Entity type id must be a lowercase identifier")
            fields = payload.get("fields", {})
            if not isinstance(fields, dict):
                raise ValueError("Entity fields must be a mapping")
            allowed = {
                "string",
                "text",
                "int",
                "float",
                "number",
                "decimal",
                "datetime",
                "date",
                "bool",
                "object",
            }
            for name, spec in fields.items():
                kind = spec.get("type", "")
                inner = kind
                if kind.startswith(("array<", "option<")) and kind.endswith(">"):
                    inner = kind[kind.index("<") + 1 : -1]
                if inner not in allowed or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    raise ValueError(f"Invalid field schema {name}")
                spec.setdefault("embed", "text" in kind)
                indexed_triplet = (key == "workflow_triplet"
                                   and spec == default_types()["workflow_triplet"]["fields"].get(name))
                if "text" in kind and not spec["embed"] and not indexed_triplet:
                    raise ValueError("Free-text fields must be embedded")
                spec.setdefault("required", False)
                spec.setdefault("unique_key", False)
            previous = state["entity_types"].get(key)
            if "primary" not in payload and previous and "primary" in previous:
                payload["primary"] = previous["primary"]
            if not isinstance(payload.get("primary", True), bool):
                raise ValueError("primary must be true or false")
            if key == "ticket":
                fixed = default_types()["ticket"]["fields"]
                if any(fields.get(name) != fixed[name] for name in COMPLETION_FIELDS):
                    raise ValueError("Ticket completion fields are fixed and must remain embedded text")
            if key in {"property", "transaction", "service_provider", "service_offering", "quote"}:
                fixed = default_types()[key]
                if fields != fixed["fields"] or payload.get("composite_keys", []) != fixed.get(
                    "composite_keys", []
                ):
                    raise ValueError(
                        "Addendum canonical schemas are fixed; change them through a migration"
                    )
            if previous and payload.get("version") != previous["version"]:
                raise ConflictError("Stale entity type version")
            result = {
                **payload,
                "fields": fields,
                "version": (previous or {}).get("version", 0) + 1,
            }
            state["entity_types"][key] = result
            for entity in state["entities"].values():
                if entity["type"] == key:
                    validate_fields(state, key, entity["fields"], allow_read_only=True)
                    self.embedder.entity(state, entity)
            publish(state, "entity_type.updated", {"id": key})
            return result

        return self.store.mutate(save)
