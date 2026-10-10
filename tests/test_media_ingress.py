"""Raw PDFs/images are retained and parsed consistently for upload and AgentMail ingress."""

import base64
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from propadmin_core import Store
from propadmin_core.ingestion import IngestionService
from propadmin_core.media import describe_media
from propadmin_core.workflow_judge import grade
from propadmin_runtime import create_app
from propadmin_runtime.auth import issue_token
from propadmin_runtime.config import Settings

from services.email.app import main as email_service

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jMh0AAAAASUVORK5CYII=")


def test_uploaded_image_retains_original_and_embeds_caption_without_merging_distinct_files(monkeypatch):
    monkeypatch.setattr("propadmin_core.media.describe_media", lambda encoded, mime: (
        "A visible damaged window handle; diagnosis is uncertain.", {
            "model": "claude-haiku-5-5", "usage": {"input_tokens": 123, "output_tokens": 12},
            "input_block": {"type": "image", "source": {"type": "base64", "data": encoded, "media_type": mime}},
        }))
    store, settings = Store(), Settings()
    with TestClient(create_app(store=store, settings=settings, seed=False)) as client:
        headers = {"Authorization": f"Bearer {issue_token(settings)}"}
        payload = {"filename": "damage.PNG", "mime": "application/octet-stream", "content_base64": base64.b64encode(PNG).decode()}
        response = client.post("/v1/ingest/upload", headers=headers, json=payload)
        assert response.status_code == 201, response.text
        first = response.json()["document_id"]
        document = store.snapshot()["documents"][first]
        assert base64.b64decode(document["raw_content_base64"]) == PNG
        assert document["mime"] == "image/png"
        assert document["multimodal"]["usage"]["input_tokens"] == 123
        assert any("window handle" in e["text"] for e in store.snapshot()["embeddings"].values())
        from propadmin_core.search import SearchService

        results = SearchService(store).search({"query": "damaged window handle", "types": ["media_asset"]})
        assert results["results"][0]["citations"]
        asset = store.snapshot()["entities"][results["results"][0]["id"]]
        assert asset["fields"]["source_document"] == first
        payload["content_base64"] = base64.b64encode(PNG + b"different-original").decode()
        second = client.post("/v1/ingest/upload", headers=headers, json=payload)
        assert second.status_code == 201 and second.json()["document_id"] != first


def test_email_pdf_and_image_download_raw_bytes_into_the_shared_pipeline(monkeypatch):
    pdf = Path("Property Management/008/attachments/attachment-02-estimate.pdf").read_bytes()
    monkeypatch.setattr("propadmin_core.media.describe_media", lambda encoded, mime: ("Damaged door latch visible.", {"usage": {"input_tokens": 10}}))
    calls = []
    monkeypatch.setattr(email_service, "agentmail", lambda *args: {
        "filename": "quote.pdf" if args[1].endswith("pdf") else "photo.png",
        "content_type": "application/pdf" if args[1].endswith("pdf") else "image/png",
        "download_url": "https://files.example.test/" + args[1].split("/")[-1],
    })

    def download(method, url, **kwargs):
        calls.append(url)
        return httpx.Response(200, content=pdf if url.endswith("pdf") else PNG)

    monkeypatch.setattr(email_service.httpx, "request", download)
    store = Store()
    app = create_app("email", store=store, seed=False)
    attachments = email_service.ingest_attachments(app, {
        "inbox_id": "inbox", "message_id": "message", "attachments": [
            {"attachment_id": "pdf"}, {"attachment_id": "image"}],
    })
    assert len(calls) == len(attachments) == 2
    documents = [store.snapshot()["documents"][a["document"]] for a in attachments]
    assert documents[0]["mime"] == "application/pdf" and "Estimate" in documents[0]["text"]
    assert base64.b64decode(documents[0]["raw_content_base64"]) == pdf
    assert documents[1]["mime"] == "image/png" and "latch" in documents[1]["text"]


def test_media_without_mandatory_canonical_keys_still_ingests_and_embeds(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-haiku-5-5")
    monkeypatch.setattr("propadmin_core.media.describe_media", lambda *args, **kwargs: (
        "Flat 1 at Example Road; Alice Tenant reports a damaged latch.", {"usage": {"input_tokens": 10}}))
    monkeypatch.setattr("propadmin_core.providers.ClaudeProvider.json", lambda *args, **kwargs: {
        "entities": [{"type": "property", "name": "Flat 1", "fields": {"address_line1": "Example Road"},
                      "mentions": [{"text": "Flat 1"}]},
                     {"type": "person", "name": "Alice Tenant", "fields": {},
                      "mentions": [{"text": "Alice Tenant"}]}], "facts": [],
    })
    store = Store()
    job = IngestionService(store).ingest({"filename": "latch.png", "content_base64": base64.b64encode(PNG).decode()})
    assert job["status"] == "completed"
    assert any("ref is required" in warning for warning in job["extraction_warnings"])
    assert any(e["type"] == "person" and e["name"] == "Alice Tenant" for e in store.snapshot()["entities"].values())
    assert not any(e["type"] == "property" for e in store.snapshot()["entities"].values())
    assert "damaged latch" in store.snapshot()["documents"][job["document_id"]]["text"]


def test_scanned_pdf_vision_fallback_and_incomplete_media_output_are_explicit(monkeypatch):
    from io import BytesIO

    from pypdf import PdfWriter

    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    raw = buffer.getvalue()
    monkeypatch.setattr("propadmin_core.media.describe_media", lambda encoded, mime, pdf=False: (
        "Scanned inspection report: door latch damaged.", {"usage": {"input_tokens": 100}}))
    job = IngestionService(Store()).ingest({"filename": "scan.pdf", "mime": "application/pdf",
                                          "content_base64": base64.b64encode(raw).decode()})
    assert job["status"] == "completed"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-haiku-5-5")
    monkeypatch.setattr("propadmin_core.media.http_json", lambda *args, **kwargs: {
        "stop_reason": "max_tokens", "content": [{"type": "text", "text": "partial"}]})
    with pytest.raises(ValueError, match="did not complete"):
        describe_media(base64.b64encode(PNG).decode(), "image/png")


def test_haiku_grading_validates_scores_and_critical_errors(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("PIPELINE_MODEL", "claude-haiku-5-5")
    result = {"scores": {key: 100 for key in ["action", "facts", "recipient_channel", "sequence", "communication"]},
              "critical_error": True, "explanation": "Invented approval", "differences": ["No approval in prefix"]}

    def provider(url, payload, headers, **kwargs):
        assert "haiku" in payload["model"]
        assert payload["tool_choice"]["name"] == "submit_grade"
        assert json.loads(payload["messages"][0]["content"])["expected_next_step"] == "Request approval"
        return {"model": payload["model"], "id": "grade1", "usage": {"input_tokens": 100},
                "stop_reason": "tool_use", "content": [{"type": "tool_use", "name": "submit_grade", "input": result}]}

    monkeypatch.setattr("propadmin_core.workflow_judge.http_json", provider)
    graded = grade("No approval yet", "Request approval", "Book the job")
    assert graded["score"] == 100 and graded["passed"] is False
    result["scores"]["action"] = float("nan")
    with pytest.raises(ValueError, match="scores"):
        grade("No approval yet", "Request approval", "Book the job")
