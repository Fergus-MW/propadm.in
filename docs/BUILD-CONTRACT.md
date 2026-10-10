# Shared service and API contracts

Read `PRD.md`, `AGENTS.md`, and `design.md`. This build assignment covers
admin-panel, api, and ingestion; other agents can add the remaining services
against these interfaces. Service-specific production workflows are independently
owned. Keep all source and documentation files within 1,000 lines.

## Local service integration

All implemented services must start with `make dev`. The host supervisor discovers
Python service directories containing `pyproject.toml` and `app/main.py`, installs
locked workspace dependencies, seeds shared storage, assigns ports/service URLs,
checks readiness, and handles clean shutdown. Add new service dependencies to the
root uv workspace and its lockfile. Do not require manual separate startup.

The API is the **only MCP server**. Agents use API `/mcp` for graph read/write
operations and never receive database credentials. Other services expose ordinary
internal HTTP routes; they must not create another graph MCP server. Per-session
grants can be minted through the API's authenticated internal token endpoint;
see [MCP.md](MCP.md) for the protocol and tool schemas.

## Shared core

`propadmin_core` exports synchronous `Store`, `GraphService`, `IngestionService`,
`RuleService`, `SearchService`, `ConflictError`, `ProviderNotConfigured`, `publish`,
`seed_demo`, and the separate `SurrealRepository` adapter. Domain results are
JSON-compatible dictionaries. See `packages/core/README.md` and actual method
signatures for canonical behaviour.

`Store(path=None)` is in-memory for tests. A path enables local file-backed JSON
with thread/process locks, atomic commits, rollback on callback failure, bounded
replay history, and a monotonically increasing event version. `snapshot()` returns
a deep copy; `mutate(callback)` runs an atomic state change. The local Store is
not a Cloud Run database. Production adapters require durable shared persistence.

Graph methods: `list_entities(type=None,q=None)`, `get_entity(id)`,
`create_entity(payload,actor='admin',reason='')`, `update_entity(id,payload,...)`,
`merge_entities(id,target_id,...,version=None,target_version=None)`,
`link_entities(payload,...)`, `unlink_entities(id,...)`,
`graph(depth=1,entity_id=None,type=None)`, `list_documents()`, `get_document(id)`,
`entity_types()`, and `save_entity_type(payload)`.

Updates require the current entity version. Merge checks source/target versions
atomically when supplied. Manual edge deletion cannot remove rule-generated
edges. Registry validation rejects undeclared entity fields. Writes record actor,
reason and previous values, refresh embeddings and propagate enabled rules.

Entity shape: `{id,type,name,description,aliases,fields,external_ids,version,
created_at,updated_at,layout_x,layout_y,merged_into}`. Fields follow the registry.
Edge shape: `{id,source,target,relation,rule,rule_version,score,evidence}`.
Document shape includes text, chunks, mentions, facts and source provenance.

`IngestionService(store).ingest(payload)` accepts filename, text, mime, origin,
optional structured records and extractor version. It returns a job with id,
document_id, status, chunk count and resolved entity IDs. The local pipeline is
explicitly offline; provider configuration never silently simulates success.

`RuleService` supports list/save/compile/preview/recompute. Rules use `source_type`
and `target_type`, plus relation, kind, params, enabled and version. Six kinds:
field_match, field_overlap, expression, co_occurrence, similarity and llm_judge.
Unconfigured LLM judgement fails explicitly. Rule edits require current versions;
recompute preserves manual edges.

`SearchService.search({query,types?,limit?,expand?})` returns results, citations,
elapsed_ms, embedding_provider and ranking. Local vectors are labelled
`local-deterministic-hash-v1`; they are not a production semantic model.

## Admin HTTP API

Data routes use `/v1` and Bearer authentication. `GET /healthz`,
`POST /v1/auth/login {password}` and `GET /v1/auth/status` are public. Login returns
an expiring signed token. The frontend stores it only in an httpOnly cookie and
proxies calls through `/api/backend/v1/...`; tokens never enter localStorage.

List endpoints return `{items:[...]}`; detail endpoints return the record.
Core endpoints include overview, entities, documents, entity-types, edge-rules,
search, ingestion jobs/upload/sync, actions/undo, settings, read-only calls/emails,
and MCP grants. API OpenAPI output is the request contract source of truth.
Run `pnpm --dir services/admin-panel generate:api` after API schema changes.

`POST /v1/entities/{id}/merge` accepts `{target_id,version,target_version?,reason}`.
Rules use source_type/target_type and current version; compile takes `{prompt}`.
Upload accepts JSON text/records and base64 CSV/OFX/text PDF bytes (5 MB limit).
Financial source types include bank statements, labelled invoices/receipts and
tenancy agreements. Scanned PDFs require OCR; DOCX/audio need configured adapters. Ingestion's `/internal/events/{stage}` accepts
JSON or a Pub/Sub push envelope, authenticated by an internal bearer token or
configured Google OIDC identity/audience.

## Addendum A domain contracts

`LedgerService` and `ProviderService` share the repository and event stream.
Property/transaction/provider/offering/quote schemas are fixed; derived fields
are read-only. Economic ledger writes, fees, reconciliation and balances commit
atomically. Unallocated candidates remain outside the canonical graph until
classified and assigned exactly one property. General graph mutation/undo/rule
paths cannot rewrite transaction entries. Relationship attributes are validated.
Read [the addendum notes](ADDENDUM-A-IMPLEMENTATION.md) for decisions and limits.

## Graph transport

`GET /v1/entities/graph.bin` accepts optional type, entity_id and depth. Transactions are hidden unless
`include_transactions=true` and `property_id` select one property. Header:
magic `PGR1`, uint32 metadata JSON byte length, uint32 node count, uint32 edge count
(all little endian), UTF-8 metadata `{nodes,edges,version}`, then Float32 x/y pairs
and Uint32 source/target node-index pairs.

`GET /v1/entities/graph/stream?since=` emits `event: delta`, `id: <version>`,
`data: {events,version}`. Event entries carry kind, payload and version. A
`reset` event requests a new snapshot when replay history no longer covers the
cursor. `Last-Event-ID` is supported. Local deltas are coalesced at 250ms; the UI
preserves the camera and provides pause/error/retry states.

## Validation

Validation errors return 422, missing records 404, stale writes 409, authentication
failures 401/403 and unconfigured providers 503. Run local tests/types/builds and
relevant infrastructure checks before pushing changes. Do not infer successful
provider actions or cloud deployment from local smoke tests.
