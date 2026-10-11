# Verification

## Production fixes and retest — 10–11 October 2026

The failures in the earlier run below were followed by fixes, local regression
checks and production deployment. Verification uses controlled test recipients
and synthetic records; operational ledger balances remain unchanged.

- Email sends reserve a durable idempotency key, use AgentMail's idempotency
  header, save acceptance independently of extraction and claim the thread before
  enrichment. A real retry returned the same provider message; the controlled
  recipient received exactly one copy. Source extraction failures have a local
  recording fallback and cannot turn an accepted send into a failed-send result.
- Browser extraction and clicking pass with the production Sonnet model after
  replacing unsupported forced tool choice with auto and validating the result.
  Browser open, extraction, actual navigation click, screenshot and close passed.
- App/API/voice/email Cloud Run domain mappings are Ready with managed TLS.
  Verified HTTPS 200 on all four from GCP. The local DNS cache has now refreshed;
  Chrome opens `app.withproperly.com` and production sign-in succeeds.
- Voice has an end-call tool, 25-second silence timeout and one-message voicemail
  instructions. A real outbound voicemail test ended after 18 seconds via
  `end_call`; its webhook updated the same canonical call record.
- A fresh inbound regression exposed initiation timeouts. Agent events now return
  a durable queued run/tool grant before remote provisioning. SIP caller ids
  without `+` are normalised; signed initiation-failure events settle failed/busy
  calls and deduplicate repeated webhooks. Transcript ingestion runs off the ASGI
  event loop. Telemetry now sends the final response before background work or
  analytics flushing; a regression checks the ASGI ordering. Python services have
  4 GiB for the larger shared vector cache. API/agent/voice stay warm; the agent
  has CPU outside requests for
  post-response provisioning, with durable queue recovery by its scheduler.
  A fresh owned-line PSTN round trip completed both legs in 57 seconds. The inbound
  assistant confirmed clear audio and the controlled caller's identity; initiation
  returned 200 in 5.37 seconds and the signed webhook settled the canonical record.
  After the Vertex switch, a second owned-line test invoked live `get_entity` and
  `search` tools successfully, read back the expected name, and settled both call
  legs as completed (91 seconds including the tool exchange). Associated test
  agent runs finished with no operational action. Historical synthetic initiation
  failures were reconciled against the provider's failed status and retained for audit.
- Workflow tuning's scheduler is enabled. A new unseen private case completed
  automatically with one evaluation and a passing 92.7 score. Its trace exposed
  an additional example-search handler signature error, now fixed and covered
  through the actual MCP transport. A second automatic private test passed at 91.1
  with successful example retrieval.
- Concurrent writer checks exposed a SurrealDB 3.0.0 lost-update defect. After a
  production data-disk snapshot, SurrealDB was upgraded to 3.3.0; locked revision
  reads, unique commit markers and bounded conflict retries preserve all 160
  increments in an eight-writer real-database regression.
- The current portal is deployed. Today, Inbox, Maintenance, Viewings, Calendar
  and Availability load in Chrome. Negated hazard reports no longer trigger an
  emergency; later positive hazards still do. The live portal version stream's
  accidental snapshot invocation was fixed and has a regression check.
- Semantic embeddings migrate resumably to Vertex `gemini-embedding-001` at 1536
  dimensions, preserving the old search space until completion. Batches stay
  within the database RPC size limit; read-only scans avoid cloning every vector,
  concurrent source changes cannot commit stale vectors, and removed fields clear
  both spaces. Similarity rules use only the active model and avoid full-vector
  copying. Workflow triplet embeddings remain in their own index. All 8,285 source
  entries were staged before the switch; production now reports Vertex active,
  offline=false and zero pending entries. Three live paraphrase queries returned
  vector matches and citations in 0.96–1.41 seconds; the shower hot-water query
  included the expected ticket `ticket:prop-1042`.

Local validation: `make check` passed **157 Python tests** (four database tests
require an explicit local database), and `SURREAL_TEST_URL=http://127.0.0.1:8008
SURREAL_TEST_PASSWORD=local-surreal uv run pytest packages/core/tests/test_surreal_store.py`
passed those **four real-database tests**, for **161 Python tests** overall, alongside
**29 frontend tests** and **four landing-server tests**, plus Python lint,
frontend types/build, generated API contracts, Terraform and Compose validation.
`make schema-check` applied migrations 001–005 against SurrealDB 3.3.0.
Frontend ESLint passed with one existing generated-import warning.

