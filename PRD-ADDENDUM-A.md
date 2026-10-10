# Addendum A — Properties, Ledgers and Service Providers

10 Oct 2026 · Fergus

## Summary

This addendum adds property as a canonical entity type and gives every property
its own transaction ledger: rent due and received, deposits, expenses, management
fees, landlord payouts and contributions, refunds and adjustments. Each
transaction is itself a canonical entity linked to its property and to the
people, companies, tickets, emails and source files behind it. The agent can
answer “what does this property owe and who paid what” from the graph.

It extends the main [PRD](PRD.md) and follows all its rules: fixed schemas in
the entity-type registry, every free-text field embedded, the same chunk →
extract → dedupe/merge/flatten → resolve pipeline, live graph changes, and a
fully autonomous agent.

Changes to the main specification:

- Canonical types: Person, Company, Ticket, Email, Call, Property,
  Service provider, Transaction, Service offering and Quote.
- A ticket’s free-text location becomes `ticket ->at-> property`; remaining
  flat/room text is `location_detail`.
- Emails, calls and chunks link to properties through `about` and `mentions`.
- The agent records ledger entries and reconciles/reports them. It never
  initiates payments or moves money.

## Property

A property is one lettable unit: a house or a single flat within a building.
Its fixed schema extends common canonical fields (`name`, `aliases`,
`description`, `external_ids`, `version`, etc.). Free text is embedded.

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| ref | unique string | | Internal reference; resolution key |
| address_line1, address_line2, city, postcode | string | | postcode + address_line1 resolution key |
| address_text | text | yes | Full address; fuzzy matching |
| unit_label | optional string | | e.g. Flat 3B |
| building_name | optional string | | Groups flats until a building entity exists |
| property_type | enum | | house, flat, maisonette, studio, room, commercial |
| bedrooms, bathrooms | int | | |
| status | enum | | let, vacant, void_works, off_market |
| rent_amount_minor | int | | Current rent in pence |
| rent_frequency | enum | | weekly, monthly, quarterly |
| rent_due_day | int | | Day of month or week |
| deposit_amount_minor | optional int | | |
| deposit_scheme_ref | optional string | | Protection scheme reference |
| management_fee_pct | optional decimal | | Percentage of rent received |
| tenancy_start, tenancy_end | optional date | | Current tenancy |
| features | text | yes | Boiler, appliances, parking |
| access_notes | text | yes | Keys, alarm, contractor parking |
| compliance_notes | text | yes | Gas safety, EICR, EPC dates/status |
| notes | array of text | yes | |
| tenant_balance_minor | int, derived/read-only | | Positive means arrears |
| deposit_held_minor | int, derived/read-only | | |
| landlord_balance_minor | int, derived/read-only | | Money held for landlord |

Edges:

- `person|company ->owns-> property`, with `share_pct` for joint owners.
- `person ->tenant_of-> property`, with `from`, `to`, `is_lead_tenant`.
- `company ->manages-> property`.
- `ticket ->at-> property`.
- `email|call ->about-> property`; `chunk ->mentions-> property`.
- `transaction ->for-> property`.

Default rules: `same_building` joins properties with the same building_name and
postcode. `recurring_issue` uses the `at` property edge rather than location text.

## Service providers

A `service_provider` is a trade or firm used to fix or maintain properties.
Services/prices are separate `service_offering` entities, and quotes are `quote`
entities. The graph must answer which roofers cover E1, can attend this week,
and what they charge for gutter repairs.

Supported trades: plumbing, heating/gas, electrical, roofing, guttering,
drainage, carpentry, locksmith, glazing, damp/mould, pest control, appliance
repair, decorating, plastering, flooring, cleaning, gardening, handyman,
general building.

