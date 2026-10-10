# Properly

A local property-operations knowledge graph with source evidence, typed entities,
maintenance tickets, property ledgers, service providers, hybrid search, and a live admin panel.

The full brief is saved in [PRD.md](PRD.md). Development rules are in
[AGENTS.md](AGENTS.md), and the UI follows [design.md](design.md).
[Addendum A](PRD-ADDENDUM-A.md) extends the PRD; its implementation and decisions
are described in [the addendum notes](docs/ADDENDUM-A-IMPLEMENTATION.md).

## Run locally

Install Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20.9+, and pnpm.
From the repository root:

```sh
make dev
```

This installs locked dependencies, seeds synthetic data, and starts every
implemented service. Open **http://127.0.0.1:3000** and sign in with
**`propadmin-local`**. The API defaults to port 8000 and ingestion to 8001.
Ctrl-C stops the stack. The supervisor waits for every service to become healthy
before announcing readiness; one service failing stops the others.

Both the Next.js frontend and all Python services reload when local source changes.
Python services also watch the shared core/runtime packages and database code/schema
YAML. Dependency or environment changes require restarting `make dev`.

For containers, run `make dev-docker` instead of `make dev`; run only one stack
at a time. This combines `compose.yaml` with `compose.dev.yaml`, mounts local
source code, enables Uvicorn reload in every Python service, and runs Next.js in
development mode with Fast Refresh. Container dependencies and the Next.js cache
are isolated from host files. Rerun `make dev-docker` after dependency changes;
the shared named data volume is retained. Ctrl-C stops the containers, and
`make stop` removes them without deleting their data. Bare `docker compose up
--build` still uses the production-like images without hot reload.

Optional `.env` values override local defaults; shell environment values take
precedence. `PROPADMIN_DATA_PATH` selects the persistent local data file.
Occupied default ports automatically move to available ports; use the URLs
printed at startup. Set `API_PORT`, `INGESTION_PORT`, `ADMIN_PORT`, or
`<SERVICE>_PORT` to require specific ports. Explicit port conflicts fail clearly.
Existing unrelated processes are never terminated.

The [landing page](landing/README.md) also starts with `make dev` at
**http://127.0.0.1:3001**. Its signup form saves emails to `landing/.data/signups.csv`.

New Python services join local startup automatically once their `pyproject.toml`
and `app/main.py` exist. Add dependencies to the uv workspace and regenerate the
lockfile in the same change. Their local service URLs are supplied automatically.

## What this build delivers

This implementation focuses on **admin-panel, api, and ingestion**:

- Graph explorer with binary snapshots, GPU rendering, SSE replay and evidence.
- Typed entities, optimistic updates/merges, provenance and an undoable change log.
- Idempotent source ingestion, hard-key resolution, embedded text, hybrid search
  with source citations, and versioned rule preview/recompute inside the API.
- One graph MCP gateway at `/mcp`, with per-session access grants and audited
  read/write tools. See [MCP.md](docs/MCP.md).
- Append-only property ledgers, reconciliation, daily rent accrual, automatic fees,
  evidence-backed PDF statements and an unallocated queue.
- Provider directory, sourced service prices, accredited trade matching, quotes,
  ticket assignments and six graph-versioned operational skills.
- Generated OpenAPI request contracts, focused tests, local startup, and GCP
  infrastructure with deployment gates.

The **rules, agent, voice, email, and browser** services also start with `make dev`.
Their local health, service boundaries and configured-provider gates were checked
with the running stack. Focused tests cover their mocked provider workflows;
real external agent, voice, email and browser sessions require configuration and
were not exercised.

Voice uses the existing Vonage phone number through ElevenLabs SIP trunking.
See [voice setup](services/voice/README.md) for inbound/outbound routing,
credentials and live verification. No audio bridge container is required.

Local extraction and embeddings are explicitly deterministic offline modes.
Claude/Vertex provider adapters require configuration. SurrealDB migrations and
an HTTP adapter are included. Local runtime uses file-locked JSON; cloud mode
requires shared durable storage (the GCS adapter or an injected repository).
SurrealDB 3.0 schema guards were exercised against a real local instance.
Real provider calls and cloud deployment were not exercised.

## Checks and shared interfaces

```sh
make test
make check
pnpm --dir services/admin-panel generate:api
```

Run local checks before pushing a PR. `make check` includes Python lint/tests,
frontend tests/types/build, Terraform validation and Compose configuration.
See [verification results](docs/VERIFICATION.md),
[shared contracts](docs/BUILD-CONTRACT.md), and
[infrastructure instructions](infra/README.md).

Cloud Run execution evidence, OpenTelemetry correlation, unattended case batches and
the Cloud Logging export command are documented in [observability](docs/OBSERVABILITY.md).
