# Single graph MCP gateway

The `api` service hosts the only graph MCP server at `POST /mcp`.
Neither `ingestion` nor any future service should host another MCP server.
Agent callers hold a signed, expiring session bearer token, never database credentials.
The API gateway serves all implemented services. Agent, rules, voice, email and
browser services added by other agents use this same endpoint.
Graph tools work locally without a Managed Agents deployment.

## Session access

Sign in at `POST /v1/auth/login` with `{ "password": "…" }`.
Use the returned admin bearer token for `POST /v1/mcp/tokens`:

```json
{"session_id":"maintenance-42","reason":"Tenant follow-up","lifetime_seconds":3600}
```

The response contains `token`, `session_id`, `expires_in`, and `endpoint`.
Lifetime is capped at 86,400 seconds. Treat this token as a credential.
`GET /v1/mcp/tokens` returns grant metadata without tokens.
`DELETE /v1/mcp/tokens/{session_id}` revokes access immediately.
Session IDs cannot be reused, including after revocation; rotate using a new ID.
This prevents a newly issued grant from reviving old tokens.
Expired signatures are rejected even if their grant is still present.

A trusted agent service can use `POST /internal/mcp/tokens` with service
authentication and the same body. It must keep its service credential server-side
and give the hosted session only the returned graph token.
This service-authenticated endpoint is available on the API only.

## Streamable HTTP

The server responds with JSON without holding transport sessions or SSE streams.
`GET /mcp` and `DELETE /mcp` return 405. Transport sessions are distinct from
persisted access grants. POSTs require `Content-Type: application/json` and
`Accept: application/json, text/event-stream`. An `Origin` header must match
the endpoint host. Batches and bodies over one megabyte are rejected.

MCP `2025-11-25` clients use `initialize`, then send
`notifications/initialized` (202 with an empty body). No `Mcp-Session-Id` is issued.
Subsequent requests include `MCP-Protocol-Version: 2025-11-25`.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {"name": "local-agent", "version": "1.0.0"}
  }
}
```

MCP `2026-07-28` clients call `server/discover` and tools directly.
Include the protocol version on every request, both in `MCP-Protocol-Version`
and `params._meta["io.modelcontextprotocol/protocolVersion"]`.
Send `Mcp-Method` equal to the JSON-RPC method and `Mcp-Name` equal to the tool
name for `tools/call`. Advertised tool names are ASCII.
Mismatches return HTTP 400 with error `-32020`; unsupported versions return
`-32022` and supported versions. Unknown methods return 404 with `-32601`.
Authentication failures use HTTP 401/403.

```http
POST /mcp
Authorization: Bearer <session-token>
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: get_entity

{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_entity","arguments":{"id":"person:amelia-thompson"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}
```

`tools/list` advertises object schemas fully inline, without `$ref` or root
composition keywords. `tools/call` returns text JSON and the same object in
`structuredContent`, with `isError`. Validation, stale versions, missing records
and protected writes are tool errors the agent can inspect and recover from.
Malformed envelopes and unknown tools return JSON-RPC errors.

## Graph tools

| Tool | Arguments | Behaviour |
| --- | --- | --- |
| `search` | `query`, optional `types`, `limit`, `expand` | Hybrid search with source citations; local embeddings are labelled |
| `get_entity` | `id` | Fields, evidence, edges, history and version |
| `traverse` | `entity_id`, optional `depth`, `type` | Neighbourhood up to five hops |
| `get_document` | `id` | Source text, chunks, mentions and facts |
| `query_graph` | `query` | Explicit unavailable error locally; no raw SurrealQL executes |
| `upsert_entity` | `type`, `name`, `reason`, optional `id`, `version`, fields | Create, or update an explicit existing ID with its current version |
| `update_entity` | `id`, `version`, `reason`, changed fields | Validated optimistic update |
| `link_entities` | `source`, `target`, `relation`, `reason`, optional `attributes` | Create validated manual edge (including ownership share/tenancy dates) |
| `unlink_entities` | `id`, `reason` | Remove manual edge; generated edges protected |
| `merge_entities` | `id`, `target_id`, `version`, `target_version`, `reason` | Atomic source/target version checks, merge history and redirected edges |
| `add_note` | `id`, `version`, `note`, `reason` | Append to a declared `array<text>` notes field; embed and publish |

Mutation reasons are required. Shared core validates IDs and typed fields.
Re-read on a conflict rather than retrying a stale version. `add_note` supports
types declaring an editable notes field; transaction notes remain immutable.
Tools cannot edit rules, remove generated
edges, or change live skills/versions including their links.
Communications, browser, plan, sleep and scheduling tools are contributed by their
service modules through this same gateway.

Every tool invocation records actor `agent_run:<session_id>`, session, reason,
status and tool in actions, including read calls and failures. MCP audit records
exclude authentication headers, payloads and returned documents. Graph core
change records preserve previous and resulting values for mutations. Grant
records contain metadata only. Changes publish through the same local replay
stream used by the graph explorer.

## Property, ledger and provider tools

| Tools | Behaviour |
| --- | --- |
| `get_property`, `get_ledger`, `get_balances` | Property relationships, dated ledger with running balances, or weighted landlord totals |
| `get_unallocated`, `allocate` | Inspect staged candidates and assign one property; unresolved receipts also need category/kind |
| `record_transaction`, `reverse_transaction`, `settle` | Append validated entries, reverse mistakes, match partial payments to charges |
| `generate_statement` | Historical property/landlord PDF stored as a source file, with authenticated download URL |
| `find_providers`, `get_provider` | Coverage/trade/service ranking, valid accreditations, offerings, jobs and spend |
| `upsert_provider`, `upsert_offering`, `set_provider_status` | Validated provider/price changes with evidence and status reasons |
| `record_quote`, `accept_quote` | Track quote, assign ticket and record expected expense without moving money |

Amounts are positive integer pence; explicit adjustment deltas supply signs.
Pending claims do not contribute received funds. Economics are immutable;
forward status promotion and appended evidence use dedicated ledger paths.
General entity edits, merges, deletion, undo and rule tools cannot rewrite ledger
entries. Passing `skill` to `record_transaction` records the workflow version;
reversals linked to a followed skill create workflow issues.
Six seeded version-1 skills cover arrears, reconciliation, contractor invoices,
landlord statements, choosing providers and provider research.

## Verification and references

```sh
uv run pytest tests/test_mcp.py
uv run ruff check packages/runtime/src/propadmin_runtime/mcp.py tests/test_mcp.py
```

The focused suite covers authentication, both protocol eras, discovery and
headers, inline schemas, writes, conflicts, merge versions, protected data,
audit records, expiration and revocation.

Official specifications fetched with Context7:
[2025-11-25 lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http),
[2026-07-28 discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover).