| Provider field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| ref | unique string | | Internal reference |
| trading_name, legal_name | string | | legal_name + company_number resolution key |
| business_type | enum | | sole trader, partnership, limited company |
| company_number, vat_number | optional string | | Companies House and VAT identifiers |
| trades | array of enum | | Supported trades above |
| description | text | yes | Services in provider’s or our words |
| phone_main, phone_emergency | string | | E.164 resolution keys |
| emails | array of string | | Resolution keys |
| website, portal_url | optional string | | Portal can link to stored browser credential |
| address, service_area | text | yes | e.g. East London and Essex |
| postcode_districts | array of string | | Normalised E1, E2, IG1 |
| working_hours | text | yes | e.g. Mon–Fri 8–6, Sat mornings |
| emergency_callout | bool | | Out-of-hours/24-hour service |
| typical_response_hours | optional int | | Stated or observed attendance time |
| booking_method | enum | | phone, email, portal, app |
| booking_instructions | text | yes | Contact, lead time and booking procedure |
| accreditations | array of object | | scheme, number, expires_on; Gas Safe/NICEIC/NAPIT/TrustMark/CSCS/other |
| insurance_public_liability_minor | optional int | | Cover in pence |
| insurance_expires_on | optional date | | |
| payment_terms | text | yes | e.g. 30 days from invoice |
| preferred_payment_method | optional enum | | bank transfer, card, cheque |
| status | enum | | preferred, approved, trial, suspended, do_not_use |
| status_reason | text | yes | Reason for status |
| notes | array of text | yes | |
| jobs_completed | derived int | | Closed/resolved tickets |
| avg_response_hours | derived optional decimal | | Reported to first visit |
| first_time_fix_rate | derived optional decimal | | Tickets resolved in one visit |
| avg_job_cost_minor | derived optional int | | Ledger expenses |
| rating | derived optional decimal | | 1–5 from outcomes/tenant feedback |

Bank details are not stored in the graph. Payments happen outside the system.

### Service offering

One entity per service offered by a provider at a given price.

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| name | text | yes | e.g. Annual boiler service |
| trade | enum | | Supported provider trades |
| description | text | yes | Scope, inclusions/exclusions |
| pricing_model | enum | | fixed, hourly, day rate, call-out + hourly, per unit, quote only |
| price_minor | optional int | | Fixed/per-unit price in pence |
| unit | optional string | | per metre/window |
| callout_fee_minor, hourly_rate_minor, day_rate_minor, min_charge_minor | optional int | | |
| out_of_hours_multiplier | optional decimal | | e.g. 1.5 |
| vat_included | bool | | |
| typical_duration_hours | optional decimal | | |
| price_source | enum | | website, quote, invoice, call, email, admin |
| valid_from, last_confirmed_at | date | | Recheck stale prices |

### Quote

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| ref | optional string | | Provider quote number |
| amount_minor | int | | Total pence |
| vat_included | bool | | |
| scope, exclusions | text | yes | |
| earliest_start, valid_until | optional date | | |
| status | enum | | requested, received, accepted, declined, expired |

Provider edges:

- `service_provider ->offers-> service_offering`.
- `service_provider ->contact-> person`, role owner/office/engineer.
- `service_provider ->registered_as-> company` when a company exists.
- `service_provider ->covers-> property`, derived from postcode districts;
  `preferred_for` is manually set by admins or agents.
- `ticket ->assigned_to-> service_provider`, replacing company assignment.
- `quote ->from-> service_provider`, `quote ->for-> ticket`,
  `quote ->accepted_as-> transaction`.
- `transaction ->paid_to-> service_provider` for expenses.
- `email|call ->about-> service_provider`; `chunk ->mentions-> service_provider`;
  `service_offering ->evidenced_by-> chunk` for price evidence.

Providers, services and prices come from emails, calls, invoices, browser-read
websites and admin edits through the normal ingestion/resolution pipeline.
Haiku 5.5 extracts candidates; phone, email, company number and name deduplicate
them. Derived metrics refresh whenever a linked ticket closes or an expense
is recorded.

## Transaction ledger

Every property ledger is its linked transaction entities. Economic entries are
append-only: mistakes require reversing entries, never edits or deletion.
Amounts are positive integer GBP pence; category determines signed effects.

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| ref | unique string | | Generated TX-2026-000123 |
| external_ref | optional string | | Bank/invoice/receipt ref; key with amount/date |
| kind | enum | | charge, payment, transfer, adjustment |
| category | enum | | Effects below |
| amount_minor | int > 0 | | Pence |
| currency | enum | | GBP |
| effective_date | date | | Occurrence/due date |
| period_start, period_end | optional date | | Covered rent period |
| status | enum | | expected, pending, cleared, reconciled, void |
| payment_method | optional enum | | bank transfer, standing order, direct debit, card, cash, cheque |
| bank_account | optional string | | Account label, not bank credentials/details |
| counterparty_name | string | | As on bank statement/invoice |
| description | text | yes | Statement/invoice description |
| notes | array of text | yes | |
| recorded_by | enum + ref | | ingestion, agent session, admin |
| confidence | float | | 1.0 bank-sourced; lower email claims |

