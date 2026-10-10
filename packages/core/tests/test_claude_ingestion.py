"""Claude output is grounded in source text; offline seeds never call a provider."""

import pytest
from propadmin_core import IngestionService, Store, seed_demo
from propadmin_core.providers import ClaudeProvider


def test_claude_ingestion_repairs_unique_quotes_and_deduplicates(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-test")
    text = "Cedar Tester uses cedar@example.test. Inspection is tomorrow."
    calls = []

    def extract(self, instruction, context):
        calls.append(context)
        return {"entities": [{"type": "person", "name": "Cedar Tester",
                             "fields": {"emails": ["cedar@example.test"]},
                             "mentions": [{"text": "Cedar Tester", "start": 9, "end": 21}]}],
                "facts": [{"key": "inspection", "value": "tomorrow",
                           "text": "Inspection is tomorrow.", "start": 0, "end": 23,
                           "entity_name": "Cedar Tester"}]}

    monkeypatch.setattr(ClaudeProvider, "json", extract)
    store = Store()
    ingestion = IngestionService(store)
    job = ingestion.ingest({"filename": "test.txt", "text": text})
    assert job["status"] == "completed" and job["extraction_provider"] == "claude"
    document = store.snapshot()["documents"][job["document_id"]]
    assert document["mentions"][0]["span"] == {"start": 0, "end": 12, "text": "Cedar Tester"}
    fact = store.snapshot()["facts"][document["facts"][0]]
    assert text[fact["span"]["start"]:fact["span"]["end"]] == fact["text"]
    assert ingestion.ingest({"text": text})["deduplicated"]
    assert len(calls) == 1


@pytest.mark.parametrize("quote", ["Invented person", "Cedar"])
def test_claude_rejects_missing_or_ambiguous_evidence(monkeypatch, quote):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-test")
    monkeypatch.setattr(ClaudeProvider, "json", lambda *args: {
        "entities": [{"type": "person", "name": "Cedar", "mentions": [{"text": quote}]}]})
    store = Store()
    with pytest.raises(ValueError, match="missing or ambiguous"):
        IngestionService(store).ingest({"text": "Cedar mentioned Cedar"})
    assert not store.snapshot()["documents"]
    assert next(iter(store.snapshot()["jobs"].values()))["status"] == "failed"


def test_seed_is_offline_with_production_extractor_enabled(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    store = Store()
    seed_demo(store)
    seed_demo(store)
    assert store.snapshot()["documents"]
    assert all(job["extraction_provider"] == "local-structured-exact"
               for job in store.snapshot()["jobs"].values())


def test_provider_requires_complete_structured_result(monkeypatch):
    from propadmin_core import providers

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-test")
    replies = [{"stop_reason": "tool_use", "content": [
        {"type": "text", "text": "Here is the result"},
        {"type": "tool_use", "name": "submit_result", "input": {"entities": []}}]},
        {"stop_reason": "max_tokens", "content": []}]
    requests = []

    def request(url, payload, headers):
        requests.append(payload)
        return replies.pop(0)

    monkeypatch.setattr(providers, "http_json", request)
    assert ClaudeProvider().json("Extract", {"text": "Test"}) == {"entities": []}
    assert requests[0]["tool_choice"]["name"] == "submit_result"
    with pytest.raises(ValueError, match="output token limit"):
        ClaudeProvider().json("Extract", {"text": "Test"})


def test_unsupported_facts_are_discarded_and_channel_records_are_authoritative(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-test")

    def extract(self, instruction, context):
        assert "email" not in context["registry"]
        return {"entities": [{"type": "person", "name": "Cedar Tester",
                             "mentions": [{"text": "Cedar Tester"}]}],
                "facts": [{"key": "notes", "value": "needs inspection",
                           "text": "needs inspection", "entity_name": "Cedar Tester"},
                          {"key": "notes", "text": "Not in the source"},
                          {"key": "notes", "value": "Missing quote"}],
                "relationships": [{"source": "Cedar Tester", "target": "Cedar Tester",
                                   "relation": "contact", "attributes": {"role": "other"}}]}

    monkeypatch.setattr(ClaudeProvider, "json", extract)
    store = Store()
    job = IngestionService(store).ingest({
        "text": "Cedar Tester needs inspection", "records": [{
            "type": "email", "name": "Inspection", "fields": {
                "message_id": "<authoritative@example.test>", "direction": "outbound",
                "status": "sent", "from_address": "ops@example.test", "subject": "Inspection"}}]})
    snapshot = store.snapshot()
    assert len(snapshot["facts"]) == 1
    assert len(job["extraction_warnings"]) == 3
    email = next(e for e in snapshot["entities"].values() if e["type"] == "email")
    assert email["fields"]["direction"] == "outbound"
    assert email["fields"]["message_id"] == "<authoritative@example.test>"
