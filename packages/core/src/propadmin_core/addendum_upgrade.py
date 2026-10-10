"""Idempotent local registry and graph backfill preserving custom entity types."""

import copy
import re
from datetime import datetime, timezone

from .embeddings import EmbeddingService
from .graph import add_edge, create_in_state
from .registry import default_types, hard_keys
from .registry_addendum import TRADES
from .store import now, publish

TRADE_MAP = {
    "heating": "heating/gas",
    "appliances": "appliance repair",
    "pests": "pest control",
    "access/security": "locksmith",
    "structural": "general building",
    "other": "handyman",
}


def refresh_property_edges(state):
    """Rebuild only our derived rules; manually chosen coverage stays intact."""
    rules = {"addendum:same_building", "addendum:covers", "addendum:recurring_issue"}
    state["edges"] = {
        key: edge for key, edge in state["edges"].items() if edge.get("rule") not in rules
    }
    properties = [
        item
        for item in state["entities"].values()
        if item["type"] == "property" and not item.get("merged_into")
    ]
    providers = [
        item
        for item in state["entities"].values()
        if item["type"] == "service_provider" and not item.get("merged_into")
    ]
    for source in properties:
        fields = source["fields"]
        building = fields.get("building_name", "")
        if building:
            for target in properties:
                other = target["fields"]
                if (
                    source["id"] != target["id"]
                    and building.casefold() == (other.get("building_name") or "").casefold()
                    and fields.get("postcode") == other.get("postcode")
                ):
                    add_edge(
                        state,
                        source["id"],
                        target["id"],
                        "same_building",
                        rule="addendum:same_building",
                        version=1,
                    )
        district = fields.get("postcode", "").split(" ")[0]
        for provider in providers:
            if district and district in provider["fields"].get("postcode_districts", []):
                add_edge(
                    state, provider["id"], source["id"], "covers", rule="addendum:covers", version=1
                )

    ticket_properties = {
        edge["source"]: edge["target"]
        for edge in state["edges"].values()
        if edge["relation"] == "at"
    }
    tickets = [
        item
        for item in state["entities"].values()
        if item["type"] == "ticket" and not item.get("merged_into")
    ]
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "there",
        "their",
        "from",
        "have",
        "has",
        "repair",
        "issue",
        "reported",
    }

    def observed(ticket):
        value = ticket["fields"].get("reported_at")
        if not value:
            return None
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.replace(tzinfo=timezone.utc) if not timestamp.tzinfo else timestamp

    def words(ticket):
        text = ticket.get("description", "") + " " + ticket["fields"].get("title", "")
        return {
            word
            for word in re.findall(r"[a-z0-9]+", text.casefold())
            if len(word) > 2 and word not in stopwords
        }

    for source in tickets:
        recent, prop = observed(source), ticket_properties.get(source["id"])
        category = source["fields"].get("category")
        if not recent or not prop or not category:
            continue
        for target in tickets:
            previous = observed(target)
            if (
                not previous
                or source["id"] == target["id"]
                or not 0 < (recent - previous).total_seconds() <= 90 * 86400
            ):
                continue
            if (
                ticket_properties.get(target["id"]) != prop
                or target["fields"].get("category") != category
            ):
                continue
            tags = {tag.casefold() for tag in source["fields"].get("tags", [])} & {
                tag.casefold() for tag in target["fields"].get("tags", [])
            }
            tags = {tag for tag in tags if len(tag) > 2 and tag not in stopwords}
            first, second = words(source), words(target)
            shared = first & second
            similarity = len(shared) / max(len(first | second), 1)
            if tags or (len(shared) >= 3 and similarity >= 0.35):
                add_edge(
                    state,
                    source["id"],
                    target["id"],
                    "recurring_issue",
                    rule="addendum:recurring_issue",
                    version=1,
                )