Transaction edges: `for` exactly one property; `paid_by` person/company;
`paid_to` person/company/provider; `for_ticket` ticket; `settles` transaction;
`reverses` transaction; `evidenced_by` chunk; `derived_from` source_file.

### Category effects

| Category | Kind | Tenant | Landlord | Deposit | Example |
| --- | --- | --- | --- | --- | --- |
| rent_due | charge | + | | | Scheduled rent |
| rent_received | payment in | − | + | | Tenant standing order |
| tenant_recharge | charge | + | | | Damage/lost keys |
| deposit_received | payment in | | | + | Move-in deposit |
| deposit_deduction | transfer | | + | − | Agreed move-out deduction |
| deposit_returned | payment out | | | − | Tenant deposit refund |
| management_fee | charge | | − | | Fee on rent received |
| expense | payment out | | − | | Contractor repair |
| service_charge, ground_rent | payment out | | − | | Freeholder |
| utility, council_tax | payment out | | − | | Voids |
| insurance, compliance | payment out | | − | | Insurance/gas safety/EICR |
| landlord_contribution | payment in | | + | | Landlord repair top-up |
| landlord_payout | payment out | | − | | Monthly remittance |
| refund | payment out | + | | | Tenant overpayment refund |
| adjustment | adjustment | ± | ± | ± | Explicit correction; reason in notes |

Rules:

- Daily Cloud Scheduler → rules generates `rent_due` from each let property’s
  rent amount/frequency/due day.
- Derived balances sum non-void transactions and refresh inside the same
  database transaction as every ledger write; no manually entered balances.
- Reverse a wrong entry using the same amount/category, retain both, then
  append the correct entry.
- Recording `rent_received` automatically creates the property’s percentage
  management fee.
- Landlord position is a query across `owns` edges weighted by `share_pct`;
  there is no separate landlord ledger.
- Rent due raises arrears; rent received reduces them and credits landlord
  funds; fees/expenses/payouts debit landlord funds. Deposits are separate.

### Ingestion and reconciliation

Each source is chunked, embedded, extracted and resolved with provenance before
canonical graph writes.

| Source | Parsing | Result |
| --- | --- | --- |
| Bank statement CSV, OFX, PDF | One row per line | Payment per line, confidence 1.0 |
| Contractor invoice PDF/email attachment | Invoice fields/line items | Expense charge linked to provider/ticket |
| Receipt/remittance advice | Amount/date/payer/ref | Payment or more evidence on existing payment |
| Rent schedule/tenancy agreement | Rent/frequency/due day/deposit/dates | Property fields and tenant_of |
| Money mentioned in email/call | Extracted claim | Low-confidence pending payment until bank confirmation |

Deduplicate transaction candidates by external_ref, then amount/date within
three days/counterparty, then Haiku tie-break. Bank, email and call evidence
can describe the same transaction.

Reconcile after every ledger write:

1. Assign property via reference, tenant/owner, invoice or ticket. Ambiguous
   lines go to an unallocated queue worked by the agent.
2. Match rent payments against oldest open rent charges; contractor payments
   against invoices. Partial payments leave remainder open.
3. Promote claims to cleared when bank-confirmed and reconciled when matched.
4. Flag overdue rent, payments without charges, and invoices above ticket cost
   estimates as entities for the agent.

## Agent tools and skills

All graph/ledger/provider tools use the existing single sandboxed MCP endpoint.
There is no money-sending tool.

| Tool | Purpose |
| --- | --- |
| get_property(ref or id) | Owners, tenants, open tickets, balances |
| get_ledger(property, from?, to?, category?) | Date-ordered transactions/running balances |
| get_balances(property or landlord) | Property balances or weighted owned properties |
| record_transaction(...) | Validate and append evidence-backed entry |
| reverse_transaction(tx, reason) | Append reversal |
| allocate(tx, property), settle(payment, charge) | Unallocated assignment/manual matching |
| generate_statement(property or landlord, period) | PDF stored as source_file, emailable |
| find_providers(trade, property or postcode, urgency?, service?) | Rank coverage/status/emergency/response/outcomes/prices |
| get_provider(id) | Offers, prices, contacts, accreditation, jobs, spend |
| upsert_provider(...), upsert_offering(...) | Provenance-backed provider/price edits |
| record_quote(provider, ticket, ...), accept_quote(quote) | Quote lifecycle; assign/record expected expense |
| set_provider_status(provider, status, reason) | Preferred/suspended/do_not_use with reason |

