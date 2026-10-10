# Execution evidence on Cloud Run

The shared Python runtime uses the OpenTelemetry SDK for real spans and W3C trace
propagation. A synchronous span exporter writes completed spans as structured JSON
to stdout. Explicit execution records log starts before actions and results/errors
afterwards. Cloud Run collects the flushed JSON into Cloud Logging; there is no
logging sidecar, background upload queue or container-local journal.

This integration stores spans in **Cloud Logging**, not the Cloud Trace service.
`trace.jsonl` is our versioned evidence schema (`propadmin.evidence.v1`), containing
OTel span records and execution events; it is not an OTLP wire-format file.

## What is captured

- HTTP request method/path/status and exceptions, without bodies, query strings or headers.
- Authenticated MCP tool inputs, results, validation failures and unexpected errors.
- Internal service calls propagate W3C context and case identity. MCP requests recover
  the authoritative case/trace identity from the run associated with their bearer grant.
- Managed Agents HTTP operations and full exposed provider events, before the bounded
  UI transcript is reduced. An event cursor and provider event IDs distinguish repeats.
- Run inputs, session creation, completion/failure/cancellation and snapshots of existing messages, plans and actions.
- Tool action span IDs in durable run evidence allow the exporter to detect a completely
  missing tool span, not only a missing end record.

Case kickoff asks for a labelled conclusion in the agent's **normal final message**;
there is no separate reporting MCP tool. The agent uses headings `Final result`,
`Outputs and decisions`, `Actions taken`, `Escalations`, `Checks and rationale`,
`Conflicts and uncertainty`, and `Failures`, each as a level-two Markdown heading.
It must explicitly state `None` where applicable and `Unknown` when evidence is missing.
The exporter reuses that message, existing plan notes/evidence and the audited action
records. It makes no LLM calls and never repairs an answer. Escalation descriptions are
agent claims; delivery must be supported by communication results. Recorded failures
remain visible even if the agent incorrectly claims there were none.

A `done` run without a complete closing message is labelled **No clear final conclusion**,
with the latest message retained as unconfirmed and evidence completeness marked false.
Failed/cancelled runs retain their actual execution outcome. Missing evidence never
becomes a claim that nothing failed or nothing was escalated.

Every case attempt has `batch_id`, `case_id`, `attempt_id`, and the generated `run_id`.
Spans use `trace_id`/`span_id`, parent relationships, and GenAI conventions for
`invoke_agent` and `execute_tool`. Observed provider control-plane HTTP requests are
not labelled as model generations. All our spans are recorded, without sampling.

Credentials are redacted by structured field name, bearer/assignment patterns and known
environment secret values before logs or blobs are written. This is not PII anonymisation:
case inputs, correspondence and business documents remain evidence. Only appropriate
synthetic hackathon data should be included in the public submission.

## Payload size and durability

Payloads above 128,000 UTF-8 bytes go to `gs://<artifacts-bucket>/evidence/<event-id>.json`.
The log records object generation, SHA-256 and byte count. Upload uses
`if_generation_match=0` and runtime IAM grants create-only access to this prefix.
The exporter retrieves the exact generation, verifies length/hash and embeds the
resolved payload in `trace.jsonl`; judges do not need bucket access.

Without a configured bucket, or if upload fails, the payload is split into individually
bounded base64 JSON log records. Reconstruction is lossless; missing chunks cause an
incomplete export. Upload failures are logged. A telemetry encoding/sink failure must
not turn an already completed external action into a retry.

## Deployment

The existing Python Dockerfiles already run `uv sync --locked --no-dev --extra cloud`
and set `PYTHONUNBUFFERED=1`. The updated runtime dependency installs OTel; the cloud
extra installs the Cloud Logging client for exporting. No Dockerfile or new service
is required. `make dev` remains the local entry point and needs no GCP credentials.

Terraform changes:

1. `infra/bootstrap` enables `logging.googleapis.com`.
2. `infra/main` sets `OBSERVABILITY_ARTIFACT_BUCKET` to the existing artifacts bucket
   on Python services and grants conditional `roles/storage.objectCreator` for `evidence/`.
