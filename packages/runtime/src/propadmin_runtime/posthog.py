"""PostHog AI events and OTLP export share the runtime's existing trace IDs."""

import os
import time
from datetime import datetime, timezone

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from posthog import Posthog


class PostHogTelemetry:
    def __init__(self, service, provider):
        self.service = service
        self.environment = os.getenv("PROPADMIN_MODE", "local")
        self.client = None
        token = os.getenv("POSTHOG_PROJECT_TOKEN", "")
        if not token.startswith("phc_"):
            return
        host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").rstrip("/")
        self.client = Posthog(token, host=host, timeout=3, max_retries=1)
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{host}/i/v1/traces",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=3,
                ),
                export_timeout_millis=3000,
            )
        )

    def capture(self, event, identity, properties, timestamp):
        if self.client is None:
            return
        try:
            self.client.capture_ai(
                event,
                distinct_id=identity.get("run_id") or f"service:{self.service}",
                timestamp=timestamp,
                properties={
                    "surface": "agent",
                    "service": self.service,
                    "environment": self.environment,
                    "$process_person_profile": False,
                    **identity,
                    **properties,
                },
            )
        except Exception:
            # Analytics failures must never cause an agent action to be retried.
            pass

    def operation(self, span, name, inputs, outcome, identity):
        if self.client is None or not (identity.get("run_id") or name == "invoke_agent"):
            return
        context = span.get_span_context()
        properties = {
            "$ai_trace_id": f"{context.trace_id:032x}",
            "$ai_span_id": f"{context.span_id:016x}",
            "$ai_span_name": name,
            "$ai_latency": max(0, (time.time_ns() - span.start_time) / 1e9),
            "$ai_input_state": inputs,
            "$ai_output_state": outcome.get("result"),
            "$ai_is_error": bool(outcome.get("error")),
        }
        if identity.get("run_id"):
            properties["$ai_session_id"] = identity["run_id"]
        if not identity.get("run_id"):
            properties["$ai_parent_id"] = properties["$ai_trace_id"]
        elif span.parent:
            properties["$ai_parent_id"] = f"{span.parent.span_id:016x}"
        if outcome.get("error"):
            properties["$ai_error"] = outcome["error"]
        self.capture(
            "$ai_span", identity, properties,
            datetime.fromtimestamp(span.start_time / 1e9, timezone.utc),
        )

    def record(self, record):
        if self.client is None or record["event"] != "run.finished":
            return
        payload = record["payload"]
        created = payload.get("created_at")
        if not created or not record.get("trace_id"):
            return
        start = datetime.fromisoformat(created)
        end = datetime.fromisoformat(record["timestamp"])
        properties = {
            "$ai_trace_id": record["trace_id"],
            "$ai_session_id": record["run_id"],
            "otel_root_span_id": payload.get("trace_context", {}).get("span_id"),
            "$ai_span_name": "agent.run",
            "$ai_latency": max(0, (end - start).total_seconds()),
            "$ai_input_state": payload.get("goal"),
            "$ai_output_state": payload.get("final_message"),
            "$ai_is_error": payload.get("status") == "failed",
            "status": payload.get("status"),
        }
        if payload.get("error"):
            properties["$ai_error"] = payload["error"]
        self.capture("$ai_trace", {"run_id": record["run_id"]}, properties, start)

    def flush(self):
        if self.client:
            try:
                self.client.flush(timeout_seconds=3)
            except Exception:
                pass

    def shutdown(self):
        if self.client:
            self.client.shutdown()
