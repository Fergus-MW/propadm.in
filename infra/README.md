# Local development and infrastructure

Services: **admin-panel, api, ingestion, rules, agent, voice, email, browser**.
The API's `/mcp` is the only agent MCP gateway; voice, email and browser
register their tools there and never expose parallel MCP endpoints.

## Run locally

Run `make dev` from the repository root. `uv` installs Python dependencies,
the supervisor installs the locked pnpm workspace, seeds shared persistent data,
and starts API on 8000, ingestion on 8001, and the admin panel on 3000. It loads
`.env` if present, while shell environment values take precedence. The default
login password is `propadmin-local`. Ctrl-C or a service crash stops the entire
stack. Future Python services are discovered once `app/main.py` and a service
`pyproject.toml` exist; add their dependencies/workspace membership to root
`pyproject.toml` and regenerate the lock before running them. Default ports are
registered in `infra/scripts/dev.py` (new names receive ports from 8010).
Port conflicts produce an actionable error without terminating unrelated
processes. Set `API_PORT`, `INGESTION_PORT`, or `ADMIN_PORT` to choose other ports.

`make seed` seeds `.data/state.json` idempotently. `PROPADMIN_DATA_PATH` overrides
that path. Both Python services share the file with cross-process locking; this
storage is suitable for local development only.

`make test` runs the focused Python and frontend suites. `make check` additionally
runs Python lint, frontend types/build, Terraform checks and Compose validation.
Run these locally before pushing a PR, and record commands/results in its body.

`make dev-docker` starts all eight services with a shared local data volume,
source bind mounts, Python reloaders (including shared packages) and Next.js Fast
Refresh. It uses `compose.dev.yaml`; bare Compose uses the production-like images.
Only run one application stack at a time. Port overrides such as
`BROWSER_PORT=8007 make dev-docker` also work for containers. Dependency changes
require rerunning the command; container dependency/cache volumes are refreshed
without deleting application data.
The optional `docker compose --profile surreal up -d surrealdb` starts SurrealDB
3.0.0 on localhost:8008 for database development. It does not change the active
application repository. To create the local namespace and apply the schema:

```sh
SURREAL_PASSWORD=local-surreal make schema-check
```

## Terraform

`infra/bootstrap` creates a dedicated project, enables required APIs, creates a
versioned private state bucket, a Cloud DNS zone, and the Cloud Build service
account. The optional GitHub connection uses an existing Secret Manager token
reference, so token values never enter Terraform state. Grant the Cloud Build
service agent access to that referenced secret before creating the connection,
and complete the GitHub App installation/connection approval.

```sh
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap plan -var-file=terraform.tfvars
terraform -chdir=infra/main init -backend-config=bucket=PROJECT-tf-state -backend-config=prefix=main
terraform -chdir=infra/main plan -var-file=terraform.tfvars
```

Copy the `.tfvars.example` files to ignored `terraform.tfvars`, replacing example
project, billing and image values. The bootstrap initially uses local state;
after creating the bucket, migrate its state to a separate GCS prefix if desired.
No apply, deployment, provider calls or DNS changes are performed by local checks.

Main modules provision Artifact Registry, private raw/artifact buckets, scoped
service accounts and secret access, ingestion Pub/Sub stages with authenticated
push and retained dead-letter subscriptions, parameterized DNS records, and
Cloud Build PR/deployment triggers. Cloud Run services and the migration/text
backfill jobs require `enable_runtime=true`. Every service has zero minimum
instances, CPU throttling and startup CPU boost.

**Shared state in cloud** is one JSON object in the `PROJECT-state` bucket
(`PROPADMIN_DATA_PATH=gs://...`), written with GCS generation compare-and-swap
so every Cloud Run instance sees one consistent store. It manages a few writes
per second; the SurrealDB repository is the upgrade path. Every service URL,
`MCP_SERVER_URL` and the OIDC caller identity are derived in `infra/main`.

Deploy into an existing project:

```sh
# bootstrap: create_project = false, create_dns_zone = false in terraform.tfvars
terraform -chdir=infra/bootstrap apply
gcloud builds submit --config cloudbuild/images.yaml --substitutions _TAG=v1 .
# main: images = {...:v1}, enable_runtime = true, secret_versions = {...}
terraform -chdir=infra/main apply
```

Add provider secret versions (`anthropic-api-key`, `elevenlabs-api-key`,
`elevenlabs-webhook-secret`, `elevenlabs-tool-secret`, `agentmail-api-key`, `agentmail-webhook-secret`,
`browserbase-api-key`) to Secret Manager and list them in `secret_versions`;
non-secret ids (`MANAGED_AGENT_ID`, `MANAGED_ADMIN_AGENT_ID`, `MANAGED_ENVIRONMENT_ID`,
`ELEVENLABS_AGENT_ID`, `ELEVENLABS_PHONE_NUMBER_ID`, `BROWSERBASE_PROJECT_ID`,
`PIPELINE_MODEL`, `BROWSER_MODEL`) go in `service_environment`. Unconfigured
providers answer 503. Cloud Scheduler sweeps agent wake-ups every minute and
runs a nightly full edge recompute.