The final deployment uses image tag `prod-fixes-20261011-1125`. The post-cutover
retest passed all seven public health checks, portal/property/document/tuning
reads, controlled email retry/delivery, and browser MCP actions. A test-harness
revocation URL was corrected; the temporary grant was then revoked successfully.
All four service custom domains returned HTTPS 200 locally, and Chrome showed
Vertex search results/citations, completed calls, and the single test email on
the custom app domain. The signed-in production tab is left open for the user.
Terraform reports no changes; the deployment is reconciled with its configuration.

The scope still excludes valid signup/chat notifications, real financial mutations
and live skill publication. Fresh phone checks used Properly's own line and an AI
caller; the user's earlier successful answered-call confirmation remains the
evidence for a human recipient. These exclusions are not reported as passes.
Scoped evidence remains under `/tmp/properly-prod-e2e-20261010/` (restricted).

## Earlier production end-to-end checks — 10 October 2026

Tested the deployed `properly-511210` Cloud Run stack with real providers, under
reference `prod-e2e-20261010-165229`. **This is not an all-pass result.**
Controlled test inboxes and a user-supplied phone recipient were used. No
deployment, DNS, scheduler, live skill, or operational financial changes were made.

### Verified

- All 19 deployed admin navigation screens loaded their data in Chrome, with no
  application console errors. The graph rendered about 4,580 nodes. Property
  balances, rent filtering, bank-source highlighting, search results/citations,
  and the recorded call transcript worked. At 390 × 844, the property page had
  no document overflow and the mobile navigation opened.
- API/admin-proxy login and logout, incorrect passwords, absent credentials,
  Secure/HttpOnly cookies, origin rejection, and access after logout behaved
  correctly. All seven Python services responded through their Cloud Run URLs.
- Graph, document, property, landlord, provider, ledger, communications, audit,
  skills, workflow corpus, ingestion, and tuning reads succeeded. Graph binary
  framing/counts and SSE replay were verified. JSON/PDF statement generation
  succeeded; PDF signature and nonempty output were checked, not visual layout.
- A dedicated synthetic contact supported creation, versioned edits, stale-write
  rejection, audited undo and repeat-undo conflict protection. Test edits were
  restored. MCP initialization/discovery, graph reads/search, session revocation,
  and revoked-token rejection passed. Other services did not expose `/mcp`.
- Live Claude text ingestion, source retrieval, and duplicate-source idempotence
  passed. Inbound AgentMail attachment delivery produced a downloadable source
  document and raw GCS object containing the exact synthetic marker.
- An email was sent to the user-supplied address and recorded in the graph.
  A separate controlled inbox round trip exercised Managed Agents, plans,
  graph/skill reads, outbound email, inbound webhooks, sleep, thread ownership,
  wake-up and acknowledgement. All six plan steps eventually completed.
- The outbound SIP call reached voicemail. ElevenLabs returned a 122-second,
  25-turn transcript; its signed post-call webhook returned 200 and updated the
  existing call record, which was visible in the admin UI. The user subsequently
  confirmed that the test call worked. The captured transcript contains voicemail
  rather than an answered conversation; no fresh inbound test call appeared in
  the final check. Unsigned email/voice callbacks and unauthenticated voice
  initiation were rejected.
- The public landing page, analytics configuration, invalid-email/name handling,
  and honeypot handling passed. A valid new signup was not submitted because it
  sends a notification to the configured chat webhook.

### Failures and deployment gaps

| Finding | Evidence and consequence |
| --- | --- |
| Email may send successfully while reporting failure | The first agent send reached the controlled recipient, then ingestion failed with `Claude evidence quotes are missing or ambiguous in source text`; the tool returned 422. The agent retried, delivering a second message. The failed send had no canonical outbound email/claimed thread, and its reply started a separate run. The agent's final report incorrectly claimed the first attempt delivered nothing and exactly one email was delivered. This is a duplicate-send and audit/ownership defect. |
| Browser action/extraction fail with the configured model | Browserbase open, screenshot and close passed. Both `browser_act` and `browser_extract` failed. A minimal request reproduced Anthropic HTTP 400: `tool_choice: type "tool" and "any" are not supported for this model.` The browser adapter uses `claude-sonnet-5-5` with the forced named tool in `ClaudeProvider.json`. |
| App/API/voice/email custom domains are unavailable | Local resolution failed for the four subdomains; public DNS returned Google-hosted addresses for app/API, but verified TLS connections also failed. Cloud Run listed mappings only for `withproperly.com` and `www.withproperly.com`. Testing therefore used the working Cloud Run application/service URLs. |
| Voice does not end promptly after voicemail | The agent recognized voicemail, left its message, then repeatedly said goodbye until the 122-second call ended. The requested test was under one minute. Answered two-way audio, inbound caller context and live voice tools remain unverified in this run. |
| Tuning work does not advance automatically | `propadmin-workflow-tuning` Cloud Scheduler was `PAUSED`. A private unseen-case test remained `running` in phase `sample`, with zero trials. That test was stopped through its API; the production scheduler was not resumed. |
| Concurrent writes can exhaust retries | One isolated contact creation returned 409, `Concurrent updates to shared state; retry the operation`, while other test work was running. A later serialized attempt passed. This is an observed contention limit, not evidence of lost committed writes. |
| Production search uses offline embeddings | API runtime/search output reported `local-deterministic-hash-v1`, 256 dimensions, `offline=true`. Vertex configuration exists but is inactive for these searches. Lexical search/citations passed; production semantic embedding quality was not validated. |
| Portal functionality is not in this deployment | `/v1/portal` returned 404 and the deployed navigation uses Overview rather than Today/Inbox/Maintenance/Viewings. The portal implementation in the working tree was not exercised in production. `/v1/workflow-tuning` is available; `/v1/tuning` is not its endpoint. |

