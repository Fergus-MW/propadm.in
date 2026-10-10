"""OTel spans and execution evidence as Cloud Run logs, with optional PostHog export.

Cloud Run collects each flushed JSON line. PostHog queues flush before response completion.
Full payloads are separate from OTel's bounded attributes. ContextVars isolate requests.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import sys
import threading
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import NonRecordingSpan, SpanContext, SpanKind, StatusCode, TraceFlags
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .posthog import PostHogTelemetry

SCHEMA = "propadmin.evidence.v1"
IDENTITY = ContextVar("propadmin_evidence_identity", default={})
ACTIVE_TELEMETRY = ContextVar("propadmin_active_telemetry", default=None)
WRITE_LOCK = threading.RLock()
IDENTITY_KEYS = ("batch_id", "case_id", "attempt_id", "run_id")
SECRET_KEY = re.compile(
    r"(^|[_-])(password|passwd|secret|token|authorization|cookie|api[_-]?key|credential)(s|$)",
    re.I,
)
BEARER = re.compile(r"\bBearer\s+[^\s\"',;]+", re.I)
INLINE_SECRET = re.compile(
    r"""((?:password|passwd|api[_-]?key|access[_-]?token|token|secret)["']?\s*[=:]\s*)"""
    r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;}]+)""",
    re.I,
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def redact(value):
    """Credential redaction, not PII anonymisation: case evidence retains business content."""
    secrets = [v for k, v in os.environ.items() if SECRET_KEY.search(k) and len(v) >= 8]

    def clean(item):
        if isinstance(item, dict):
            return {
                str(k): "[REDACTED]" if SECRET_KEY.search(str(k)) else clean(v)
                for k, v in item.items()
            }
        if isinstance(item, (tuple, list)):
            return [clean(v) for v in item]
        if isinstance(item, str):
            for secret in secrets:
                item = item.replace(secret, "[REDACTED]")
            return INLINE_SECRET.sub(r"\1[REDACTED]", BEARER.sub("Bearer [REDACTED]", item))
        return item

    return clean(value)


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def current_ids():
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    return {"trace_id": f"{context.trace_id:032x}", "span_id": f"{context.span_id:016x}"}


def run_identity(run):
    return {**{k: run[k] for k in IDENTITY_KEYS if run.get(k)}, "run_id": run["id"]}


def run_context(run):
    saved = run.get("trace_context", {})
    if not saved:
        return None
    span = SpanContext(
        int(saved["trace_id"], 16),
        int(saved["span_id"], 16),
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    return trace.set_span_in_context(NonRecordingSpan(span))


def propagation_headers():
    headers = {}
    TraceContextTextMapPropagator().inject(headers)
    headers.update(
        {
            f"x-propadmin-{key.replace('_', '-')}": str(value)
            for key, value in IDENTITY.get().items()
            if key in IDENTITY_KEYS
        }
    )
    return headers


def incoming_context(headers):
    context = TraceContextTextMapPropagator().extract(headers)
    if trace.get_current_span(context).get_span_context().is_valid:
        return context
    # Cloud Run request logs may use this header instead of W3C traceparent.
    match = re.fullmatch(
        r"([0-9a-f]{32})/(\d+)(?:;o=([01]))?", headers.get("x-cloud-trace-context", "")
    )
    if match and 0 < int(match[2]) < 2**64:
        span = SpanContext(
            int(match[1], 16),
            int(match[2]),
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        return trace.set_span_in_context(NonRecordingSpan(span))
    return context


class GcsArtifacts:
    """Immutable objects; ADC and a lazy client keep local startup credential-free."""

    def __init__(self, bucket):
        self.bucket_name = bucket
        self._client = None

    def put(self, key, content):
        if self._client is None:
            from google.cloud import storage

            self._client = storage.Client()
        blob = self._client.bucket(self.bucket_name).blob(f"evidence/{key}.json")
        blob.upload_from_string(
            content, content_type="application/json", if_generation_match=0, timeout=15
        )
        return {"uri": f"gs://{self.bucket_name}/{blob.name}", "generation": str(blob.generation)}


class LoggingSpanExporter(SpanExporter):
    def __init__(self, telemetry):
        self.telemetry = telemetry

    def export(self, spans):
        for span in spans:
            self.telemetry.emit(
                "otel.span",
                json.loads(span.to_json()),
                trace_id=f"{span.context.trace_id:032x}",
                span_id=f"{span.context.span_id:016x}",
            )
        return SpanExportResult.SUCCESS


class Telemetry:
    def __init__(self, service, *, project=None, artifacts=None, stream=None):
        self.service, self.project = service, project or os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.stream = stream
        bucket = os.getenv("OBSERVABILITY_ARTIFACT_BUCKET")
        self.artifacts = artifacts or (GcsArtifacts(bucket) if bucket else None)
        resource = {"service.name": service, "service.version": os.getenv("K_REVISION", "local")}
        # Per-app provider avoids global-provider replacement and duplicate instrumentation.
        self.provider = TracerProvider(resource=Resource.create(resource), sampler=ALWAYS_ON)
        self.provider.add_span_processor(SimpleSpanProcessor(LoggingSpanExporter(self)))
        self.posthog = PostHogTelemetry(service, self.provider)
        self.tracer = self.provider.get_tracer("propadmin.runtime", "1.0.0")

    def _write(self, record):
        with WRITE_LOCK:
            stream = self.stream or sys.stdout
            stream.write(encode(record).decode() + "\n")
            stream.flush()

    def emit(self, event, payload, *, severity="INFO", **fields):
        try:
            return self._emit(event, payload, severity=severity, **fields)
        except Exception as exc:
            # A malformed result or failed log sink must never retry an external action.
            fallback = {
                "schema": SCHEMA,
                "event": "evidence.emit_error",
                "event_id": uuid4().hex,
                "timestamp": utcnow(),
                "severity": "ERROR",
                "service": self.service,
                **IDENTITY.get(),
                **current_ids(),
                "payload": {"lost_event": event, "error_type": type(exc).__name__},
            }
            try:
                self._write(fallback)
            except Exception:
                try:
                    sys.stderr.write("propadmin evidence write failed; export may be incomplete\n")
                except Exception:
                    pass
            return fallback["event_id"]

    def _emit(self, event, payload, *, severity="INFO", **fields):
        record = {
            "schema": SCHEMA,
            "event": event,
            "event_id": uuid4().hex,
            "timestamp": utcnow(),
            "severity": severity,
            "service": self.service,
            "revision": os.getenv("K_REVISION", "local"),
            **IDENTITY.get(),
            **current_ids(),
            **fields,
            "payload": redact(payload),
        }
        record["logging.googleapis.com/insertId"] = record["event_id"]
        if record.get("trace_id") and self.project:
            record["logging.googleapis.com/trace"] = (
                f"projects/{self.project}/traces/{record['trace_id']}"
            )
            record["logging.googleapis.com/spanId"] = record.get("span_id", "")
            record["logging.googleapis.com/trace_sampled"] = True
        content = encode(record["payload"])
        self.posthog.record(record)
        if len(content) > 128_000:
            ref = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
            if self.artifacts:
                try:
                    ref.update(self.artifacts.put(record["event_id"], content))
                except Exception as exc:
                    self.emit(
                        "evidence.storage_error",
                        {
                            "error": str(exc),
                            "fallback": "stdout_chunks",
                            "for_event": record["event_id"],
                        },
                        severity="ERROR",
                    )
            if "uri" not in ref:
                chunks = [content[i : i + 64_000] for i in range(0, len(content), 64_000)]
                ref.update(event_id=record["event_id"], chunks=len(chunks))
                for index, chunk in enumerate(chunks):
                    self.emit(
                        "payload.chunk",
                        {
                            "for_event": record["event_id"],
                            "index": index,
                            "data": base64.b64encode(chunk).decode(),
                        },
                    )
            record.pop("payload")
            record["payload_ref"] = ref
        self._write(record)
        return record["event_id"]

    @contextmanager
    def operation(
        self, name, inputs, *, identity=None, context=None, attributes=None, kind=SpanKind.INTERNAL
    ):
        # A run's stored identity replaces incoming labels; don't inherit another case
        # when one request starts several queued runs.
        token = IDENTITY.set(dict(IDENTITY.get() if identity is None else identity))
        active_token = ACTIVE_TELEMETRY.set(self)
        attrs = {f"propadmin.{k}": str(v) for k, v in IDENTITY.get().items()}
        attrs.update(attributes or {})
        try:
            with self.tracer.start_as_current_span(
                name,
                context=context,
                attributes=attrs,
                kind=kind,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                operation_id = uuid4().hex
                self.emit(
                    "operation.started", {"name": name, "input": inputs}, operation_id=operation_id
                )
                outcome = {}
                try:
                    yield outcome
                except BaseException as exc:
                    error = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "stacktrace": "".join(traceback.format_exception(exc)),
                    }
                    span.set_status(StatusCode.ERROR, redact(str(exc)))
                    outcome["error"] = error
                    self.emit(
                        "operation.finished",
                        {"name": name, "error": error},
                        operation_id=operation_id,
                        severity="ERROR",
                    )
                    raise
                else:
                    if outcome.get("error"):
                        span.set_status(StatusCode.ERROR)
                    self.emit(
                        "operation.finished",
                        {"name": name, **outcome},
                        operation_id=operation_id,
                        severity="ERROR" if outcome.get("error") else "INFO",
                    )
                finally:
                    self.posthog.operation(
                        span, name, redact(inputs), redact(outcome), dict(IDENTITY.get())
                    )
        finally:
            ACTIVE_TELEMETRY.reset(active_token)
            IDENTITY.reset(token)

    def for_run(self, run, name, inputs=None, **kwargs):
        return self.operation(
            name, inputs or {}, identity=run_identity(run), context=run_context(run), **kwargs
        )

    def flush(self):
        if self.posthog.client:
            self.provider.force_flush(timeout_millis=3000)
            self.posthog.flush()

    def shutdown(self):
        self.provider.shutdown()
        self.posthog.shutdown()


def observed_run(function):
    @wraps(function)
    def wrapped(app, run_id, *args, **kwargs):
        run = app.state.store.snapshot()["runs"][run_id]
        with app.state.telemetry.for_run(
            run, f"agent.{function.__name__}", {"args": args, "kwargs": kwargs}
        ) as operation:
            result = function(app, run_id, *args, **kwargs)
            operation["result"] = {
                "run_id": run_id,
                "status": result.get("status"),
                "action": result.get("action"),
            }
            return result

    return wrapped


class TelemetryMiddleware:
    """Pure ASGI middleware preserves context across streaming responses and sync routes."""

    def __init__(self, app, telemetry):
        self.app, self.telemetry = app, telemetry

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/healthz":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        final_body = None
        context = incoming_context(headers)
        identity = {
            k: headers[f"x-propadmin-{k.replace('_', '-')}"][:200]
            for k in IDENTITY_KEYS
            if f"x-propadmin-{k.replace('_', '-')}" in headers
        }
        # Never log query strings, headers or arbitrary request bodies (login credentials).
        with self.telemetry.operation(
            "http.request",
            {"method": scope["method"], "path": scope["path"]},
            context=context,
            identity=identity,
            kind=SpanKind.SERVER,
            attributes={"http.request.method": scope["method"], "url.path": scope["path"]},
        ) as outcome:

            async def respond(message):
                nonlocal final_body
                if message["type"] == "http.response.body" and not message.get("more_body", False):
                    final_body = message
                    return
                if message["type"] == "http.response.start":
                    span = trace.get_current_span()
                    span.set_attribute("http.response.status_code", message["status"])
                    route = scope.get("route")
                    if route is not None and hasattr(route, "path"):
                        span.set_attribute("http.route", route.path)
                        span.update_name(f"{scope['method']} {route.path}")
                    outcome["result"] = {"status_code": message["status"]}
                    if message["status"] >= 400:
                        outcome["error"] = {"type": "HTTPError", "status_code": message["status"]}
                await send(message)

            await self.app(scope, receive, respond)
        # Flush while Cloud Run still allocates request CPU, before the last body.
        if self.telemetry.posthog.client:
            await asyncio.to_thread(self.telemetry.flush)
        if final_body is not None:
            await send(final_body)
