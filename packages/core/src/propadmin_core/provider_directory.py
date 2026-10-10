"""Provider recommendations, sourced prices and quotes, with no payment execution."""

import copy
import re
from datetime import date, datetime, timedelta

from .addendum_upgrade import refresh_property_edges
from .graph import add_edge, create_in_state, update_in_state
from .registry import hard_keys, normalise
from .registry_addendum import PROVIDER_STATUSES
from .store import ConflictError, now, publish


def _entity(state, entity_id, type_name):
    item = state["entities"][entity_id]
    if item["type"] != type_name or item.get("merged_into"):
        raise ValueError(f"Expected active {type_name}")
    return item


def _related(state, source, relation):
    return [
        state["entities"][edge["target"]]
        for edge in state["edges"].values()
        if edge["source"] == source
        and edge["relation"] == relation
        and edge["target"] in state["entities"]
    ]


def _warnings(fields, today):
    warnings = []
    for accreditation in fields.get("accreditations", []):
        expiry = accreditation.get("expires_on")
        if expiry and date.fromisoformat(expiry) < today:
            warnings.append(f"{accreditation['scheme']} accreditation expired {expiry}")
    expiry = fields.get("insurance_expires_on")
    if expiry and date.fromisoformat(expiry) < today:
        warnings.append(f"Public liability insurance expired {expiry}")
    return warnings


def _qualified(fields, trade, today):
    schemes = {"heating/gas": {"Gas Safe"}, "electrical": {"NICEIC", "NAPIT"}}.get(trade)
    if not schemes:
        return True
    return any(
        item.get("scheme") in schemes
        and item.get("expires_on")
        and date.fromisoformat(item["expires_on"]) >= today
        for item in fields.get("accreditations", [])
    )


def _offering(state, provider_id, today):
    rows = copy.deepcopy(_related(state, provider_id, "offers"))
    for item in rows:
        confirmed = item["fields"].get("last_confirmed_at")
        item["price_stale"] = not confirmed or date.fromisoformat(confirmed) < today - timedelta(
            days=183
        )
        item["evidence"] = [
            copy.deepcopy(state["chunks"][edge["target"]])
            for edge in state["edges"].values()
            if edge["source"] == item["id"]
            and edge["relation"] == "evidenced_by"
            and edge["target"] in state["chunks"]
        ] or item.get("evidence", [])
    return rows


def refresh_metrics(state):
    """Refresh observed provider metrics; unknown outcomes stay unknown, never invented."""
    for provider in state["entities"].values():
        if provider["type"] != "service_provider" or provider.get("merged_into"):
            continue
        tickets = [
            state["entities"][edge["source"]]
            for edge in state["edges"].values()
            if edge["relation"] == "assigned_to"
            and edge["target"] == provider["id"]
            and edge["source"] in state["entities"]
        ]
        closed = [
            item for item in tickets if item["fields"].get("status") in {"resolved", "closed"}
        ]
        response = []
        for ticket in tickets:
            fields = ticket["fields"]
            if fields.get("reported_at") and fields.get("first_visit_at"):
                start = datetime.fromisoformat(fields["reported_at"].replace("Z", "+00:00"))
                visit = datetime.fromisoformat(fields["first_visit_at"].replace("Z", "+00:00"))
                hours = (visit - start).total_seconds() / 3600
                if hours >= 0:
                    response.append(hours)
        paid_ids = {
            edge["source"]
            for edge in state["edges"].values()
            if edge["relation"] == "paid_to" and edge["target"] == provider["id"]
        }
        spend = [
            item["fields"]["amount_minor"]
            for item in state["entities"].values()
            if item["id"] in paid_ids
            and item["type"] == "transaction"
            and item["fields"].get("category") == "expense"
            and item["fields"].get("kind") == "payment"
            and item["fields"].get("status") in {"cleared", "reconciled"}
            and not any(
                edge["relation"] == "reverses"
                and (edge["source"] == item["id"] or edge["target"] == item["id"])
                for edge in state["edges"].values()
            )
        ]
        observed = [item for item in closed if item["fields"].get("visits_count")]
        feedback = [
            item["fields"]["tenant_feedback_rating"]
            for item in closed
            if item["fields"].get("tenant_feedback_rating") is not None
        ]
        metrics = {
            "jobs_completed": len(closed),
            "avg_response_hours": sum(response) / len(response) if response else None,
            "avg_job_cost_minor": round(sum(spend) / len(spend)) if spend else None,
            "first_time_fix_rate": sum(item["fields"]["visits_count"] == 1 for item in observed)
            / len(observed)
            if observed
            else None,
            "rating": sum(feedback) / len(feedback) if feedback else None,
        }
        fields = provider["fields"]
        if any(fields.get(key) != value for key, value in metrics.items()):
            fields.update(metrics)
            provider.update(version=provider["version"] + 1, updated_at=now())
            publish(state, "provider.metrics", {"id": provider["id"], "fields": metrics})


