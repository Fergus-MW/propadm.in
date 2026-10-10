"""Versioned rules, safe predicates, previews, and atomic edge replacement."""

import ast
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from .embeddings import cosine, local_vector
from .graph import add_edge
from .providers import ClaudeProvider, ProviderNotConfigured
from .store import ConflictError, identifier, now, publish

KINDS = {"field_match", "field_overlap", "expression", "co_occurrence", "similarity", "llm_judge"}


def field_value(entity, path):
    if path == "email_domain":
        return [email.rsplit("@", 1)[-1] for email in entity["fields"].get("emails", [])]
    value = entity
    pieces = path.split(".")
    if pieces[0] not in entity:
        value = entity["fields"]
    for piece in pieces:
        if not isinstance(value, dict):
            return None
        value = value.get(piece)
    return value


def values(value):
    if value is None or value == "":
        return set()
    return {str(item).casefold() for item in (value if isinstance(value, list) else [value])}


def predicate(expression, source, target):
    """A bounded comparison/boolean subset, never eval or arbitrary SurrealQL."""
    expression = expression.replace("$a.", "a.").replace("$b.", "b.")
    expression = re.sub(r"\bAND\b", "and", expression)
    expression = re.sub(r"\bOR\b", "or", expression)
    expression = re.sub(r"\bNOT\b", "not", expression)
    expression = re.sub(r"(?<![!<>=])=(?!=)", "==", expression)
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid rule expression syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("Expression is too complex")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(
            node.value, (str, int, float, bool, type(None))
        ):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            return [visit(item) for item in node.elts]
        if isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if not isinstance(current, ast.Name) or current.id not in ("a", "b"):
                raise ValueError("Expressions only reference $a and $b fields")
            if any(part.startswith("_") for part in parts):
                raise ValueError("Private attributes are forbidden")
            return field_value(source if current.id == "a" else target, ".".join(parts))
        if isinstance(node, ast.BoolOp):
            items = [bool(visit(item)) for item in node.values]
            return all(items) if isinstance(node.op, ast.And) else any(items)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not visit(node.operand)
        if isinstance(node, ast.Compare):
            left = visit(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = visit(comparator)
                if isinstance(op, ast.Eq):
                    match = left == right
                elif isinstance(op, ast.NotEq):
                    match = left != right
                elif isinstance(op, ast.In):
                    match = left in right if right is not None else False
                elif isinstance(op, ast.NotIn):
                    match = left not in right if right is not None else True
                elif left is None or right is None:
                    match = False
                elif isinstance(op, ast.Gt):
                    match = left > right
                elif isinstance(op, ast.GtE):
                    match = left >= right
                elif isinstance(op, ast.Lt):
                    match = left < right
                elif isinstance(op, ast.LtE):
                    match = left <= right
                else:
                    raise ValueError("Unsupported expression comparison")
                if not match:
                    return False
                left = right
            return True
        raise ValueError("Expressions permit only field comparisons and boolean operators")

    return bool(visit(tree))


def entity_vector(state, entity, field="description"):
    entry = next(
        (
            embedding
            for embedding in state["embeddings"].values()
            if embedding["owner"] == entity["id"] and embedding["field"] == field
        ),
        None,
    )
    return entry["vector"] if entry else local_vector(str(field_value(entity, field) or ""))


def pair_documents(state, source_id, target_id, window_days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    results = []
    for document in state["documents"].values():
        if datetime.fromisoformat(document["created_at"]) < cutoff:
            continue
        mentioned = {mention["entity_id"] for mention in document.get("mentions", [])}
        if source_id in mentioned and target_id in mentioned:
            results.append(document["id"])
    return results


def validate_rule(state, payload):
    if payload.get("kind") not in KINDS:
        raise ValueError(f"Rule kind must be one of {sorted(KINDS)}")
    for field in ("source_type", "target_type"):
        if payload.get(field) not in state["entity_types"]:
            raise ValueError(f"Unknown {field}")
    if "transaction" in (payload["source_type"], payload["target_type"]):
        raise ValueError("Ledger relationships cannot be created or replaced by edge rules")
    relation = payload.get("relation", "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", relation):
        raise ValueError("Relation must be a lowercase identifier")
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("Rule params must be an object")
    kind = payload["kind"]
    if kind in ("field_match", "field_overlap"):
        for side in ("source", "target"):
            path = params.get(f"{side}_field")
            if not isinstance(path, str):
                raise ValueError(f"{side}_field is required")
            registry = state["entity_types"][payload[f"{side}_type"]]["fields"]
            if path.removeprefix("fields.") not in registry and path not in (
                "name",
                "description",
                "email_domain",
            ):
                raise ValueError(f"Unknown {side} field {path}")
    if kind == "expression":
        expression = params.get("expression", "")
        if not expression:
            raise ValueError("Expression is required")
        # Validate against empty fields: missing values are safe comparisons.
        predicate(expression, {"fields": {}}, {"fields": {}})
    for key, default, lower, upper in [
        ("threshold", 0.85, 0, 1),
        ("top_k", 5, 1, 100),
        ("min_documents", 3, 1, 1000),
        ("window_days", 90, 1, 3650),
    ]:
        value = params.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not lower <= value <= upper
        ):
            raise ValueError(f"Invalid {key}")
        if key != "threshold" and not isinstance(value, int):
            raise ValueError(f"{key} must be an integer")
    if "enabled" in payload and type(payload["enabled"]) is not bool:
        raise ValueError("enabled must be boolean")
    return copy.deepcopy(payload)


def matches(state, rule):
    params, kind = rule.get("params", {}), rule["kind"]
    candidates = [entity for entity in state["entities"].values() if not entity.get("merged_into")]
    sources = [entity for entity in candidates if entity["type"] == rule["source_type"]]
    targets = [entity for entity in candidates if entity["type"] == rule["target_type"]]
    provider = ClaudeProvider() if kind == "llm_judge" else None
    results = []
    for source in sources:
        source_results = []
        for target in targets:
            if source["id"] == target["id"]:
                continue
            if (
                rule["source_type"] == rule["target_type"]
                and source["id"] > target["id"]
                and params.get("symmetric", True)
            ):
                continue
            evidence, score, matched = [], 1.0, False
            if kind in ("field_match", "field_overlap"):
                a = values(field_value(source, params["source_field"]))
                b = values(field_value(target, params["target_field"]))
                overlap = sorted(a & b)
                matched = bool(overlap)
                evidence = [
                    {
                        "source_field": params["source_field"],
                        "target_field": params["target_field"],
                        "matched_values": overlap,
                    }
                ]
            elif kind == "expression":
                matched = predicate(params["expression"], source, target)
                evidence = [{"expression": params["expression"]}]
            elif kind == "co_occurrence":
                documents = pair_documents(
                    state, source["id"], target["id"], int(params.get("window_days", 90))
                )
                matched = len(documents) >= params.get("min_documents", 3)
                score = len(documents)
                evidence = [{"document_id": key} for key in documents]
            elif kind == "similarity":
                score = cosine(
                    entity_vector(state, source, params.get("field", "description")),
                    entity_vector(state, target, params.get("field", "description")),
                )
                matched = score >= params.get("threshold", 0.85)
                evidence = [{"field": params.get("field", "description"), "cosine": score}]
            elif kind == "llm_judge":
                documents = pair_documents(
                    state, source["id"], target["id"], int(params.get("window_days", 90))
                )
                if len(documents) < params.get("min_documents", 1):
                    continue
                fingerprint = hashlib.sha256(
                    json.dumps(
                        [rule["id"], rule["version"], source, target, documents], sort_keys=True
                    ).encode()
                ).hexdigest()
                judgement = state["rule_judgements"].get(fingerprint)
                if judgement is None:
                    judgement = provider.json(
                        "Judge this relation. Return {matches: boolean, score: number, reason: string}.",
                        {
                            "rule": rule,
                            "source": source,
                            "target": target,
                            "documents": [state["documents"][key]["text"] for key in documents],
                        },
                    )
                    if type(judgement.get("matches")) is not bool or not isinstance(
                        judgement.get("score"), (int, float)
                    ):
                        raise ValueError("Claude returned an invalid relation judgement")
                    state["rule_judgements"][fingerprint] = judgement
                score = judgement["score"]
                matched = judgement["matches"] and score >= params.get("threshold", 0.85)
                evidence = [{"document_id": key} for key in documents] + [
                    {"judgement": judgement["reason"]}
                ]
            if matched:
                source_results.append(
                    {
                        "source": source["id"],
                        "target": target["id"],
                        "score": score,
                        "evidence": evidence,
                    }
                )
        if kind == "similarity":
            source_results.sort(key=lambda item: -item["score"])
            source_results = source_results[: int(params.get("top_k", 5))]
        results.extend(source_results)
    return results


def apply_rule(state, rule):
    pairs = matches(state, rule) if rule.get("enabled", True) else []
    previous = [key for key, edge in state["edges"].items() if edge.get("rule") == rule["id"]]
    for key in previous:
        del state["edges"][key]
    for pair in pairs:
        add_edge(
            state,
            pair["source"],
            pair["target"],
            rule["relation"],
            rule=rule["id"],
            version=rule["version"],
            score=pair["score"],
            evidence=pair["evidence"],
        )
    rule.update(last_recomputed_at=now(), edge_count=len(pairs), last_error=None)
    publish(
        state,
        "rule.recomputed",
        {"id": rule["id"], "count": len(pairs), "version": rule["version"]},
    )
    return {"count": len(pairs), "version": rule["version"]}


def safe_apply(state, rule):
    try:
        return apply_rule(state, rule)
    except ProviderNotConfigured as exc:
        rule["last_error"] = str(exc)
        # Never silently retain stale LLM edges after a source change.
        for key in [key for key, edge in state["edges"].items() if edge.get("rule") == rule["id"]]:
            del state["edges"][key]
        publish(state, "rule.error", {"id": rule["id"], "error": str(exc)})
        return {"count": 0, "version": rule["version"], "error": str(exc)}


def recompute_enabled(state, entity_type=None):
    """All enabled rules, or only those touching entity_type (incremental)."""
    results = {}
    for rule in state["rules"].values():
        if rule.get("enabled", True) and entity_type in (
            None,
            rule["source_type"],
            rule["target_type"],
        ):
            results[rule["id"]] = safe_apply(state, rule)
    from .addendum_upgrade import refresh_property_edges
    from .provider_directory import refresh_metrics

    refresh_property_edges(state)
    refresh_metrics(state)
    return results


class RuleService:
    def __init__(self, store):
        self.store = store

    def list_rules(self):
        return list(self.store.snapshot()["rules"].values())

    def save_rule(self, payload):
        def save(state):
            key = payload.get("id") or identifier("rule")
            previous = state["rules"].get(key)
            if previous and payload.get("version") != previous["version"]:
                raise ConflictError("Stale rule version")
            rule = validate_rule(state, {**(previous or {}), **payload})
            rule.update(
                id=key,
                version=(previous or {}).get("version", 0) + 1,
                enabled=rule.get("enabled", True),
                created_at=(previous or {}).get("created_at", now()),
                updated_at=now(),
                params=rule.get("params", {}),
            )
            rule["compiled_query"] = compiled_query(rule)
            state["rules"][key] = rule
            publish(state, "rule.updated", {"id": key, "version": rule["version"]})
            # Explicit saves of an enabled unconfigured judge reject atomically.
            apply_rule(state, rule)
            return rule

        return self.store.mutate(save)

    def preview(self, id):
        state = self.store.snapshot()
        pairs = matches(state, state["rules"][id])
        return {"count": len(pairs), "samples": pairs[:20]}

    def recompute(self, id):
        return self.store.mutate(lambda state: apply_rule(state, state["rules"][id]))

    def compile(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Rule prompt is required")
        lowered = prompt.casefold()
        if (
            "domain" in lowered
            and ("people" in lowered or "person" in lowered)
            and "compan" in lowered
        ):
            spec = {
                "name": "Company email domain",
                "kind": "field_match",
                "source_type": "person",
                "target_type": "company",
                "relation": "works_at",
                "params": {"source_field": "email_domain", "target_field": "domains"},
                "compiler": "local-template-v1",
            }
        elif "ticket" in lowered and "tag" in lowered:
            spec = {
                "name": "Shared ticket tags",
                "kind": "field_overlap",
                "source_type": "ticket",
                "target_type": "ticket",
                "relation": "related_ticket",
                "params": {"source_field": "tags", "target_field": "tags"},
                "compiler": "local-template-v1",
            }
        else:
            provider = ClaudeProvider()
            spec = provider.json(
                "Compile an edge rule; return name, kind, source_type, target_type, relation, params. "
                f"Allowed kinds: {sorted(KINDS)}. Expression subset uses field comparisons and AND/OR.",
                {"prompt": prompt, "entity_types": self.store.snapshot()["entity_types"]},
            )
            spec["compiler"] = provider.model
        spec.update(prompt=prompt, enabled=False)
        validate_rule(self.store.snapshot(), spec)
        spec["compiled_query"] = compiled_query(spec)
        return spec


def compiled_query(rule):
    kind, params = rule["kind"], rule.get("params", {})
    if kind == "expression":
        return params["expression"]
    if kind in ("field_match", "field_overlap"):
        operator = "=" if kind == "field_match" else "INTERSECTS"
        return f"$a.{params['source_field']} {operator} $b.{params['target_field']}"
    return f"-- {kind}: executed by the {kind} rule evaluator"
