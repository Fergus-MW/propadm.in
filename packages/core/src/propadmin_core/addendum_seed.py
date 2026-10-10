"""Synthetic properties, bank sources, prices and versioned financial workflows."""

from pathlib import Path

from .addendum_upgrade import upgrade_addendum
from .embeddings import EmbeddingService
from .graph import add_edge, create_in_state, update_in_state
from .ingestion import IngestionService
from .ledger import LedgerService
from .provider_directory import ProviderService
from .store import now, publish

PROPERTY = "property:hoxton-3b"
SKILLS = {
    "rent-arrears": "Rent arrears",
    "reconcile-ledger": "Reconcile ledger",
    "contractor-invoice": "Check contractor invoice",
    "landlord-statement": "Landlord statement",
    "choose-provider": "Choose provider",
    "provider-research": "Research providers",
}


def seed_skills(state):
    root = Path(__file__).resolve().parents[4] / "skills"
    for slug, title in SKILLS.items():
        content = (root / slug / "SKILL.md").read_text()
        key, version_id = f"skill:{slug}", f"skill_version:{slug}-v1"
        if key in state["skills"]:
            continue
        create_in_state(state, {"id": key, "type": "skill", "name": title,
                               "description": title, "fields": {"slug": slug, "source": "custom", "status": "active"}},
                        "seed", "Addendum A workflow")
        create_in_state(state, {"id": version_id, "type": "skill_version", "name": title + " v1",
                               "fields": {"version": 1, "content": content, "change_summary": "Addendum A initial workflow",
                                          "created_by": "seed", "published_at": now()}}, "seed", "Addendum A workflow")
        add_edge(state, key, version_id, "current")
        add_edge(state, key, version_id, "has_version")
        state["skills"][key] = {"id": key, "slug": slug, "name": title, "description": title,
                                "source": "custom", "status": "active", "current_version": 1,
                                "content": content, "versions": [{"version": 1, "content": content,
                                    "created_by": "seed", "change_summary": "Initial workflow", "created_at": now()}]}
    key = "skill:workflow-review"
    if key in state["skills"]:
        skill = state["skills"][key]
        content = (root / "workflow-review/SKILL.md").read_text()
        if skill["content"] != content:
            version = skill["current_version"] + 1
            version_id = f"skill_version:workflow-review-v{version}"
            create_in_state(state, {"id": version_id, "type": "skill_version", "name": f"Workflow review v{version}",
                                    "fields": {"version": version, "content": content,
                                               "change_summary": "Flag ledger corrections caused by workflows",
                                               "created_by": "seed", "published_at": now()}}, "seed", "Addendum A criterion")
            for edge in list(state["edges"].values()):
                if edge["source"] == key and edge["relation"] == "current":
                    del state["edges"][edge["id"]]
            add_edge(state, key, version_id, "current")
            add_edge(state, key, version_id, "has_version")
            skill.update(content=content, current_version=version)
            skill["versions"].append({"version": version, "content": content, "created_by": "seed",
                                     "change_summary": "Addendum A ledger correction criterion", "created_at": now()})


