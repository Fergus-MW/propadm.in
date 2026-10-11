"""Trace correlation, redaction and Cloud Run delivery for optional PostHog export."""

import asyncio
import io
from unittest.mock import Mock

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from propadmin_runtime import posthog as integration
from propadmin_runtime.observability import Telemetry, TelemetryMiddleware, current_ids


@pytest.fixture
def configured(monkeypatch):
    client = Mock()
    spans = []

    class Exporter(SpanExporter):
        def export(self, batch):
            spans.extend(batch)
            return SpanExportResult.SUCCESS

    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test")
    monkeypatch.setenv("TOKEN_SECRET", "secret-signing-key")
    monkeypatch.setattr(integration, "Posthog", Mock(return_value=client))
    monkeypatch.setattr(integration, "OTLPSpanExporter", Mock(return_value=Exporter()))
    monkeypatch.setattr(integration, "BatchSpanProcessor", lambda exporter, **_: SimpleSpanProcessor(exporter))
    telemetry = Telemetry("api", stream=io.StringIO())
    yield telemetry, client, spans
    telemetry.shutdown()


def test_run_and_tool_events_share_native_trace_ids_and_redact_credentials(configured):
    telemetry, client, spans = configured
    with telemetry.operation("invoke_agent", {"goal": "Reconcile rent"}):
        context = current_ids()
    run = {"id": "run:test", "trace_context": context}
    with telemetry.for_run(run, "agent.sync"):
        with telemetry.operation("execute_tool search", {"token": "secret-signing-key"}):
            pass
        telemetry.emit("run.finished", {
            "created_at": "2026-10-10T00:00:00+00:00", "goal": "Reconcile rent",
            "final_message": "Done", "status": "done", "trace_context": context,
        })
    events = client.capture_ai.call_args_list
    tool = next(call.kwargs for call in events
                if call.kwargs["properties"].get("$ai_span_name") == "execute_tool search")
    root = next(call.kwargs for call in events if call.args[0] == "$ai_trace")
    native_tool = next(span for span in spans if span.name == "execute_tool search")
    assert tool["properties"]["$ai_trace_id"] == root["properties"]["$ai_trace_id"] == context["trace_id"]
    assert tool["properties"]["$ai_span_id"] == f"{native_tool.context.span_id:016x}"
    assert tool["properties"]["$ai_parent_id"] == f"{native_tool.parent.span_id:016x}"
    assert tool["properties"]["$ai_input_state"] == {"token": "[REDACTED]"}
    assert tool["properties"]["$ai_latency"] >= 0
    assert root["properties"]["otel_root_span_id"] == context["span_id"]
    assert root["properties"]["$ai_session_id"] == "run:test"


def test_failed_actions_report_error_and_analytics_failures_do_not_retry(configured):
    telemetry, client, _ = configured
    client.capture_ai.side_effect = RuntimeError("Analytics unavailable")
    with pytest.raises(ValueError, match="Provider failed"):
        with telemetry.operation("execute_tool send_email", {}, identity={"run_id": "r"}):
            raise ValueError("Provider failed")
    properties = client.capture_ai.call_args.kwargs["properties"]
    assert properties["$ai_is_error"] is True
    assert properties["$ai_error"]["message"] == "Provider failed"


def test_cloud_response_finishes_before_background_work_and_analytics(configured):
    telemetry, client, spans = configured
    order = []
    client.flush.side_effect = lambda **_: order.append("flush")

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"ok"})
        order.append("background")
        assert order[:2] == ["http.response.start", "http.response.body"]

    async def send(message):
        order.append(message["type"])

    asyncio.run(TelemetryMiddleware(app, telemetry)(
        {"type": "http", "path": "/v1/runs", "method": "GET", "headers": []}, None, send,
    ))
    assert spans[0].name == "http.request"
    assert order == ["http.response.start", "http.response.body", "background", "flush"]


def test_empty_and_personal_keys_disable_export(monkeypatch):
    for token in ("", "phx_personal-key"):
        monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", token)
        telemetry = Telemetry("api", stream=io.StringIO())
        assert telemetry.posthog.client is None
        telemetry.shutdown()
