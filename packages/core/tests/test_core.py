"""Small scenario suite covering persistence and the graph's important invariants."""

import concurrent.futures
import copy

import pytest
from propadmin_core import (
    ConflictError,
    GraphService,
    IngestionService,
    RuleService,
    SearchService,
    Store,
    publish,
    seed_demo,
)
from propadmin_core.providers import ProviderNotConfigured
from propadmin_core.rules import predicate


def person(graph, name="Jane Doe", **fields):
    return graph.create_entity(
        {
            "type": "person",
            "name": name,
            "description": "Tenant needing heating repair",
            "fields": fields,
        }
    )


def test_persistent_transactions_concurrent_writes_and_rollback(tmp_path):
    path = tmp_path / "state.json"
    stores = [Store(path), Store(path)]

    def increment(index):
        def mutation(state):
            state["counter"] = state.get("counter", 0) + 1
            publish(state, "counter", {"value": state["counter"]})

        stores[index % 2].mutate(mutation)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(increment, range(30)))
    snapshot = Store(path).snapshot()
    assert snapshot["counter"] == 30
    assert snapshot["version"] == 30

    def failed(state):
        state["counter"] = 999
        raise ValueError("abort")

    with pytest.raises(ValueError):
        stores[0].mutate(failed)
    assert stores[1].snapshot()["counter"] == 30
    snapshot["counter"] = -1
    assert stores[0].snapshot()["counter"] == 30


def test_registry_validation_concurrency_and_embedding_dedupe():
    store, graph = Store(), None
    graph = GraphService(store)
    jane = person(
        graph,
        emails=["JANE@example.org"],
        phones=["07700 900111"],
        notes=["Heating needs attention"],
    )
    assert jane["fields"]["emails"] == ["jane@example.org"]
    assert jane["fields"]["phones"] == ["+447700900111"]
    with pytest.raises(ConflictError):
        person(graph, name="J. Doe", emails=["jane@example.org"])
    with pytest.raises(ValueError):
        graph.update_entity(jane["id"], {"version": 1, "fields": {"secret": "untyped"}})
    before = store.snapshot()["embeddings"]
    updated = graph.update_entity(jane["id"], {"version": 1, "name": "Jane A. Doe"})
    assert updated["version"] == 2
    assert store.snapshot()["embeddings"] == before
    with pytest.raises(ConflictError):
        graph.update_entity(jane["id"], {"version": 1, "description": "stale"})
    with pytest.raises(ValueError):
        person(graph, roles=["invalid-role"])
    with pytest.raises(ValueError):
        graph.save_entity_type(
            {"id": "building", "fields": {"notes": {"type": "text", "embed": False}}}
        )
    graph.save_entity_type(
        {"id": "building", "fields": {"notes": {"type": "text"}, "units": {"type": "int"}}}
    )
    with pytest.raises(ValueError):
        graph.create_entity({"type": "building", "name": "Block A", "fields": {"units": "ten"}})


def test_hard_key_resolution_provenance_idempotency_and_reextraction():
    store = Store()
    graph = GraphService(store)
    jane = person(graph, emails=["jane@example.org"], notes=["Pinned admin note"])
    text = "J. Doe emailed jane@example.org: the boiler has no hot water."
    ingestion = IngestionService(store)
    payload = {
        "filename": "report.md",
        "text": text,
        "records": [
            {
                "type": "person",
                "name": "J. Doe",
                "description": "This must not replace the pinned admin description",
                "fields": {"emails": ["JANE@example.org"], "availability": "After 17:00"},
                "mentions": [{"start": 0, "end": 6, "text": "J. Doe", "confidence": 0.97}],
            }
        ],
    }
    first = ingestion.ingest(payload)
    assert first["status"] == "completed"
    assert first["entities"] == [jane["id"]]
    assert ingestion.ingest(payload)["deduplicated"]
    entity = graph.get_entity(jane["id"])
    assert entity["description"] == jane["description"]
    assert entity["fields"]["availability"] == "After 17:00"
    assert "J. Doe" in entity["aliases"]
    assert all(
        e["span"]["text"] == text[e["span"]["start"] : e["span"]["end"]] for e in entity["evidence"]
    )
    ingestion.ingest({**payload, "extractor_version": "offline-v2"})
    entity = graph.get_entity(jane["id"])
    assert all(e["extractor_version"] == "offline-v2" for e in entity["evidence"])
    assert len(store.snapshot()["documents"]) == 1
    assert len(store.snapshot()["entities"]) == 1
    resolutions = list(store.snapshot()["resolutions"].values())
    assert any(decision["method"] == "hard_key" for decision in resolutions)
    bad = {
        **payload,
        "text": text + " bad",
        "records": [
            {
                **payload["records"][0],
                "mentions": [{"start": 999, "end": 1000, "text": "x", "confidence": 1}],
            }
        ],
    }
    with pytest.raises(ValueError):
        ingestion.ingest(bad)
    assert any(job["status"] == "failed" for job in store.snapshot()["jobs"].values())
    assert len(store.snapshot()["documents"]) == 1


