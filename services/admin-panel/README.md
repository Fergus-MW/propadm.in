# Properly admin panel

Next.js App Router, React, Tailwind v4, TanStack Query and the MIT-licensed
`@cosmos.gl/graph` renderer. UI primitives and semantic tokens are adapted from
`propadmin-design-system/`.

Run from the repository root:

```sh
pnpm install --frozen-lockfile
pnpm dev
```

The API defaults to `http://localhost:8000`. Set `API_URL` or `API_BASE_URL` for
another API origin. Open `http://localhost:3000` and use the locally configured
admin password (`propadmin-local` by default).

Included screens: overview, graph explorer, entities and tickets, documents with
source-span highlighting, hybrid search, ingestion, six-kind edge rules, entity
types, imported calls and emails, change log, and configuration status. The graph
uses a Web Worker to decode binary snapshots, persisted coordinates, and
coalesced SSE updates. Entity edits and merges carry optimistic versions.

Ticket completion requires a final answer and a detailed evidence-based reasoning
field. The ticket editor accepts Markdown for both. Resolved and closed tickets
offer separate `answer.md` and `reasoning.md` downloads through the authenticated
API gateway. Historical completed tickets keep their recorded resolution and
explicitly identify missing original reasoning.

The frontend stores the upstream bearer token in an httpOnly, SameSite cookie.
All backend traffic flows through `/api/backend/v1/*`; mutations reject foreign
origins and SSE reconnections forward the event cursor. Browser storage is used
for the colour theme and PostHog's anonymous analytics identity. Calls and emails
are read-only imported records.

Verify locally before a PR:

```sh
pnpm --filter @propadmin/admin-panel test
pnpm --filter @propadmin/admin-panel typecheck
pnpm --filter @propadmin/admin-panel lint
pnpm --filter @propadmin/admin-panel build
```

Eight focused tests cover binary graph validation, API failures and concurrency
errors, and authenticated proxy/login handling. Provider-dependent rule
compilation and adjudication report configuration errors from the API.

## Analytics

Set `POSTHOG_PROJECT_TOKEN` to the public `phc_` project token and `POSTHOG_HOST`
to the project's ingestion host (`https://us.i.posthog.com` for US Cloud).
`make dev` loads these from the root `.env`; standalone startup needs them in
the shell environment. An empty token disables analytics. The runtime
`/api/analytics-config` endpoint allows the same container image to be configured
without a rebuild. Personal `phx_` API keys are never exposed.

Page views and explicit conversion events include the `surface` property.
Tracking excludes form values and URL query strings/fragments; session replay
and automatic DOM capture are disabled.