def seed_addendum(store):
    store.mutate(upgrade_addendum)
    store.mutate(seed_skills)
    if store.snapshot().get("addendum_seeded"):
        return
    ingestion = IngestionService(store)
    common = {"property_type": "flat", "bedrooms": 2, "bathrooms": 1,
              "city": "London", "building_name": "Hoxton House", "postcode": "N1 6SH",
              "rent_amount_minor": 95000, "rent_frequency": "monthly", "rent_due_day": 1,
              "management_fee_pct": 8, "tenancy_start": "2026-10-01", "features": "Combi boiler",
              "access_notes": "Call tenant before visiting", "compliance_notes": "Synthetic compliance fixture"}
    records = [
        {"id": PROPERTY, "type": "property", "name": "Flat 3B, 24 Hoxton Street",
         "description": "Aisha Khan's lettable flat in Hoxton House",
         "fields": {**common, "ref": "HOXT-3B", "address_line1": "Flat 3B, 24 Hoxton Street",
                    "address_text": "Flat 3B, 24 Hoxton Street, London N1 6SH", "unit_label": "Flat 3B",
                    "status": "let", "deposit_amount_minor": 150000}},
        {"id": "property:hoxton-4a", "type": "property", "name": "Flat 4A, 24 Hoxton Street",
         "description": "Vacant flat in Hoxton House",
         "fields": {**common, "ref": "HOXT-4A", "address_line1": "Flat 4A, 24 Hoxton Street",
                    "address_text": "Flat 4A, 24 Hoxton Street, London N1 6SH", "unit_label": "Flat 4A", "status": "vacant"}},
        {"id": "person:james-landlord", "type": "person", "name": "James Whitmore",
         "description": "Landlord of the synthetic Hoxton flats",
         "fields": {"roles": ["landlord"], "emails": ["james.whitmore@example.net"]}},
    ]
    ingestion.ingest({"filename": "properties-and-tenancies.json", "mime": "application/json",
                      "origin": "synthetic_env", "records": records})
    store.mutate(upgrade_addendum)

    def relationships(state):
        for key in (PROPERTY, "property:hoxton-4a"):
            owner = add_edge(state, "person:james-landlord", key, "owns")
            owner["share_pct"] = 100
            add_edge(state, "company:ember-property", key, "manages")
        tenancy = add_edge(state, "person:aisha-khan", PROPERTY, "tenant_of")
        tenancy.update({"from": "2026-10-01", "to": None, "is_lead_tenant": True})
        for ticket in ("ticket:prop-1042", "ticket:prop-1036", "ticket:prop-1051"):
            add_edge(state, ticket, PROPERTY, "at")
        resolved = state["entities"]["ticket:prop-1036"]
        update_in_state(state, resolved["id"], {"version": resolved["version"], "fields": {
            "first_visit_at": "2026-09-23T12:00:00+00:00", "visits_count": 1, "tenant_feedback_rating": 4}},
                        "seed", "Synthetic observed job outcome")
        publish(state, "property.seeded", {"id": PROPERTY})

    store.mutate(relationships)
    providers = ProviderService(store)
    moss = next(item for item in store.snapshot()["entities"].values()
                if item["type"] == "service_provider" and item["name"] == "Moss Plumbing & Heating")
    providers.upsert_provider({"version": moss["version"], "fields": {
        "status": "preferred", "status_reason": "Verified synthetic trade fixture",
        "postcode_districts": ["N1", "E1", "E2"], "emergency_callout": True,
        "typical_response_hours": 4, "booking_method": "email",
        "booking_instructions": "Email Daniel Moss; request a confirmed attendance time",
        "insurance_expires_on": "2027-12-31", "insurance_public_liability_minor": 200000000,
        "accreditations": [{"scheme": "Gas Safe", "number": "SYN-123456", "expires_on": "2027-12-31"}],
    }}, id=moss["id"])
    offer = {"type": "service_offering", "name": "Annual boiler service",
             "provider_id": moss["id"], "fields": {"name": "Annual boiler service", "trade": "heating/gas",
             "pricing_model": "fixed", "price_minor": 8500, "vat_included": True,
             "description": "Inspect and service a domestic combi boiler; repairs excluded",
             "price_source": "email", "valid_from": "2026-10-10", "last_confirmed_at": "2026-10-10"}}
    ingestion.ingest({"filename": "moss-services.txt", "origin": "synthetic_env",
                      "text": "Moss Plumbing & Heating offers an Annual boiler service for £85, VAT included. Confirmed 10 October 2026.",
                      "records": [offer]})
    ledger = LedgerService(store)
    ledger.generate_rent_due("2026-10-10")
    bank = """date,amount,reference,counterparty,description,category,property_ref,provider_id,ticket_id
2026-10-02,950.00,HOXT-3B-RENT-OCT,Aisha Khan,HOXT-3B October rent,rent_received,HOXT-3B,,
2026-10-01,1500.00,HOXT-3B-DEPOSIT,Aisha Khan,HOXT-3B tenancy deposit,deposit_received,HOXT-3B,,
2026-10-04,-95.00,SYN-INV-095,Moss Plumbing & Heating,HOXT-3B sink repair,expense,HOXT-3B,PROVIDER_ID,ticket:prop-1036
2026-10-05,125.00,UNKNOWN-125,Unknown sender,Unrecognised client receipt,rent_received,,,
""".replace("PROVIDER_ID", moss["id"])
    invoice = """Invoice: SYN-INV-095
Date: 2026-10-03
Total: £95.00
Provider: Moss Plumbing & Heating
Provider id: PROVIDER_ID
Property: HOXT-3B
Ticket: ticket:prop-1036
Description: Replace kitchen sink waste trap
""".replace("PROVIDER_ID", moss["id"])
    ingestion.ingest({"filename": "sink-repair-invoice.txt", "source_type": "invoice", "origin": "synthetic_env", "text": invoice})
    ingestion.ingest({"filename": "client-bank-october.csv", "mime": "text/csv", "source_type": "bank_statement",
                      "origin": "synthetic_env", "text": bank})

    def finish(state):
        from .layout import apply_layout
        from .rules import recompute_enabled

        recompute_enabled(state)
        embedder = EmbeddingService()
        for item in state["entities"].values():
            if item["type"] == "property":
                embedder.entity(state, item)
        state["addendum_seeded"] = True
        apply_layout(state)
        publish(state, "addendum.seeded", {"addendum": "A"})

    store.mutate(finish)
