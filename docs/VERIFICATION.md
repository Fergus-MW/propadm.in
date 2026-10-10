# Local verification

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
