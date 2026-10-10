# Propadmin core

Synchronous, JSON-compatible domain services shared by API and ingestion.

- `Store` provides thread-safe and process-safe local transactions using a lock
  file, atomic replace, rollback on callback failure, and bounded event replay.
- `GraphService` validates fields against a data registry, enforces hard-key
  uniqueness and entity versions, records change history, and preserves evidence
  and links on merge. Rule edges cannot be deleted as manual edges.
- `IngestionService` accepts parsed text, RFC 5322 email, Markdown, typed CRM JSON,
  and structured call records. Hashes make duplicate uploads idempotent. Source
  chunks preserve character offsets; entity mentions, field evidence, extracted
  facts, and extraction decisions retain source and extractor references.
- `RuleService` supports field equality/overlap, safe boolean/comparison
  expressions, document co-occurrence, vector similarity, and a configurable
  Claude judge. Recomputes atomically replace only their own generated edges.
- `SearchService` fuses BM25, vector and source-text rankings and expands the
  canonical graph, returning source citations. Direct matches retain ranking
  over neighbours found only by graph traversal.

Default ingestion uses **offline structured records and exact known mentions**,
not an LLM. Default embeddings use **local deterministic hashed token vectors**,
not semantic model embeddings. Demo data is synthetic and repeatable.

Select `EXTRACTION_PROVIDER=claude`, configure `ANTHROPIC_API_KEY` and
`PIPELINE_MODEL` for real extraction, identity adjudication, and rule compilation.
Select `EMBEDDING_PROVIDER=vertex`, configure `GOOGLE_CLOUD_PROJECT` or
`GCP_PROJECT_ID`, ADC, `VERTEX_LOCATION`, `EMBEDDING_MODEL`, and
`EMBEDDING_DIMENSIONS` for real embeddings. Changing embedding providers requires
re-embedding existing content; providers never silently fall back to local mode.

`SurrealRepository` supplies authenticated, parameterised SQL operations as a
separate adapter. Local `Store` is **not a production SurrealDB backend**. Cloud
Run must be wired to a durable repository before enabling cloud writes. The
external adapters are not validated against live accounts in this checkout.

PDF/DOCX, audio and images need a configured external parser/transcriber before
calling ingestion with `parsed=true`; plain text is never represented as having
passed through Docling, speech recognition or object storage. Local rule
expressions accept field comparisons and boolean operators, not arbitrary
SurrealQL. Hard-key resolution is conservative; unconfigured offline mode does
not invent embedding/LLM tie-breaks for ambiguous names.

Run `uv run pytest packages/core/tests` and
`uv run ruff check packages/core services/ingestion/app` locally.

Addendum A adds fixed `property`, `transaction`, `service_provider`,
`service_offering` and `quote` schemas. `ProviderService` ranks exact postcode
coverage and observed outcomes, filters unavailable providers, requires current
Gas Safe or NICEIC/NAPIT accreditation for regulated trades, and marks prices
older than six months. Explicit status filters support the administration
screen; recommendations exclude suspended and do-not-use firms. Quote acceptance
atomically assigns the ticket and records an expected invoice charge, without
moving money. Existing record edits require their current version.

`upgrade_addendum(state)` safely upgrades local snapshots and preserves custom
entity types. It converts ticket location text into `location_detail`, matches
existing property addresses, and replaces contractor assignments with providers
while keeping `registered_as` company links. Provider ratings and first-time-fix
metrics use ticket `tenant_feedback_rating` and `visits_count` observations;
response metrics use `first_visit_at`, never a planned appointment. Missing
observations remain unknown. Core ledger writes refresh observed provider spend
and metrics, including reversals.
