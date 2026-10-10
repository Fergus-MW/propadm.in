# Large synthetic ingestion portfolio

A connected, reproducible portfolio for the actual Propadmin ingestion API and
typed graph. It includes raw sources, structured CRM/ledger exports, relationship
imports and independent financial checks. All identities, addresses, commercial
details and accreditation numbers are fabricated. Contacts use `.example.test`.

## Default dataset

| Record or source | Count |
| --- | ---: |
| Properties | 120 |
| Tenants | 240 |
| Landlords | 30 |
| Contractor contact people | 36 |
| Service providers | 36 |
| Service offerings/prices | 108 |
| Maintenance tickets | 480 |
| Quotes | 480 |
| Supplied call transcripts with call records | 480 |
| EML messages | 1,000 |
| Tenancy documents | 120 |
| Monthly rent charges, May–October 2026 | 720 |
| Recorded opening deposits | 120 |
| Rent payment bank rows | 708 |
| Repair payment bank rows | 40 |
| Invoices | 80 |
| Unidentified OFX payments | 10 |
| **Total source files** | **3,288** |

The ledger also derives management fees. Amounts are integer GBP pence in typed
records and decimal GBP in the bank/source documents. Property balances are
computed by the platform; the generator does not seed derived balances or
contractor performance metrics.

The portfolio has partial/missing rent, shared owners, unresolved repairs,
completed repairs with and without a charge, disputed invoices, expired quotes,
withdrawn access consent, silent contractors, reopened faults, wrong-property
evidence and unverified instructions. Provider profiles include suspended firms,
expired qualifications/insurance and stale prices. These are valid input records
that the application must interpret, not malformed files or real credentials.

Sources use deterministic templates and varied identities, amounts and states.
This is a sizeable development dataset, not a representative sample of all
real-world language or a performance certification. It contains historical
outcomes known as of **10 October 2026 at 12:00 UTC**. Do not use the complete
histories as blind future-decision tests. Controlled decision-point evaluation
requires a separate harness that withholds later evidence.

## Files and relationships

```text
manifest.json
sources/
  directory/                     # agency, landlords, providers, contacts and prices
  properties/SYN-P0001/
    crm.json                     # known people/property records
    relationships.md             # authoritative CRM ownership/tenancy relationships
    tenancy.txt
    management-policy.md
    opening-ledger.json
    bank.csv
    repairs/REP-0001-1/
      ticket-and-quote.json
      intake.eml
      update.eml
      call.txt
      quote.md
      ...                        # invoice/approval where the history calls for them
import/
  directory.json
  SYN-P0001.json                 # ordered source payloads and declared relationships
evaluator-only/
  SYN-P0001.json                 # expected balances and integrity assertions
```

Ticket → property, quote → ticket/provider, provider → offering and known
tenant links are supported by the ingestion pipeline. Ownership, agency
management, extra tenants and provider contacts are imported as explicit CRM
relationships through `GraphService.link_entities`, with validation, audit
records and a source-document reference. They are not guessed from names.

The import indexes matter: call records and financial `source_type` values are
provided there. Uploading only the raw text without these fields does not create
the same structured portfolio. Evaluator files must stay outside an agent's
context and retrieval index.

## Rebuild or scale

From the platform repository root, using Python 3.12+:

This package is self-contained: it does not require the stress-test suite, testing
actors or other evaluation work. The checked-in ZIP contains the complete default
dataset. Extract it locally with:

```sh
python3 -m zipfile -e eval/portfolio/data/large-portfolio-001.zip .artifacts
python3 eval/portfolio_data.py validate --pack .artifacts/large-portfolio-001
```

Or regenerate it:

```sh
python3 eval/portfolio_data.py build --out .artifacts/my-large-portfolio
python3 eval/portfolio_data.py validate --pack .artifacts/my-large-portfolio
```

Default: 120 properties, seed `20261010`. Set `--properties 250` for 1,000 tickets,
or choose up to 1,000 properties. Change `--seed` to vary financial/provider data.
The catalogue remains 30 landlords and 36 providers; tenants, repairs and sources
scale with the property count. Existing destinations and `ANSWERS` paths are
refused. The same parameters produce identical source files and hashes.

## Load and verify against the platform

```sh
uv run --locked python eval/portfolio_data.py ingest \
  --pack .artifacts/my-large-portfolio \
  --platform-root . \
  --out .artifacts/my-portfolio-check --save-state
```

The default `sharded` mode ingests the directory once, then each property with its
required shared suppliers into a fresh isolated store. This verifies every source
and property while keeping checks practical for the current JSON repository.
Directory sources are reused across shards, so summing source counts from all
batches will exceed 3,288. Shard entity counts also must not be summed as unique
portfolio entity counts.

For several properties in **one shared database**, use:

```sh
uv run --locked python eval/portfolio_data.py ingest \
  --pack .artifacts/my-large-portfolio --platform-root . \
  --out .artifacts/my-combined-check --mode combined --save-state \
  --property SYN-P0001 --property SYN-P0002 --property SYN-P0005 \
  --property SYN-P0012 --property SYN-P0031
```

Omit all `--property` options to import the complete portfolio into one shared
store. That is supported by the importer, but whole-portfolio combined load time
has not been validated. The current snapshot-based repository repeatedly copies
and serialises growing state; a large combined import may be slow and use substantial
memory. Increasing source size does not establish production database scalability.

The importer executes authenticated `/v1/ingest/upload` routes in-process, uses
the actual domain services, and disables demo seeding and background scheduling.
It uses deterministic local extraction/embeddings and blocks normal outbound
HTTP. No live agent/model or external provider is called. It does not modify
normal `.data/state.json`, a running app or cloud storage.

With `--save-state`, each successful batch includes the actual `state.json`
snapshot and a `document-map.json`; snapshot reload through the platform's local
Store is verified. These snapshots contain the platform's normal records and can
be used as isolated development data. Keep a copy before starting a normal
`make dev` session against one: startup also seeds its built-in demo and starts
rent scheduling. There is no silent switch of the user's active database.

Checks include preserved source text/chunks, every ticket/property and quote
relationship, supplied ownership shares, tenant identities, expected financial
balances, unallocated payments and transaction evidence. Replaying CRM, intake
email and bank sources must leave the entire state unchanged. Errors are retained
per batch; one failed property does not hide the others.

The platform can generate historical arrears/workflow issues while importing
charges before later payments. The importer retains those records and checks
final balances; it does not claim to verify automatic issue closure. Domain
timestamps are supplied data, but the platform's clock is not frozen and the
loader does not exercise its background scheduler.

## Validation evidence

See [RESULTS.json](RESULTS.json) for the original full-dataset checks, pinned
platform revision and pack hash. The original code hashes predate the packaging
refactor. The underlying reports are included in [results/](results/).
See [PACKAGING_VALIDATION.json](PACKAGING_VALIDATION.json) for validation of this
self-contained package and its current code hashes. New local output goes under
`.artifacts/`.
All source files are plain text/JSON/EML/CSV/OFX. No PDF OCR, real audio, live-model
extraction, full UI run or operational-agent completion is claimed.

```sh
python3 -m unittest discover -s eval/portfolio/tests -v
uv run --locked ruff check eval/portfolio eval/portfolio_data.py
```

These are explicit ingestion checks; this commit does not change `make test` or
other platform checks. Generated stores and regenerated data stay under the
repository's existing ignored `.artifacts/` directory.