New skills are stored and versioned in the graph with workflow issues/proposals:

- **rent-arrears:** check pending claims after grace period, email then call
  tenant, log promises, schedule follow-ups, escalate per policy.
- **reconcile-ledger:** assign queued entries, settle charges, chase evidence.
- **contractor-invoice:** compare invoice scope/cost/completion with ticket,
  record expense, flag overruns.
- **landlord-statement:** monthly landlord statements/remittance figures.
- **choose-provider:** emergency response first; routine price/rating/fix rate;
  seek 2–3 quotes above threshold; never suspended/do_not_use; valid Gas Safe
  for gas and NICEIC/NAPIT for electrical.
- **provider-research:** research missing coverage or prices older than six
  months with browser; save prices with `price_source=website`.
- Workflow review flags ledger corrections caused by following a skill as an
  issue on that skill.

## Admin panel, API and schema

- Property page: schema fields, owners/tenants/managing company, tickets,
  emails/calls, three balances, period/category ledger filters, running
  balances and source evidence on every row.
- Landlord view: owned properties, combined balances and statements.
- Unallocated queue is read-only for admins; agents work it.
- Properties/transactions have graph colours; transactions hidden by default,
  shown for an individual property on demand.
- Provider directory filters trade/area/status/rating. Details show offers,
  prices with sources/confirmation dates, contacts, accreditation/insurance
  expiry warnings, quotes, assigned tickets and ledger spend.
- API routes (under existing `/v1` prefix): GET `/properties`,
  `/properties/{id}`, `/properties/{id}/ledger`, `/properties/{id}/balances`;
  POST `/transactions`, `/transactions/{id}/reverse`; GET
  `/landlords/{id}/statement?period=`. Expose the same operations through MCP.
- SurrealDB 3.x strict tables: property, transaction, service_provider,
  service_offering, quote. Unique property/provider/transaction refs;
  address and external_ref/amount/date indexes; provider coverage index.
- Typed relations: `for` transaction→property; `settles`, `reverses`
  transaction→transaction; `owns` person/company→property; `tenant_of`
  person→property; `at` ticket→property; `offers` provider→offering;
  `assigned_to` ticket→provider.
- Verify SurrealDB 3.x append-only syntax during the schema spike. Ordinary
  update/delete permissions are denied; dedicated API status transitions only
  move forwards. Derived fields are protected against direct edits.

## Implementation tasks

Implemented in the local build; verification boundaries are recorded in
[the implementation notes](docs/ADDENDUM-A-IMPLEMENTATION.md). These extend the
main phases after ingestion works:

- [x] Registry/migrations, append-only enforcement and derived balances.
- [x] Ticket property edges and backfill from location text.
- [x] CSV/OFX/PDF bank/invoice/receipt parsers and candidate deduplication.
- [x] Daily rent scheduler and automatic fees.
- [x] Property assignment, partial settlement, status promotion and flags.
- [x] MCP ledger tools and graph-versioned skills at version 1.
- [x] Property/landlord pages, statements and graph node types.
- [x] Provider/offering/quote registry; migrate contractors with registered_as.
- [x] Provider extraction, metrics and postcode coverage.
- [x] Provider ranking, quotes and provider selection/research skills.
- [x] Provider UI and accreditation/insurance expiry warnings.

## Open questions

- Does the synthetic environment include bank statements, and in what format?
- One client bank account for all properties or one per landlord?
- Deposits held by us or only referenced to a protection scheme?
- Arrears policy: default three-day grace; email then call at day seven.
- Is a property a whole building with units? Add a building type later rather
  than overloading the single-unit property definition.

## Local implementation decisions

Until the open questions are resolved, synthetic CSV and OFX bank fixtures use
one labelled client account; deposits are balances held separately with optional
scheme references; properties are single units. No real bank account details
are stored. Monetary adjustments include explicit signed balance deltas.
Invoice charges represent expected liabilities; confirmed payments debit
landlord funds. Pending claims do not count as received funds. The economic
entry stays immutable when evidence/status is promoted through reconciliation.
Unallocated entries are staged candidates until the required property link can
be established. These decisions preserve the financial meaning of the category
table while avoiding double-counting invoices and their settlement payments.