Production ingestion uses Claude Haiku 5.5 by default in `api`, `ingestion`,
`email` and `voice`, including email attachments and call transcripts. Each of
these services receives the Anthropic secret; `secret_versions` must contain
`anthropic-api-key`. Override `PIPELINE_MODEL` in `service_environment` when
changing models. Local development keeps its credential-free extractor.
Generated ledger statements use deterministic extraction of their supplied
records. Verify production jobs report `extraction_provider=claude` and the
configured model as `extractor_version`; setting a model alone does not enable
Claude extraction.

For production email, `secret_versions` must include both `agentmail-api-key`
and `agentmail-webhook-secret`. Terraform removes manually attached Cloud Run
secret references when they are absent from this map, causing inbound webhooks
to return 503 and preventing outbound replies. Record provider secret versions
in `terraform.tfvars` when configuring them, even if the first attachment was
made with `gcloud`.

For Vonage, use the ElevenLabs ID of the imported Vonage number in the voice
service's `service_environment`. Calls always use ElevenLabs' SIP endpoint.
Vonage account credentials and trunk passwords
are provisioning credentials, not voice-service runtime secrets. Follow the
[voice setup](../services/voice/README.md); no extra Cloud Run service is needed.

Secrets are mounted only into their consuming services. The API/ingestion
accounts may invoke Vertex models, and ingestion can write raw objects. Delivery
uses `propadmin-events@PROJECT.iam.gserviceaccount.com` with a Cloud Run URL OIDC
audience. Internal handlers must verify that identity and audience.

## DNS and Cloud Build

The separate public landing service is enabled by `landing_image`. Build it with
`cloudbuild/landing.yaml`; its private GCS signup bucket and service identity are
managed in `infra/main/landing.tf`. This can be deployed independently of the
eight application services. See [landing hosting instructions](../landing/README.md).

Change the registrar nameservers to the bootstrap output after deployment.
Domain mappings require prior ownership verification. Set `domain_services` to
map admin/api hostnames, read the resulting DNS records, and put their actual
values in `dns_records`. No fake MX, SPF or DKIM values are supplied.

Cloud Build runs Python lint/tests, frontend tests/types/build, and Terraform
format/validation on PRs. Deployment triggers build a commit-tagged container and
are blocked by `_DURABLE_BACKEND_VERIFIED=false`. Runtime provisioning, production
Terraform plans/applies, migration execution and smoke tests require configured
project access and durable storage; they are not represented as completed cloud
validation. Once configured, publish images first, provision the runtime with
Terraform, apply migrations, then enable the deployment trigger gate.

## Generated files

The strict entity migration is generated from `propadmin_core.registry` using
`uv run python db/schema/generate.py`. Other migrations define evidence, hybrid
HNSW/fulltext indexes, versioned relations, and future durable runtime records.
All three were applied successfully to a real local SurrealDB 3.0.0 instance.
Provider-backed ingestion and full production concurrency need separate tests.

Generated lockfiles preserve all package hashes and metadata while meeting the
1,000-line cap. After updating dependencies run:

```sh
uv lock
uv run --no-sync python infra/scripts/compact_lock.py
uv run --no-sync python infra/scripts/compact_yaml_lock.py
uv lock --check
pnpm install --frozen-lockfile
```

The YAML lockfile uses grouped JSON, which is valid YAML. Compaction verifies
semantic equality before saving; neither lockfile loses dependency metadata.

## PostHog

Set `POSTHOG_PROJECT_TOKEN` (a public `phc_` ingestion token) and `POSTHOG_HOST`
in `.env` for `make dev` and Compose. Empty tokens disable analytics and need no
cloud credentials. For Cloud Run, set `posthog_project_token` and `posthog_host`
in `infra/main/terraform.tfvars`; Terraform passes them to every service and the
landing page. Both sites fetch public config at runtime, so no build-time token
is required. Never put a personal `phx_` API key in application config.

Browser events have a `surface` of `landing` or `admin`. Page views, landing
signup outcomes and admin sign-ins/outs are explicit events; form values are not
recorded, query strings/fragments are removed, and session replay is disabled.
Python services export native OTel spans to `/i/v1/traces`. Agent runs and tools
also emit `$ai_trace` and `$ai_span` events with the same trace/span/parent IDs,
run/session IDs, duration, redacted inputs/outputs and errors. Cloud Run requests
flush queues before the final response body and services flush on shutdown.

Claude Managed Agents hosts the model loop. This integration records the local
orchestrator and MCP tools; it cannot report hidden provider-side generations,
token counts or costs that Anthropic does not return. Existing Cloud Logging
evidence remains available.