3. Existing Cloud Scheduler minute sweeps continue to wake/sync queued and sleeping runs.
   One failing run no longer stops the rest of a sweep.

Use the repository's existing Terraform plan/apply and Cloud Build release procedure
in [infra/README.md](../infra/README.md). Apply the bootstrap/main infrastructure changes
and release the Python images together so the API and agent share the case schema and telemetry.
No deployment is performed by either command below.

Cloud Run's stdout collection does not require our application to call the Logging
write API or carry a service-account key. The **exporting identity**, authenticated
through Application Default Credentials, needs `roles/logging.viewer` on the project
and `roles/storage.objectViewer` on the artifacts bucket. These reader permissions
are not granted to every runtime service. Do not exclude these evidence records from
the project's log storage. Check an actual cloud round trip after deployment.

## Run a batch

Prepare a JSON manifest containing the actual supplied cases. This is an input example,
not an execution result:

```json
{
  "batch_id": "reality-2026-10-10",
  "kind": "reality_test",
  "cases": [
    {
      "case_id": "007",
      "attempt_id": "first",
      "goal": "Handle the supplied property-management case",
      "subjects": [],
      "input": {"case_text": "The actual case supplied by the organisers"}
    }
  ]
}
```

**Exactly one folder per organiser case, never per plan step or tool call.** Set `case_id`
to the organiser's ID as a string (e.g. `"007"` preserves leading zeros). If your input
adapter needs a different internal ID, set `"case_id": "incoming-a"` and
`"organiser_case_id": "007"` on that manifest entry. This mapping is configurable when
the actual 16:30 format arrives; no source-file format or automatic numbering is assumed.
Mapping collisions and inconsistent mappings across attempts are rejected before execution.

Set `kind` explicitly to `reality_test` for the official unseen batch. Omitted `kind`
defaults to `practice`; `dev` is also supported. Practice/dev exports are forbidden under
any `ANSWERS` path (including resolved symlinks). The standalone export command defaults
to `ANSWERS` for Reality Tests and `evals/<batch_id>` otherwise. For a practice batch, use
`--export-dir evals/<batch_id>` with the runner. Public historical cases are practice data;
the importer must distinguish supplied history from work actually performed by the agent.
The runner consumes the explicit manifest; it does not yet import a GitHub case directory.

IDs accept letters, digits, `_` and `-`. Use a new attempt ID for a retry; original
attempts and failures remain in evidence. Put inputs in `input` (sent to the agent),
not merely in an external file path the hosted agent cannot access.

Set `PROPADMIN_ADMIN_TOKEN` in the shell environment to a current admin API token.
Do not place it in the manifest or command line. Then:

```sh
uv run --extra cloud python -m infra.scripts.run_cases \
  --api-url https://YOUR_API_SERVICE \
  --manifest cases.json \
  --receipt .artifacts/reality-receipt.json \
  --parallel 4 --deadline-seconds 1500 \
  --export-dir ANSWERS \
  --project YOUR_PROJECT \
  --artifact-bucket YOUR_PROJECT-artifacts
```

The command runs cases concurrently, records submission/polling errors, requests
cancellation at its deadline and keeps going after a case fails. It writes a local
command receipt atomically as cases finish. This receipt preserves expected cases even
if a submission never reaches a Cloud Run instance; it is not the runtime log store.
The receipt path must be new. A create request with an ambiguous failure is not retried
automatically, because it may already have started a run.

The deadline is an execution budget, with up to an additional request timeout and
cancellation/export time. Leave submission margin before 17:00 London. On 2026-10-10,
16:30 London is 15:30 UTC and 17:00 London is 16:00 UTC.

## Export independently

```sh
uv run --extra cloud python -m infra.scripts.export_evidence \
  --project YOUR_PROJECT \
  --manifest .artifacts/reality-receipt.json \
  --since 2026-10-10T15:25:00Z \
  --until 2026-10-10T15:58:00Z \
  --artifact-bucket YOUR_PROJECT-artifacts \
  --out ANSWERS --wait-seconds 30
```

