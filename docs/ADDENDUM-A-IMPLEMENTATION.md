# Addendum A implementation and verification

[Addendum A](../PRD-ADDENDUM-A.md) extends the main [PRD](../PRD.md). Properties,
transactions, service providers, service offerings and quotes are implemented
across the registry, ingestion, API, single MCP gateway and admin panel. The
system records, reconciles and reports money; it has no payment-initiation tool
or registered provider bank-detail field.

## Graph and schemas

The fixed canonical schemas validate enums, dates, positive GBP pence, safe
integer bounds and embedded free-text fields. Property identity combines
postcode and address line 1; provider identity uses references, normalised phones,
emails and legal-name/company-number keys. Transaction identity includes kind
and category, so an invoice and its payment remain distinct.

The idempotent local upgrade preserves custom entity types, converts ticket
`location` to `location_detail`, links matching properties with `at`, and replaces
contractor assignments with providers while retaining `registered_as` companies.
Unknown legacy trades stay in review notes. Derived rules provide exact postcode
coverage, same-building links and recurring issues between tickets at the same
property; identical location text at different properties does not create a link.

Ownership shares, tenancy dates/lead-tenant flags and provider-contact roles are
validated relationship attributes. Ownership shares cannot exceed 100% in total,
and a ticket has one property. Generic writes cannot change derived balances,
merge transactions or alter ledger relationships. Canonical financial/provider
schemas require migrations rather than arbitrary registry edits.

## Ledger and reconciliation

Ledger writes append immutable economic records and recompute property balances
in the same atomic store mutation. Pending payment claims do not credit balances.
Cleared rent receipts settle oldest open charges, including partial payments,
and create management fees once. Expected contractor invoice charges do not
debit landlord funds until a payment is recorded. Deposits, deductions, returns,
landlord contributions/payouts, expenses, refunds and signed adjustments follow
validated category rules.

Corrections append reversing entries, including related fee reversals. Financial
fields remain unchanged; status only advances. Evidence/reference bindings may
accumulate and confidence may rise after bank confirmation. Writable corrections
use reversals rather than changing entries to `void`. Duplicate source claims and
bank lines preserve evidence without crediting money twice; distinct references
remain distinct. Unknown property assignments enter an idempotent unallocated
queue. Ambiguous receipts also remain there without a guessed category;
REST/MCP allocation requires explicit classification before creating a canonical entry. Arrears, unmatched payments and invoice overruns become graph issues.

Landlord balances and statements aggregate owned properties using `share_pct`.
Rent generation handles weekly/monthly/quarterly schedules, month-end dates and
tenancy bounds, with deterministic references preventing duplicate charges.

## Providers, prices and quotes

Recommendations match exact postcode districts, exclude suspended/do-not-use
providers and require current Gas Safe accreditation for gas work or NICEIC/NAPIT
for electrical work. Details show accreditation/insurance expiry warnings and
prices older than six months. Emergency ranking prioritises response time and
requires emergency callout; routine ranking considers preferred status/property
preference, observed quality, sourced prices and response time.

Metrics use actual ticket `first_visit_at`, `visits_count` and
`tenant_feedback_rating` observations. Scheduled appointments are not attendance;
missing observations remain unknown. Recorded expense payments determine spend,
with reversals cancelling their contribution. Quote acceptance atomically checks
expiry/qualification, assigns the provider and records an expected expense,
without moving money.

## Ingestion and source evidence

Bank CSV/OFX and supported text-layer PDFs, labelled invoices/receipts,
tenancy/rent schedules and email/call payment claims enter the existing
chunk/extract/resolve/embedding pipeline. Transactions and sourced prices retain
chunk spans and source-file links. Bank lines can confirm pending claims;
provider/property/tenant relationships help allocation. Financial ingestion uses
the same typed relationship validation as manual and MCP writes.

Local extraction is conservative and deterministic. Arbitrary document layouts,
scanned PDFs and ambiguous financial narratives need supplied parsed/OCR text,
explicit structured candidates or the configured extraction provider. Local
embeddings are deterministic hashed vectors; configured Claude/Vertex integrations
provide the external extraction/embedding paths.

## API, MCP, workflows and admin panel

Authenticated API routes expose properties, ledgers/balances, landlords,
transactions/status/reversals/settlements, unallocated candidates, providers,
offerings, quotes and statements. All agent tools remain on the API's **single
`/mcp` endpoint**, with session grants, validation and audit records; other
services expose no second MCP gateway.

Six version-1 skills are seeded in the graph: rent-arrears, reconcile-ledger,
contractor-invoice, landlord-statement, choose-provider and provider-research.
Workflow review flags skill-caused reversals as workflow issues. Defaults use a
three-day arrears grace period, email follow-up and a day-seven call; recorded
policy supplies further escalation and quote thresholds.

The admin panel includes property details/relationships, balance figures and
filtered ledgers with running balances/evidence; weighted landlord views and
statements; the read-only unallocated queue; and provider details, sourced prices,
metrics, expiry warnings and quotes. Graph transactions are hidden by default and
shown for a selected property. Statement PDFs are rendered, stored as source
files and downloadable; their stored document IDs can be used by the existing
email attachment flow.

## Scheduling and verification

`make dev` starts every implemented service with synthetic property, invoice,
bank, provider and skill fixtures. The local API accrues rent before readiness
and on each new London day, cancelling its scheduler task at shutdown. Terraform
adds the authenticated `propadmin-rent-daily` Cloud Scheduler job at 00:05
`Europe/London`, posting to rules `/internal/rent-schedule` with a service-account
OIDC token. Deployment retains the existing runtime gate.

The final local **`make check` passed: 68 backend tests and 16 frontend tests**,
plus lint, types, production build, generated API-contract checks, Terraform and
Compose validation. Focused scenarios cover ledger arithmetic/rollback,
reconciliation, reversals, identity/provenance, schema and relationship guards,
provider eligibility, quote acceptance, scheduling and authenticated API/MCP
boundaries. Native desktop and mobile UI QA passed. A focused coverage run measured 83%
across shared core/runtime (ledger 86%, providers 90%, statement PDFs 98%).

All four migrations were applied to temporary **SurrealDB 3.0.0**. Privileged-user
probes rejected financial edits, deletion, backward status moves, removed evidence,
overwritten references and lowered confidence, while accepting forward status
and appended provenance. Table permissions protect record users; events add
protection for system-user writes. Stored balance fields use update permissions
rather than literal `READONLY`, which would block privileged cache refreshes.

The local runtime uses the shared JSON store; SurrealDB migrations were verified
separately. Cloud deployment and live bank, extraction, embedding, browser,
email/voice integrations were not exercised by these checks. Bank-account
ownership, deposit custody and final escalation policies remain product decisions;
ledger account fields are labels, and no real payment movement is asserted.