def test_merge_repoints_edges_and_preserves_audit():
    store = Store()
    graph = GraphService(store)
    a = person(graph, name="J. Doe", emails=["j.doe@example.org"])
    b = person(graph, name="Jane Doe", emails=["jane@example.org"])
    company = graph.create_entity(
        {"type": "company", "name": "Estate Management", "fields": {"type": "managing agent"}}
    )
    graph.link_entities({"source": a["id"], "target": company["id"], "relation": "works_at"})
    IngestionService(store).ingest({"text": "J. Doe at Estate Management", "filename": "a.md"})
    merged = graph.merge_entities(a["id"], b["id"], reason="Confirmed by CRM")
    assert merged["version"] == 2
    assert set(merged["fields"]["emails"]) == {"j.doe@example.org", "jane@example.org"}
    assert graph.get_entity(a["id"])["merged_into"] == b["id"]
    assert not any(
        a["id"] in (edge["source"], edge["target"]) for edge in store.snapshot()["edges"].values()
    )
    assert any(
        change["reason"] == "Confirmed by CRM" for change in store.snapshot()["changes"].values()
    )
    assert len(graph.list_entities(type="person")) == 1
    assert len(graph.graph(entity_id=b["id"], depth=1)["nodes"]) == 2


def test_rules_preview_versions_incremental_recompute_and_manual_protection():
    store = Store()
    graph, rules = GraphService(store), RuleService(store)
    a = person(graph, emails=["jane@estate.example"])
    b = graph.create_entity(
        {"type": "company", "name": "Estate", "fields": {"domains": ["estate.example"]}}
    )
    manual = graph.link_entities({"source": a["id"], "target": b["id"], "relation": "works_at"})
    spec = {
        "name": "Employer",
        "kind": "field_match",
        "source_type": "person",
        "target_type": "company",
        "relation": "works_at",
        "params": {"source_field": "email_domain", "target_field": "domains"},
    }
    rule = rules.save_rule(spec)
    assert rules.preview(rule["id"])["count"] == 1
    generated = next(edge for edge in store.snapshot()["edges"].values() if edge.get("rule"))
    with pytest.raises(ValueError):
        graph.unlink_entities(generated["id"])
    rules.save_rule({**rule, "enabled": False})
    assert manual["id"] in store.snapshot()["edges"]
    assert not any(edge.get("rule") for edge in store.snapshot()["edges"].values())
    with pytest.raises(ConflictError):
        rules.save_rule({**rule, "name": "Stale rename"})
    expression = {
        **spec,
        "kind": "expression",
        "relation": "linked",
        "params": {"expression": '$a.name = "Jane Doe" AND $b.name = "Estate"'},
    }
    expr_rule = rules.save_rule(expression)
    assert rules.preview(expr_rule["id"])["count"] == 1
    with pytest.raises(ValueError):
        predicate('__import__("os").system("id")', a, b)
    with pytest.raises(ProviderNotConfigured):
        rules.save_rule({**spec, "kind": "llm_judge", "params": {}})
    graph.update_entity(a["id"], {"version": a["version"], "name": "Jane Smith"})
    assert rules.preview(expr_rule["id"])["count"] == 0
    assert (
        rules.compile("link people to the company whose domain matches their email")["compiler"]
        == "local-template-v1"
    )


def test_cooccurrence_overlap_and_similarity_rules():
    store = Store()
    graph, rules = GraphService(store), RuleService(store)
    a = graph.create_entity(
        {
            "type": "ticket",
            "name": "Ticket A",
            "description": "boiler broken no hot water",
            "fields": {"tags": ["heating", "urgent"]},
        }
    )
    b = graph.create_entity(
        {
            "type": "ticket",
            "name": "Ticket B",
            "description": "boiler broken no hot water",
            "fields": {"tags": ["heating"]},
        }
    )
    for index in range(3):
        IngestionService(store).ingest(
            {"filename": f"evidence-{index}.md", "text": f"Ticket A and Ticket B update {index}"}
        )
    base = {
        "source_type": "ticket",
        "target_type": "ticket",
        "relation": "related",
        "name": "Related",
    }
    overlap = rules.save_rule(
        {
            **base,
            "kind": "field_overlap",
            "params": {"source_field": "tags", "target_field": "tags"},
        }
    )
    cooccurrence = rules.save_rule(
        {**base, "kind": "co_occurrence", "params": {"min_documents": 3, "window_days": 90}}
    )
    similarity = rules.save_rule(
        {**base, "kind": "similarity", "params": {"threshold": 0.99, "top_k": 5}}
    )
    assert rules.preview(overlap["id"])["count"] == 1
    assert rules.preview(cooccurrence["id"])["samples"][0]["score"] == 3
    assert rules.preview(similarity["id"])["count"] == 1
    assert a["id"] != b["id"]