class ProviderService:
    def __init__(self, store):
        self.store = store

    def find_providers(
        self,
        trade=None,
        property_id=None,
        postcode=None,
        urgency=None,
        service=None,
        status=None,
        q=None,
        min_rating=None,
    ):
        state = self.store.snapshot()
        today = date.today()
        if property_id:
            postcode = _entity(state, property_id, "property")["fields"].get("postcode")
        district = None
        if postcode:
            compact = re.sub(r"\s+", "", postcode.upper())
            district = (
                compact[:-3]
                if re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}", compact)
                else compact
            )
        result = []
        for provider in state["entities"].values():
            if provider["type"] != "service_provider" or provider.get("merged_into"):
                continue
            fields = provider["fields"]
            provider_status = fields.get("status", "trial")
            if not status and provider_status in {"suspended", "do_not_use"}:
                continue
            if status and provider_status != status:
                continue
            if q and q.casefold() not in str(provider).casefold():
                continue
            if trade and trade not in fields.get("trades", []):
                continue
            if district and district not in fields.get("postcode_districts", []):
                continue
            if urgency == "emergency" and not fields.get("emergency_callout"):
                continue
            if min_rating is not None and (fields.get("rating") or 0) < min_rating:
                continue
            if not _qualified(fields, trade, today):
                continue
            offerings = _offering(state, provider["id"], today)
            if service:
                offerings = [
                    item for item in offerings if service.casefold() in str(item).casefold()
                ]
                if not offerings:
                    continue
            costs = [
                item["fields"].get("price_minor")
                for item in offerings
                if item["fields"].get("price_minor") is not None
            ]
            item = copy.deepcopy(provider)
            item.update(
                offerings=offerings,
                warnings=_warnings(fields, today),
                matching_price_minor=min(costs) if costs else None,
            )
            item["ranking"] = {
                "preferred": provider_status == "preferred"
                or bool(
                    property_id
                    and any(
                        edge["source"] == provider["id"]
                        and edge["target"] == property_id
                        and edge["relation"] == "preferred_for"
                        for edge in state["edges"].values()
                    )
                ),
                "response_hours": fields.get("avg_response_hours")
                or fields.get("typical_response_hours"),
                "rating": fields.get("rating"),
                "first_time_fix_rate": fields.get("first_time_fix_rate"),
                "matching_price_minor": item["matching_price_minor"],
            }
            result.append(item)

        def rank(item):
            values = item["ranking"]
            response = (
                values["response_hours"] if values["response_hours"] is not None else float("inf")
            )
            quality = (-float(values["rating"] or 0), -float(values["first_time_fix_rate"] or 0))
            price = (
                values["matching_price_minor"]
                if values["matching_price_minor"] is not None
                else float("inf")
            )
            return (
                (response, *quality, price, item["name"])
                if urgency == "emergency"
                else (not values["preferred"], *quality, price, response, item["name"])
            )

        return sorted(result, key=rank)

    def get_provider(self, id):
        state = self.store.snapshot()
        provider = copy.deepcopy(_entity(state, id, "service_provider"))
        edges = [edge for edge in state["edges"].values() if id in (edge["source"], edge["target"])]
        ticket_ids = {edge["source"] for edge in edges if edge["relation"] == "assigned_to"}
        tx_ids = {edge["source"] for edge in edges if edge["relation"] == "paid_to"}
        provider.update(
            offerings=_offering(state, id, date.today()),
            contacts=_related(state, id, "contact"),
            registered_companies=_related(state, id, "registered_as"),
            warnings=_warnings(provider["fields"], date.today()),
            tickets=[state["entities"][key] for key in ticket_ids],
            quotes=[
                item
                for item in state["entities"].values()
                if item["type"] == "quote"
                and any(
                    edge["source"] == item["id"] and edge["relation"] == "from" for edge in edges
                )
            ],
            spend_minor=self._spend(state, tx_ids),
            edges=edges,
        )
        return provider

    @staticmethod
    def _spend(state, tx_ids):
        from .ledger import effect

        return -sum(
            effect(state, item)["landlord_balance_minor"]
            for item in state["entities"].values()
            if item["id"] in tx_ids
            and item["type"] == "transaction"
            and item["fields"].get("category") == "expense"
            and item["fields"].get("kind") == "payment"
        )

    def _upsert(self, state, type_name, payload, id, actor):
        if "fields" not in payload:
            if set(payload) & {
                "version",
                "description",
                "aliases",
                "external_ids",
                "evidence",
                "type",
            }:
                payload = {**payload, "fields": {}}
            else:
                payload = {"fields": payload}
        payload = copy.deepcopy(payload)
        fields = payload["fields"]
        schema = state["entity_types"][type_name]["fields"]
        unknown = set(fields) - set(schema)
        if unknown:
            raise ValueError(f"Unknown {type_name} fields: {', '.join(sorted(unknown))}")
        fields = {key: normalise(value, schema[key], key) for key, value in fields.items()}
        payload["fields"] = fields
        if not id:
            keys = hard_keys(
                state,
                {
                    "type": type_name,
                    "fields": fields,
                    "external_ids": payload.get("external_ids", {}),
                },
            )
            matches = [
                item
                for item in state["entities"].values()
                if item["type"] == type_name
                and not item.get("merged_into")
                and keys & hard_keys(state, item)
            ]
            if len(matches) > 1:
                raise ConflictError("Provider identity matches multiple records; resolve first")
            if matches:
                current = matches[0]
                if all(
                    current["fields"].get(key) == value for key, value in fields.items()
                ) and all(
                    current.get(key) == value
                    for key, value in payload.items()
                    if key not in {"fields", "version"}
                ):
                    return current
                id = current["id"]
        if id:
            _entity(state, id, type_name)
            if "version" not in payload:
                raise ConflictError(
                    "Existing provider or offering updates require its current version"
                )
            return update_in_state(state, id, payload, actor, "Provider directory update")
        name = (
            payload.get("name")
            or fields.get("trading_name")
            or fields.get("name")
            or fields.get("ref")
        )
        return create_in_state(
            state, {**payload, "type": type_name, "name": name}, actor, "Provider directory create"
        )

    def upsert_provider(self, payload, id=None, actor="admin"):
        def write(state):
            item = self._upsert(state, "service_provider", payload, id, actor)
            refresh_property_edges(state)
            return item

        return self.store.mutate(write)

    def upsert_offering(self, payload, provider_id, id=None, actor="admin"):
        def write(state):
            _entity(state, provider_id, "service_provider")
            if id:
                owners = [
                    edge["source"]
                    for edge in state["edges"].values()
                    if edge["relation"] == "offers" and edge["target"] == id
                ]
                if owners and owners != [provider_id]:
                    raise ConflictError("Offering belongs to another provider")
            item = self._upsert(state, "service_offering", payload, id, actor)
            add_edge(state, provider_id, item["id"], "offers")
            publish(state, "provider.offering", {"provider_id": provider_id, "id": item["id"]})
            return item

        return self.store.mutate(write)

    def record_quote(self, provider_id, ticket_id, payload, actor="admin"):
        def write(state):
            _entity(state, provider_id, "service_provider")
            _entity(state, ticket_id, "ticket")
            fields = dict(payload.get("fields", payload))
            fields.setdefault("status", "received")
            item = create_in_state(
                state,
                {
                    "type": "quote",
                    "name": fields.get("ref") or f"Quote {provider_id} {ticket_id}",
                    "fields": fields,
                },
                actor,
                "Record provider quote",
            )
            add_edge(state, item["id"], provider_id, "from")
            add_edge(state, item["id"], ticket_id, "for")
            publish(state, "quote.recorded", {"id": item["id"]})
            return item

        return self.store.mutate(write)

    def accept_quote(self, quote_id, actor="admin"):
        from .ledger import record_in_state

        def write(state):
            quote = _entity(state, quote_id, "quote")
            fields = quote["fields"]
            if fields.get("status") == "accepted":
                return quote
            if fields.get("status") != "received":
                raise ValueError("Only received quotes can be accepted")
            if (
                fields.get("valid_until")
                and date.fromisoformat(fields["valid_until"]) < date.today()
            ):
                raise ValueError("Quote has expired")
            providers = _related(state, quote_id, "from")
            tickets = _related(state, quote_id, "for")
            if len(providers) != 1 or len(tickets) != 1:
                raise ValueError("Quote requires exactly one provider and ticket")
            provider, ticket = providers[0], tickets[0]
            if provider["fields"].get("status") in {"suspended", "do_not_use"}:
                raise ValueError("Provider is unavailable for assignment")
            trade = {"heating": "heating/gas"}.get(
                ticket["fields"].get("category"), ticket["fields"].get("category")
            )
            if not _qualified(provider["fields"], trade, date.today()):
                raise ValueError("Provider lacks current trade accreditation")
            properties = _related(state, ticket["id"], "at")
            if len(properties) != 1:
                raise ValueError("Ticket must link to exactly one property before accepting quote")
            tx = record_in_state(
                state,
                {
                    "property_id": properties[0]["id"],
                    "fields": {
                        "kind": "charge",
                        "category": "expense",
                        "amount_minor": fields["amount_minor"],
                        "effective_date": date.today().isoformat(),
                        "status": "expected",
                        "counterparty_name": provider["name"],
                        "description": fields.get("scope", ""),
                        "external_ref": fields.get("ref"),
                    },
                    "paid_to": provider["id"],
                    "ticket_id": ticket["id"],
                },
                actor=actor,
            )
            add_edge(state, quote_id, tx["id"], "accepted_as")
            for key, edge in list(state["edges"].items()):
                if edge["source"] == ticket["id"] and edge["relation"] == "assigned_to":
                    del state["edges"][key]
            add_edge(state, ticket["id"], provider["id"], "assigned_to")
            quote = update_in_state(
                state,
                quote_id,
                {"version": quote["version"], "fields": {"status": "accepted"}},
                actor,
                "Accept quote",
            )
            publish(
                state,
                "quote.accepted",
                {"id": quote_id, "transaction_id": tx["id"], "ticket_id": ticket["id"]},
            )
            return quote

        return self.store.mutate(write)

    def set_provider_status(self, id, status, reason, actor="admin"):
        if status not in PROVIDER_STATUSES or not isinstance(reason, str) or not reason.strip():
            raise ValueError("Valid status and non-empty reason are required")

        def write(state):
            current = _entity(state, id, "service_provider")
            return update_in_state(
                state,
                id,
                {
                    "version": current["version"],
                    "fields": {"status": status, "status_reason": reason},
                },
                actor,
                "Provider status decision",
            )

        return self.store.mutate(write)
