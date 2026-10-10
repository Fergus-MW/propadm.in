"""Overlapping sequence coverage, quote grounding and target-free retrieval."""

import copy

import pytest
from propadmin_core.workflow_corpus import WorkflowCorpus
from propadmin_core.workflow_replay import prepare_replay
from propadmin_core.workflow_triplets import (
    enrich_case,
    extract_metadata,
    retrieve_examples,
    validate_metadata,
    windows,
)

from tests.test_workflow_replay import corpus, fixture_sources


def test_additive_schema_upgrade_handles_deployment_order_without_erasing_custom_fields():
    from propadmin_core.addendum_upgrade import upgrade_addendum

    store, _ = corpus()
    state = store.snapshot()
    schema = state["entity_types"]["workflow_triplet"]
    schema["fields"].pop("case_ref")
    schema["fields"]["custom_note"] = {"type": "string", "required": False, "embed": False}
    version = schema["version"]
    upgrade_addendum(state)
    assert "case_ref" in schema["fields"] and "custom_note" in schema["fields"]
    assert schema["version"] == version + 1
    upgrade_addendum(state)
    assert schema["version"] == version + 1
    before = copy.deepcopy(state)
    upgrade_addendum(state)
    assert state == before


def test_model_sees_one_fixed_window_and_unsupported_metadata_is_discarded(monkeypatch):
    import json

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-haiku-5-5")
    store, imported = corpus()
    triples = windows(store.snapshot(), imported["case_id"])
    seen = []

    def model(url, payload, headers, **kwargs):
        data = json.loads(payload["messages"][0]["content"])
        seen.append([e["ordinal"] for e in data["events"]])
        event = data["events"][0]
        items = [{"kind": "insight", "basis": "inference", "step": event["ordinal"],
                  "summary": "Invented approval", "quote": "does not occur in the source"}]
        if data["start_step"] == 1:
            items.append({"kind": "action", "basis": "explicit", "step": event["ordinal"],
                          "summary": "Recorded request", "quote": event["body"]})
        return {"model": "haiku", "id": "response", "usage": {"input_tokens": 10},
                "stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "submit_triplets",
                "input": {"stage": "Request", "items": items}}]}

    monkeypatch.setattr("propadmin_core.workflow_triplets.http_json", model)
    metadata, provider = extract_metadata(triples)
    assert sorted(seen) == [[1, 2, 3], [2, 3, 4]]
    assert all(item["summary"] != "Invented approval" for row in metadata.values() for item in row["items"])
    assert all(p["warnings"] for p in provider["windows"].values())
    assert metadata[2]["items"][0]["quote"] in triples[1]["events"][2]["fields"]["body"]


def test_all_overlapping_windows_and_metadata_grounding(monkeypatch):
    store, imported = corpus()
    state = store.snapshot()
    triples = windows(state, imported["case_id"])
    assert [[e["fields"]["ordinal"] for e in t["events"]] for t in triples] == [[1, 2, 3], [2, 3, 4]]
    rows = [{"start_step": t["start_step"], "stage": "request evidence", "items": [{
        "kind": "action", "basis": "explicit", "step": t["start_step"],
        "quote": t["events"][0]["fields"]["body"], "summary": "Source-supported action",
    }]} for t in triples]
    metadata = validate_metadata(rows, triples)
    invalid = copy.deepcopy(rows)
    invalid[0]["items"][0]["quote"] = "invented approval"
    with pytest.raises(ValueError, match="exact quote"):
        validate_metadata(invalid, triples)
    with pytest.raises(ValueError, match="every overlapping"):
        validate_metadata(rows[:1], triples)
    monkeypatch.setattr("propadmin_core.workflow_triplets.extract_metadata", lambda t: (metadata, {"model": "haiku"}))
    result = enrich_case(store, imported["case_id"])
    assert result["triplets"] == 2 and not result["deduplicated"]
    assert enrich_case(store, imported["case_id"])["deduplicated"]
    state = store.snapshot()
    entities = [e for e in state["entities"].values() if e["type"] == "workflow_triplet"]
    assert len(entities) == 2
    for e in entities:
        vectors = [v for v in state["embeddings"].values() if v["owner"] == e["id"]]
        assert {v["field"] for v in vectors} >= {"context", "text"}
        assert len(e["evidence"]) == 3
        assert "FUTURE_REPLY" not in e["fields"]["context"] if e["fields"]["start_step"] == 1 else True
    from propadmin_core import GraphService

    dedicated = {v["id"] for v in state["embeddings"].values() if v.get("index")}
    schema = state["entity_types"]["workflow_triplet"]
    GraphService(store).save_entity_type(schema)
    assert dedicated <= set(store.snapshot()["embeddings"])
    from propadmin_core.workflow_triplets import embedding_id, index_status

    assert index_status(store.snapshot())["complete"]
    owner = entities[0]["id"]
    original = copy.deepcopy(store.snapshot()["entities"][owner])
    store.mutate(lambda s: s["embeddings"].pop(embedding_id(owner, "context")))
    assert not index_status(store.snapshot())["complete"]
    monkeypatch.setattr("propadmin_core.workflow_triplets.extract_metadata",
                        lambda _: pytest.fail("Vector repair must retain original model metadata"))
    assert not enrich_case(store, imported["case_id"])["deduplicated"]
    assert index_status(store.snapshot())["complete"]
    assert store.snapshot()["entities"][owner] == original


def test_retrieval_ranks_only_prefix_excludes_holdout_and_current_case(monkeypatch):
    store, imported = corpus()
    training = WorkflowCorpus(store).ingest("test", "002", fixture_sources("002"))
    holdout = WorkflowCorpus(store).ingest("test", "005", fixture_sources("005"))

    def metadata(triples):
        return ({t["start_step"]: {"stage": "evidence", "items": [{
            "kind": "action", "basis": "explicit", "step": t["start_step"],
            "quote": t["events"][0]["fields"]["body"], "summary": "Ask for evidence",
        }]} for t in triples}, {"model": "haiku"})

    monkeypatch.setattr("propadmin_core.workflow_triplets.extract_metadata", metadata)
    for case in (imported, training, holdout):
        enrich_case(store, case["case_id"])
    state = store.snapshot()
    result = retrieve_examples(state, "Tenant reports door problem", exclude_case_id=imported["case_id"])
    assert result["items"]
    assert all(row["fields"]["case_id"] == training["case_id"] for row in result["items"])
    scores = [(row["id"], row["score"]) for row in result["items"]]
    for entity in state["entities"].values():
        if entity["type"] == "workflow_triplet":
            entity["fields"].update(next_step="tenant reports door problem " * 500,
                                    text="tenant reports door problem " * 500,
                                    metadata=[{"summary": "tenant reports door problem"}])
    changed = retrieve_examples(state, "Tenant reports door problem", exclude_case_id=imported["case_id"])
    assert [(r["id"], r["score"]) for r in changed["items"]] == scores
    transition = next(e for e in store.snapshot()["entities"].values()
                      if e["type"] == "workflow_transition" and e["fields"]["case_id"] == imported["case_id"]
                      and e["fields"]["after_step"] == 1)
    replay = prepare_replay(store.snapshot(), transition["id"])
    examples = [e for e in replay["state"]["entities"].values() if e["type"] == "workflow_triplet"]
    assert examples and all(e["fields"]["case_id"] == training["case_id"] for e in examples)
    assert imported["case_id"] not in replay["state"]["entities"]
    assert holdout["case_id"] not in replay["state"]["entities"]
