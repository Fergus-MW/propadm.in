# Historical workflow evaluation

The tooling imports each case's `index.md`, `history.md` and attachments into the
production graph through the API's single `/mcp` gateway. It refuses local API URLs
and APIs whose settings aren't in cloud mode. No local database is opened.

Production uses the SurrealDB repository adapter. The registry and generated SurrealDB
migrations describe the application ontology; do not apply those migrations locally for
this workflow. The adapter persists graph records and embeddings as application records;
it does not yet query native SurrealDB vector/image indexes. Original binary files are
private GCS objects (`RAW_BUCKET`, falling back to `STATE_BUCKET`).
Source records retain raw hashes, base64, parsed text, model input content blocks and
token usage. Anthropic does not expose internal image token IDs. Image descriptions
are embedded text; they are not native image-vector embeddings.

Triplet boundaries are deterministic Python sliding windows: `[1,2,3]`, `[2,3,4]`,
through `[N-2,N-1,N]`. The 50 cases produce 1,405 triplets. Haiku sees only one
three-step window per metadata request. Every action, decision, insight, constraint,
approval, commitment, open question, escalation, completion or financial item cites
an exact quote and step; unsupported categories are absent and inferences are labelled.
Participants, channels, skills, workflow stage and extraction provenance are retained.
Full windows and their first-two-step contexts have separate Vertex `text-embedding-005`
768-dimensional vectors. The general graph index still uses its configured hash vectors.
`search_workflow_examples` ranks only context vectors/text and returns the observed third
step and metadata. Holdout cases and all revisions of the current case are excluded.
`GET /v1/workflow-triplets/status` reports expected window counts and verifies both
persisted vectors per window. Re-enrichment repairs missing vectors without rerunning
metadata extraction or changing the original metadata.

The corpus contains 50 cases, 1,505 events and 16 PDF attachments. Case revisions
are immutable and checksummed. Events have exact source spans, stable ordinals,
channel, sender/recipient, timestamps and attachment references. Every adjacent pair
is a transition. Incoming tenant/landlord/provider replies are observations rather
than agent predictions; replay supplies them before subsequent controllable actions.

An evaluation snapshots the historical prefix through step N, current skill versions
and attachments first referenced by then. End-of-case summaries/outcomes, full-history
documents, later attachments, other cases' full histories and answer keys cannot be retrieved through
its MCP session. Graph edits occur only in the evaluation's production-persisted sandbox;
communications and scheduling are captured without executing external actions. The
existing Sonnet production agent definition runs the actual session. It returns one
next event; Haiku compares it with recorded step N+1.
The replay also snapshots the five retrieved training-case triplets. Only these permitted
examples can be searched through its MCP session; their IDs and model are in the hashed context.
Replay v2 supplies a synthetic evidence container without an invented case reference or
default "reported" status. The agent derives the workflow phase from the prefix.
The context hash covers the prompt, supplied ticket fields and skill-version snapshot.
Earlier evaluation records remain unchanged and retain their earlier prompt/setup.

The supplied synthetic PDF appendices (Observations/Findings/Conclusions) contain
retrospective commentary. Replay exposes the preceding primary document text with
fresh chunks, and excludes original byte/object access; the main graph retains everything.

Haiku scores action (35%), grounded facts (25%), recipient/channel (15%), sequence (15%)
and communication (10%). Passing requires >=80 with no critical fabrication or unsafe
action. Expected/actual steps, scores, differences, explanation, provider/model IDs,
context hash, skill versions and token usage are stored as linked graph records.
Run/model failures are not successful grades. This measures next-action reproduction
in dry-run historical context; it doesn't verify live email delivery or contractor work.

Cases are split deterministically by case reference: 42 training and 8 holdout.
Skill publication rejects holdout evidence and records `learned_from` links on immutable
versions. Use holdout cases for the evaluation baseline; training replays are diagnostics.
With a concurrent tuner, each replay records its own skill-version snapshot. If that
tuner learns from the reserved cases, those cases become diagnostics; an independent
benchmark then needs fresh reserved cases and a fixed skill version.

Set `PROPADMIN_ADMIN_TOKEN` or `PROPADMIN_ADMIN_PASSWORD` using your production
credentials, and set the explicit production URL in each command:

```sh
uv run python -m eval.workflows import --api-url https://api.withproperly.com
uv run python -m eval.workflows publish-skills --api-url https://api.withproperly.com
uv run python -m eval.workflows.triplets --api-url https://api.withproperly.com
uv run python -m eval.workflows evaluate --api-url https://api.withproperly.com --after-step 12
```

Use `--case-ref 012 --split training --after-step 12 --limit 1` for the specific
12-to-13 diagnostic. `--limit 0` runs all matching controllable transitions.
Each run has a finite timeout (default 300 seconds); the runner requests cancellation
on timeout. Import receipts go in `.artifacts/workflow-corpus.json`. Reads, sync and
idempotent grading retry transient failures. An ambiguous run submission recovers the
already-created session from its evaluation record; it never blindly submits twice.
If no run is recorded, the runner stops and prints the prepared evaluation ID for inspection.

PDF and image inputs share the production ingestion parser across incoming AgentMail
attachments and admin uploads. PDFs use their text layer, with Claude transcription for
scanned/mixed pages. Images support JPEG, PNG, GIF and WebP. The parser retains originals,
embeds natural-language descriptions and exposes provider failures. Limits: 5 MB per
binary file, 250 pages for text PDFs, 100 pages for the vision fallback.

Validation (memory-only stores, no local database):

```sh
uv run --no-sync pytest tests/test_workflow_replay.py tests/test_media_ingress.py
uv run --no-sync pytest tests/test_agent.py tests/test_email.py tests/test_mcp.py packages/core/tests/test_financial_ingestion.py
```