def upgrade_addendum(state):
    """Upgrade legacy local snapshots without replacing administrator custom types."""
    definitions = default_types()
    changed = False
    for name, definition in definitions.items():
        if name not in state["entity_types"]:
            state["entity_types"][name] = copy.deepcopy(definition)
            changed = True
        elif name in {"property", "transaction", "service_provider", "service_offering", "quote"}:
            existing = state["entity_types"][name]
            if existing.get("fields") != definition["fields"] or existing.get(
                "composite_keys", []
            ) != definition.get("composite_keys", []):
                state["entity_types"][name] = {
                    **copy.deepcopy(existing),
                    **copy.deepcopy(definition),
                    "version": existing.get("version", 0) + 1,
                }
                changed = True
    ticket_schema = state["entity_types"]["ticket"]["fields"]
    for name in ("first_visit_at", "visits_count", "tenant_feedback_rating"):
        if name not in ticket_schema:
            ticket_schema[name] = copy.deepcopy(definitions["ticket"]["fields"][name])
            changed = True
    if "location" in ticket_schema:
        ticket_schema.pop("location")
        ticket_schema.setdefault(
            "location_detail", definitions["ticket"]["fields"]["location_detail"]
        )
        changed = True
    embedder = None
    entities = list(state["entities"].values())
    properties = [item for item in entities if item["type"] == "property"]
    provider_by_company = {
        edge["target"]: edge["source"]
        for edge in state["edges"].values()
        if edge["relation"] == "registered_as" and edge["source"].startswith("service_provider:")
    }
    for entity in entities:
        if entity["type"] == "ticket" and "location" in entity["fields"]:
            location = entity["fields"].pop("location")
            entity["fields"].setdefault("location_detail", location)
            matches = [
                prop
                for prop in properties
                if location
                and location.casefold()
                in {
                    prop["fields"].get("address_text", "").casefold(),
                    prop["fields"].get("address_line1", "").casefold(),
                }
            ]
            if len(matches) == 1:
                add_edge(state, entity["id"], matches[0]["id"], "at")
            embedder = embedder or EmbeddingService()
            embedder.entity(state, entity)
            entity.update(version=entity["version"] + 1, updated_at=now())
            changed = True
        if entity["type"] != "company" or entity["fields"].get("type") != "contractor":
            continue
        if entity["id"] in provider_by_company:
            continue
        fields = entity["fields"]
        embedder = embedder or EmbeddingService()
        mapped = [TRADE_MAP.get(trade, trade) for trade in fields.get("trades", [])]
        unknown_trades = [trade for trade in mapped if trade not in TRADES]
        notes = list(fields.get("notes", []))
        if unknown_trades:
            notes.append("Unmapped legacy trades requiring review: " + ", ".join(unknown_trades))
        provider_payload = {
            "type": "service_provider",
            "name": entity["name"],
            "description": entity.get("description", ""),
            "fields": {
                "ref": "SP-" + entity["id"].split(":", 1)[1].upper(),
                "trading_name": entity["name"],
                "legal_name": entity["name"],
                "trades": [trade for trade in mapped if trade in TRADES],
                "emails": fields.get("emails", []),
                "phone_main": next(iter(fields.get("phones", [])), None),
                "address": fields.get("address", ""),
                "service_area": fields.get("coverage_area", ""),
                "status": "trial",
                "status_reason": "Migrated contractor; accreditation and coverage require checking",
                "notes": notes,
                "postcode_districts": [],
                "accreditations": [],
                "emergency_callout": False,
            },
        }
        keys = hard_keys(state, provider_payload)
        matches = [
            item
            for item in state["entities"].values()
            if item["type"] == "service_provider"
            and not item.get("merged_into")
            and keys & hard_keys(state, item)
        ]
        if len(matches) > 1:
            # Ambiguous companies remain intact for explicit administrator resolution.
            continue
        provider = (
            matches[0]
            if matches
            else create_in_state(
                state, provider_payload, "migration", "Addendum A contractor backfill", embedder
            )
        )
        add_edge(state, provider["id"], entity["id"], "registered_as")
        provider_by_company[entity["id"]] = provider["id"]
        changed = True
    for edge in list(state["edges"].values()):
        if edge["relation"] == "assigned_to" and edge["target"] in provider_by_company:
            add_edge(
                state,
                edge["source"],
                provider_by_company[edge["target"]],
                "assigned_to",
                evidence=edge.get("evidence"),
            )
            del state["edges"][edge["id"]]
            changed = True
    refresh_property_edges(state)
    if changed:
        publish(state, "registry.upgraded", {"addendum": "A"})
    return changed
