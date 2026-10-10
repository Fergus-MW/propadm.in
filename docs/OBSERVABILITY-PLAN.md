# Cloud Logging observability implementation plan

Goal: preserve actual agent execution on Cloud Run and export self-contained judge evidence.
The approved design uses Cloud Logging, OpenTelemetry and a repository command; no PostHog
or durable container-local journal. Work follows the existing runtime/service/script layout.

## Implementation

1. Add shared runtime telemetry: real OTel spans, W3C propagation, Cloud Logging JSON on
   stdout, credential redaction, explicit operation starts/finishes and large-payload handling.
   Test correlation, concurrent isolation, failures, redaction and payload recovery first.
2. Instrument the FastAPI factory, internal HTTP calls, MCP dispatch and Managed Agents
   orchestration. Keep full provider events outside the bounded UI transcript. Add optional
   case identity and snapshots of existing messages, plans and action audits. Ask for a labelled
   normal closing message; do not add a reporting tool. Isolate failures in queue sweeps.
   Test actual requests, validation errors, retained events and failure continuation.
3. Add an exporter under infra/scripts with reusable runtime evidence rendering. Query
   Cloud Logging with ADC, bounded timestamps and pagination; deduplicate, retrieve and
   verify artifacts, check expected cases and unmatched starts, and refuse overwrites.
   Generate exactly one ANSWER.md and REASONING.md plus trace.jsonl per organiser case,
   with all six required evidence sections and machine-readable completeness metadata.
   Keep practice/dev exports under evals; require reality_test kind for ANSWERS. Support
   explicit organiser ID mapping and preserve every attempt within its case folder.
   Test missing/duplicate/conflicting records, artifact failures, failed cases and reruns.
4. Add an unattended batch command using the existing agent endpoints, bounded concurrency,
   a deadline and an append-only local command manifest (not a deployed telemetry journal).
   Preserve submission failures and export every expected case. Test case isolation.
5. Wire artifact permissions/environment through existing Terraform; document local/cloud
   usage, evidence limitations and exact verification commands. Run relevant and full Python
   tests, lint and available infrastructure validation. Present the final code diff.

## Constraints and review focus

- No extra MCP server, database access for agents, or service required for local development.
- Python 3.12+, FastAPI/Pydantic, uv workspace; each source/test/lock file below 1,000 lines.
- Logs describe received/executed events, not inferred hidden provider activity.
- Preserve attempts and failures; render recorded rationale without generating new answers.
- Secrets must not enter logs, artifact blobs, traces or generated submission files.
- Exports must identify missing cases, unfinished calls, late logs and missing payloads.
- Telemetry errors must not turn a completed external action into a retried action.
- Cloud delivery is not transactional with external side effects; never claim exactly-once
  logging or complete hosted-provider internals.