Public `/healthz` requests returned Google-branded 404 pages, while ordinary
service routes worked. This is consistent with the reserved paths ending in `z`
documented in [Cloud Run known issues](https://docs.cloud.google.com/run/docs/known-issues),
so these responses were not counted as seven service outages. A different public
health path is needed for external monitoring.

Raw, scoped evidence and the temporary test harness are in
`/tmp/properly-prod-e2e-20261010/` (restricted local directory). Commands included
`uv run python` for `probe.py`, `followup.py`, `agent_journey.py`,
`browser_journey.py`, `phone.py`, `attachment.py`, and `tuning_test.py`, plus
Chrome UI checks and read-only Cloud Run/Logging/Scheduler inspection. Initial
handwritten MCP requests missing required transport headers were corrected;
those harness errors are not product defects. `list_skills` is not a deployed
MCP tool; the real agent used `get_skill` successfully.

Temporary test grants were revoked, Browserbase sessions closed, the private tuning
test stopped, and temporary credentials/full graph snapshots removed. Chrome was
left signed in to the production app for the user's own visible-screen testing. Synthetic
test sources, contacts, messages, runs, call and audit evidence remain in
production for traceability. Valid new signup persistence/chat notification,
PDF layout, real financial mutations, skill publication, answered audio and a
fresh inbound PSTN call were not verified; none is represented as passed.

## Properly rebrand

Rebranded on 10 October 2026: login/sidebar wordmark, browser title/application
metadata, SVG favicon, statement PDF footer/title, API documentation and external
service display names. Existing technical identifiers and stored sessions remain
compatible. Mobile QA also found and fixed dashboard grid sizing that let the
activity table widen the page.

Verified the running Docker stack in Chrome: login/logout, the Properly wordmark,
favicon/metadata, keyboard focus, light/dark themes, 390px mobile navigation and
page width, and authenticated statement download. The PDF's title/footer were
checked through extraction and visual rendering. No browser JavaScript errors
were observed. Artifacts and the smoke script are in `/tmp/properly-rebrand/`
and `/tmp/properly-rebrand-qa.py`.

Passed: 14 focused Python tests (API, statement, email and agent), 17 frontend
tests, Python/frontend lint, type checking, the final production build and
generated API contract validation. All eight containers remain healthy in one
development stack.

Before pushing, integrated the newer landing-page and submission-checklist
commits from `origin/main`. `make check` passed on the combined tree: 70 Python,
17 admin-panel and four landing-server tests, types, production build, Python
lint, Terraform/Compose validation and generated API contracts. Separately,
`pnpm --dir services/admin-panel lint` passed.

## Repeat E2E verification and local hot reload

Rechecked on 10 October 2026 after adding local hot reload. **33 live
browser/HTTP scenarios passed**, alongside `make check`: **70 Python tests**,
**17 frontend tests**, Python lint, frontend types/production build, both Compose
configurations, Terraform validation and generated API contracts. Frontend ESLint
also passed. The Python suite retains the upstream Starlette TestClient warning.

The running application is now one Docker development stack, using
`compose.yaml` plus `compose.dev.yaml`. The previous native stack was stopped
before containers started. All eight containers are healthy; the admin panel is
at http://127.0.0.1:3000, API at :8000, and browser adapter at :8007 because an
unrelated container occupies :8006. Start it again with
`BROWSER_PORT=8007 make dev-docker`; login remains `propadmin-local`.
Native `.data/state.json` was retained; Docker uses its named data volume.

Live checks covered:

- Incorrect passwords, loopback login, HttpOnly session cookies, origin protection
  and logout; all 16 main desktop pages.
- Property balances, rent ledger filtering and bank-source span highlighting;
  authenticated PDF downloads and sourced provider prices/accreditations.
- Browser ingestion/document viewing, hybrid search citations, shared worker/API
  persistence and duplicate-source idempotence; saved edge-rule previews.
- Binary graph format, visible WebGL rendering, property transaction visibility,
  node inspection and live graph updates without refreshing the page.
- Optimistic edit conflicts, audited undo and repeat-undo conflict protection.
- 390 × 844 property/provider layouts without document overflow, mobile
  navigation, light/dark themes and no uncaught browser JavaScript or server errors.
- Session-scoped MCP ledger access and revocation; non-API services reject `/mcp`.
  Unconfigured agent, voice, email and browser providers return explicit 503s.

Testing exposed an undo regression on entities with calculated fields. Undo now
omits schema-declared read-only fields; two focused regression cases verify
property balances and provider metrics remain intact while names are restored.
Next.js development resources also needed `127.0.0.1` in `allowedDevOrigins`
when the server binds to `0.0.0.0` inside Docker.

Hot reload was exercised with real, temporary source edits and restored afterward:

- Native `make dev`: a shared runtime edit restarted all seven Python services.
- Docker: an API-only edit reloaded that service; a shared runtime edit reloaded
  all seven services without recreating containers.
- Next.js: a component edit changed the open browser through Fast Refresh;
  a marker in the page context survived, confirming no full-page reload.

The live harness, JSON results, browser trace, screenshots, PDF and logs are in
`/tmp/propadmin-e2e-20261010/` (temporary artifacts). Commands:
`uv run --with playwright python /tmp/propadmin-e2e-20261010/run_e2e.py` and
`uv run --with playwright python /tmp/propadmin-e2e-20261010/test_hot_reload.py`.
Synthetic visit-note sources and statement artifacts remain in local Docker
data; ledger balances were verified unchanged, test edits were restored and MCP
grants revoked. No real external provider calls or cloud deployment were tested.

## Earlier baseline

Verified on 10 October 2026. Addendum A was implemented across
ledger/ingestion, provider/schema/scheduling and admin UI, then integrated and
checked locally.

## Pre-push end-to-end verification

The full stack was started using `make dev`, followed by `make check` and
`pnpm --dir services/admin-panel lint`. All passed: **68 Python tests**,
**17 frontend tests**, lint, type checking, production compilation, Terraform
validation, Compose configuration and generated API contract checks.

Browser testing found that Next.js normalizes loopback hosts to `localhost` in
`NextRequest.nextUrl`, causing sign-in and mutations at the advertised
`127.0.0.1` address to fail the origin check. Session and backend routes now
compare against the incoming Host and URL protocol. A regression test covers
loopback login, logout and writes, while rejecting different hosts, ports,
opaque origins and spoofed forwarded hosts. Checks were rerun after the fix.

The compiled application was served on port 3100 with `next start`, using the
same seven backends. Native Chrome and live HTTP checks verified:

- Invalid-password rejection, login, cookie-authenticated requests and logout.
- Property balances, filtered rent ledger and highlighted bank-reference evidence.
- Browser ingestion of a synthetic visit note, entity resolution and search citations.
- Worker ingestion sharing persistent data with the API, and duplicate-source idempotence.
- Binary graph snapshots, SSE replay and visible graph updates without reloading.
- Property transaction visibility and node inspection in the GPU graph.
- Optimistic edit conflicts, audited updates and undo conflict protection.
- Provider qualifications, sourced prices, job history and eligibility filtering.
- Authenticated PDF downloads, saved-rule previews and edge recomputation.
- API-only MCP discovery and ledger reads, with temporary grants revoked afterward.
- Explicit 503 responses for unconfigured agent, email and voice providers.
- Mobile navigation, light/dark themes and 390 × 844 property/provider layouts
  with document width equal to viewport width; wide tables scroll internally.

No application console errors were observed; browser extensions emitted their
own messages. SIGINT stopped the development supervisor and all seven backends
and the admin child; every task-owned listener was verified closed. The temporary
production server was also stopped. External provider calls and cloud deployment
were not tested. Synthetic test records remain only in ignored local data.

## Commands and results

| Command | Result |
| --- | --- |
| `make check` | Passed: lint, tests, types, build, infrastructure and generated contracts |
| `uv run pytest` | 68 tests passed |
| `pnpm --dir services/admin-panel test` | 4 test files, 17 tests passed |
| `uv run ruff check packages services db infra/scripts infra/tests tests` | Passed |
| `pnpm --dir services/admin-panel lint` | Passed |
| `pnpm --dir services/admin-panel typecheck` | Passed |
| `pnpm --dir services/admin-panel build` | Production build passed |
| `docker compose config --quiet` | Passed |
| `terraform fmt -check -recursive infra` | Passed |
| `terraform -chdir=infra/bootstrap validate` | Passed |
| `terraform -chdir=infra/main validate` | Passed |
| `pnpm --dir services/admin-panel generate:api --check` | 12 modules match 66 backend paths |

A coverage run with `uv run pytest --cov=propadmin_core --cov=propadmin_runtime`
measured **83%** statement coverage across shared core/runtime: ledger 86%,
provider directory 90%, ingestion 84%, financial ingestion 80%, parsers 77%,
statements 98%, store 100%, layout 99%, search 97% and MCP 86%.
External extraction/embedding adapters are 28%; their live calls were not tested.
The suite emits one upstream Starlette warning about its HTTPX TestClient.

Tests emphasize scenarios and boundaries: exact pence arithmetic and atomic
rollback; rent calendars and tenancy bounds; pending claims confirmed by bank
lines; identity, immutable economics and cumulative evidence; partial settlement,
fees and reversals; historical weighted statements; provider eligibility,
accreditation expiry, quotes and observed metrics; relationship attributes;
API/MCP authentication, auditing and bypass prevention. Ambiguous receipts must
be classified before allocation through either REST or the same MCP endpoint.
The multipage PDF scenario checks first/last entries, exact totals, stored source
chunks, authenticated downloads, idempotence and skill-caused reversal issues.

## Running stack and browser checks

Bare `make dev` started every implemented service: admin, API, ingestion, rules,
agent, voice, email and browser. Seven backend health endpoints returned HTTP 200;
admin readiness also passed. The browser moved from occupied default port 8006
to 8007, preserving the unrelated Docker listener. Ctrl-C stopped all development
children, including the API’s daily London rent scheduler. Explicit conflicting
port overrides fail; optional automatic default-port fallback remains supported.

A live HTTP/MCP smoke verified unauthenticated property access is rejected,
all 16 financial/provider tools are advertised on API `/mcp`, balance reads
succeed, and all six non-API backend services return 404 for `/mcp`.
The synthetic property has £0 tenant arrears, £779 landlord funds and £1,500
held deposit after rent, fees and a contractor payment. The temporary verification
MCP grant was revoked.

Native Chrome desktop and 390 × 844 mobile QA passed:

- Property balances, owners, tenants, open tickets and the filtered ledger.
- Ledger evidence opens the correct bank line with its exact reference highlighted.
- Provider details show the £85 offering, source, valid Gas Safe accreditation,
  insurance and observed metrics.
- Landlord properties use ownership weights and download actual PDF statements.
- Graph starts with 43 nodes and no transactions; selecting the property and
  enabling transactions shows 49 nodes, including its six ledger entries.
- Canvas colours/rendering, property fields without writable balances, and mobile
  pages without horizontal overflow; the ledger table scrolls within its container.

The rendered synthetic landlord PDF was inspected visually after correcting an
orphan page break. Both property sections, opening/closing figures, transaction
kind/status, evidence references and footer fit cleanly on one A4 page. Long
statements split their tables over pages and repeat table headers.

## Database and verification boundaries

All four migrations applied to an actual temporary **SurrealDB 3.0.0** instance.
Privileged-user probes rejected economic edits, deletion, backward status changes,
evidence removal, overwritten references and lowered confidence. Forward status
and appended provenance succeeded. Temporary instances were removed.

Local runtime uses shared file-locked JSON; migration checks do not establish
that every live domain write currently uses SurrealDB. Cloud mode requires shared
durable storage. Live extraction/embedding, bank, email/voice/browser providers
and Cloud Run deployment were not exercised. Supported local financial PDF
layouts require text; arbitrary layouts and scans need extraction/OCR inputs.
See [implementation decisions](ADDENDUM-A-IMPLEMENTATION.md).

The final source scan checked 335 text files: none exceeds 1,000 lines, and the
largest is the 904-line PRD. Compact lockfiles preserve valid package metadata.
The design system’s former branding is absent. The extracted design system is
versioned; its original ZIP export, local credentials, runtime data and build
outputs are ignored. The pre-push source scan found no credential signatures.