def test_seed_and_hybrid_search_have_real_citations_and_all_primary_types():
    store = Store()
    first = seed_demo(store)
    snapshot = copy.deepcopy(store.snapshot())
    second = seed_demo(store)
    assert first == second
    assert set(snapshot["documents"]) == set(store.snapshot()["documents"])
    assert {entity["type"] for entity in snapshot["entities"].values()} >= {
        "person",
        "company",
        "ticket",
        "email",
        "call", "property", "transaction", "service_provider", "service_offering",
    }
    result = SearchService(store).search(
        {"query": "boiler no hot water", "types": ["ticket"], "expand": True}
    )
    assert result["results"][0]["id"] == "ticket:prop-1042"
    assert result["results"][0]["citations"]
    assert result["embedding_provider"].startswith("local-deterministic")
    assert result["elapsed_ms"] < 500
    assert {skill["slug"] for skill in snapshot["skills"].values()} >= {
        "triage-maintenance-ticket",
        "workflow-review", "rent-arrears", "reconcile-ledger", "contractor-invoice",
        "landlord-statement", "choose-provider", "provider-research",
    }
    from propadmin_core.ledger import LedgerService

    ledger = LedgerService(store)
    balances = ledger.get_balances("property:hoxton-3b")
    assert balances["tenant_balance_minor"] == 0
    assert balances["landlord_balance_minor"] == 77900
    assert balances["deposit_held_minor"] == 150000
    assert len(ledger.unallocated()) == 1
    assert ledger.unallocated()[0]["payload"]["fields"]["amount_minor"] == 12500
    transactions = [entity for entity in snapshot["entities"].values() if entity["type"] == "transaction"]
    assert {tx["id"] for tx in transactions} == {
        entity["id"] for entity in store.snapshot()["entities"].values() if entity["type"] == "transaction"
    }
    assert all(tx["evidence"] for tx in transactions)
    assert all("location" not in e["fields"] for e in snapshot["entities"].values() if e["type"] == "ticket")
    for slug in ("rent-arrears", "reconcile-ledger", "contractor-invoice", "landlord-statement",
                 "choose-provider", "provider-research"):
        version = f"skill_version:{slug}-v1"
        assert snapshot["entities"][version]["fields"]["version"] == 1
        assert any(edge["source"] == f"skill:{slug}" and edge["target"] == version
                   and edge["relation"] == "current" for edge in snapshot["edges"].values())
    email = next(entity for entity in snapshot["entities"].values() if entity["type"] == "email")
    assert any(
        edge["relation"] == "sent_by" and edge["source"] == email["id"]
        for edge in snapshot["edges"].values()
    )
    with pytest.raises(ValueError):
        SearchService(store).search({"query": ""})


def test_every_free_text_field_and_transcript_turn_embedded():
    store = Store()
    seed_demo(store)
    call = next(
        entity for entity in store.snapshot()["entities"].values() if entity["type"] == "call"
    )
    embeddings = [
        entry for entry in store.snapshot()["embeddings"].values() if entry["owner"] == call["id"]
    ]
    fields = {entry["field"] for entry in embeddings}
    assert fields >= {
        "description",
        "objective",
        "transcript_text",
        "transcript.0",
        "transcript.1",
        "summary",
        "outcome",
        "action_items.0",
    }


def test_primary_types_configure_what_ingestion_extracts():
    store = Store()
    graph, ingestion = GraphService(store), IngestionService(store)
    types = {t["id"]: t for t in graph.entity_types()}
    assert types["person"]["primary"] and not types["skill"]["primary"]
    graph.save_entity_type({**types["company"], "primary": False})
    company = {t["id"]: t for t in graph.entity_types()}["company"]
    assert company["primary"] is False and company["version"] == 2
    graph.save_entity_type({k: v for k, v in company.items() if k != "primary"})
    assert {t["id"]: t for t in graph.entity_types()}["company"]["primary"] is False
    with pytest.raises(ValueError):
        graph.save_entity_type({**company, "version": 3, "primary": "no"})

    text = "Jane Roe from Acme Ltd reported a leak."
    job = ingestion.ingest({"filename": "note.md", "text": text, "records": [
        {"type": "person", "name": "Jane Roe",
         "mentions": [{"start": 0, "end": 8, "text": "Jane Roe", "confidence": 1}]},
        {"type": "company", "name": "Acme Ltd",
         "mentions": [{"start": 14, "end": 22, "text": "Acme Ltd", "confidence": 1}]},
    ]})
    created = {e["type"] for e in store.snapshot()["entities"].values()}
    assert job["skipped_types"] == ["company"] and created == {"person"}