The time bounds select execution events. Waiting allows late ingestion without moving
the cutoff. The SDK iterator reads every page without a result-count cap. Additional
queries retrieve native request/container logs sharing observed trace IDs.

Output:

```text
ANSWERS/
  manifest.json       expected cases and any batch-runner receipts
  export.json         provenance, cutoff and evidence gaps per case
  logs.jsonl          retrieved Cloud LogEntry records, including supporting logs
  007/
    ANSWER.md         final result, outputs/decisions, actions taken, escalations
    REASONING.md      received input, checks, uncertainty, failures, evidence IDs
    trace.jsonl       deduplicated events, OTel spans and verified payloads
```

Each case gets exactly one `ANSWER.md`, one `REASONING.md` and an adjacent `trace.jsonl`.
`ANSWER.md` opens with the final result immediately after the case title, before run
metadata and action details. Outcomes from every attempt remain labelled in that opening section.
Internal steps, tool calls, retries and escalations roll up into those files. Multiple
attempts remain labelled inside the same files in manifest order; retries discovered
in the logs but absent from the manifest are appended and flagged as evidence gaps.
No successful attempt silently replaces a failure. A case that never reaches the agent still gets the same files,
with its submitted input labelled unconfirmed and the submission failure retained.

The six required questions have explicit sections:

| Requirement | File / section |
| --- | --- |
| What the system received | REASONING.md / What the system received |
| What actions it took | ANSWER.md / Actions taken + Tool execution record |
| Outputs or decisions | ANSWER.md / Outputs and decisions |
| What it escalated | ANSWER.md / Escalations |
| What failed | REASONING.md / Failures + Batch runner failures |
| Final result | ANSWER.md / Final result |

These sections always exist, even without a conclusion or execution evidence. Source event
IDs link the messages, action audit and plan snapshots to `trace.jsonl`. Batch runner
receipts are also embedded there with `source: batch_runner_receipt`, retaining submission
errors and polling retries without presenting them as Cloud Logging events. Conflicts and
uncertainty are recorded separately; the exporter does not invent a resolution.

An existing output directory is always refused. To inspect a later snapshot, use a
different directory; do not overwrite a failed output. Include the generated files in
the submission repo through the normal review/commit workflow. These commands do not
commit or push them automatically.

Exporter exit codes: `0` known completeness checks passed; `2` files written but evidence
is incomplete; `1` export failed. A faithfully recorded failed case can have complete
evidence. The batch command additionally returns nonzero for failed/cancelled executions,
even when exporting their evidence succeeds.

## Verification and limits

Run `uv run pytest`, `make lint`, `pnpm --dir services/admin-panel generate:api --check`,
and Terraform format/validation after changes. No new test files are included in this
change, per the requested delivery scope; temporary checks exercised correlation,
redaction, large payloads, Cloud LogEntry normalisation, failures and immutable exports.

After deployment, run a clearly labelled synthetic batch including a successful case,
tool failure and cancellation. Export using the real Cloud Logging API and verify that
the files retain the input, actions, rationale and actual failures. Local verification
does not establish cloud IAM, delivery latency or provider availability.

Completeness checks cover expected cases, starts/ends, audited tool span IDs, exposed
provider event inventories and payload hashes. Missing closing conclusions and cancelled sessions
whose provider events were not fully collected are explicitly incomplete. Stdout
collection is not transactional with external side effects: hard termination can lose
records before they reach the platform. Hidden provider internals, unexposed sandbox
activity and uncorrelated platform logs cannot be reconstructed. No monitoring backend
can prove those happened from absent evidence.

References: [Cloud Run logging](https://docs.cloud.google.com/run/docs/logging),
[structured fields](https://docs.cloud.google.com/logging/docs/structured-logging),
[Logging limits](https://docs.cloud.google.com/logging/quotas),
[Python Logging client](https://docs.cloud.google.com/python/docs/reference/logging/latest/google.cloud.logging_v2.client.Client),
[OTel Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/).
