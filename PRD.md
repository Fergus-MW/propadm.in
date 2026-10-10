# Propadmin product requirements

Problem
Operational knowledge is scattered across calls, inboxes, documents and the CRM. Nobody has one view of who a customer is, what was promised, and what changed. Agents can't act reliably without that view.
Users
- Operator (sales, account, ops lead): asks questions, watches agent work and can step in; never asked to approve anything.
- Admin / analyst: defines entity schemas and edge criteria, tunes extraction.
- Agents: read the graph, run code in sandboxes, draft emails, update records, place calls.
Goals
1. Every source item is ingested, linked to the canonical entities it mentions, and traceable back to its source span.
2. Canonical entities are deduplicated (one "Acme Ltd" no matter how many spellings).
3. Admins define edges between entities by rules, and the graph updates when data or rules change.
4. Every free-text field is embedded and searchable; queries combine vector, full-text and graph traversal.
5. Agents complete multi-step tasks in isolated sandboxes, including outbound voice calls, with a full audit trail.
Non-goals (v1)
- Real-time sync with production systems (we ingest the synthetic environment).
- Fine-tuning models.
- Mobile app.
Functional requirements
| ID | Requirement | Priority |
| --- | --- | --- |
| F1 | Ingest emails, call audio/transcripts, documents (PDF, DOCX, MD) and CRM records from the synthetic environment | P0 |
| F2 | Store every source file in the graph as a source_file (raw file in GCS), split into embedded chunks linked to the file and to the primary entities they mention | P0 |
| F3 | LLM extraction of entities, mentions and typed metadata per document, with confidence and source span | P0 |
| F4 | Entity resolution: match mentions to canonical entities (exact keys, then embedding + LLM adjudication) | P0 |
| F5 | Canonical entity types with a fixed schema (typed fields) plus a free-text description | P0 |
| F6 | Embed every free-text field (entity descriptions, document chunks, metadata values, notes, transcripts) | P0 |
| F7 | Edge criteria: admin writes a rule in plain English or builds it in the UI; both produce an editable rule with preview, toggle and versioning | P0 |
| F8 | Hybrid search API: vector + BM25 + graph expansion, with source citations | P0 |
| F9 | Agents run on Claude Managed Agents with custom tools over the graph; every tool call logged | P0 |
| F10 | Outbound phone call by an agent via ElevenLabs; transcript ingested back as a source document | P0 |
| F11 | Next.js UI: graph explorer that updates in real time as data and edges change, entity page, document viewer, edge-rule editor, agent console, call log | P0 |
| F12 | Inbound calls answered by an ElevenLabs agent with graph context looked up by caller number | P0 |
| F13 | Full autonomy: no human approval step for any action (calls, emails, browser, graph writes); every action logged per session | P1 |
| F14 | Entity merge/split UI with history | P1 |
| F15 | Temporal validity on edges and fields (valid_from / valid_to) | P2 |

Success metrics
- Entity resolution checked without labelling: ≥ 95% of mentions that carry a hard key (email, phone, domain, CRM id) resolve to the CRM entity holding that key, and < 2% of canonical entities flagged as likely duplicates by the nightly similarity check.
- Hybrid search p95 latency < 500 ms at demo data volume.
- Rule change to updated edges in < 60 s for the full dataset.
- An agent completes the track's headline task end-to-end, including a call, without manual data fixes.
- A write to SurrealDB (new entity, edge or merge) appears in an open graph explorer within 2 s.
- Idle cost near zero: every Cloud Run service at zero instances when unused.
Tech stack
Everything we run is serverless on GCP Cloud Run, scales to zero with cold starts, and is provisioned with Terraform; the only third-party runtime services are ElevenLabs, the model APIs and (if chosen) the sandbox provider.
| Layer | Choice | Status | Notes |
| --- | --- | --- | --- |
| Admin panel | Next.js (App Router), TypeScript, Tailwind, shadcn/ui | Decided | Server components for data pages; client components for graph explorer |
| Frontend data | TanStack Query + generated OpenAPI client (orval or openapi-ts) | Proposed | Types generated from FastAPI's OpenAPI schema |
| Graph visualisation | cosmos.gl (GPU force layout + WebGL rendering) | Decided | Open-source engine only, not the Cosmograph library (CC-BY-NC). See "Graph explorer" below |
| Live updates | FastAPI Server-Sent Events (live graph deltas, agent runs, ingestion progress, calls, emails) | Proposed | Fed by SurrealDB LIVE queries + CHANGEFEED for replay on reconnect |
| Backend services | FastAPI, Python 3.12, Pydantic v2, uv | Decided | api, ingestion, rules, voice, email share packages/core |
| Messaging | Pub/Sub topics per pipeline stage and for agent wake events, dead-letter topics; Cloud Tasks for agent sleeps and scheduled self-invocations | Proposed |  |
| Database | SurrealDB 3.x (graph + document + vector + full-text) | Decided | 3.1 adds DiskANN alongside HNSW (source) |
| DB hosting | Surreal Cloud (managed; free Start instance to begin) | Proposed | Nothing for us to run; runs on AWS, not GCP |
| Object storage | Google Cloud Storage | Decided | Raw files, call audio, email attachments, agent artefacts |
| Agents + sandbox | Claude Managed Agents running Claude Sonnet 5.5, Anthropic-hosted sandbox; tools (email, phone, CRM, tickets, graph) reached over MCP on api | Decided | Runs on the Claude API, beta header managed-agents-2026-04-01 (docs) |
| LLM (pipelines) | Claude Haiku 5.5 for every pipeline: extraction, entity-resolution tie-breaks, entity descriptions, plain-English rule compiler | Decided | Claude API, or Vertex AI to use GCP credits |
| Embeddings | Vertex gemini-embedding-001, one fixed dimension (e.g. 1536) for all fields | Proposed | Single model = one vector space across entities, chunks, metadata |
| Document parsing | Docling (PDF/DOCX → structured text) | Proposed | LLM vision fallback for scans |
| Transcription | ElevenLabs Scribe for any raw call audio | Proposed | ElevenLabs calls already return transcripts |
| Voice | ElevenLabs Agents, inbound + outbound; existing number via Vonage SIP trunk | Decided | See "Voice" |
| Email | AgentMail: API-created inboxes, send/reply, inbound webhooks, custom domain | Decided | Python SDK agentmail; see "Email" |
| DNS | Cloud DNS zone for withproperly.com (registrar stays GoDaddy, nameservers point to Cloud DNS) | Proposed |  |
| Auth | Single shared admin password (Secret Manager); internal service token between services | Proposed | No SSO or compliance work |
| Secrets | Secret Manager | Decided |  |
| Observability | Cloud Run's built-in Cloud Logging only | Proposed |  |
| CI/CD | Cloud Build triggers → Artifact Registry → Cloud Run; GitHub connected via Cloud Build repository connection | Decided | Plan on PR, deploy on merge to main |
| IaC | Terraform, GCS remote state; bootstrap stack creates the GCP project | Decided | Modules listed under Infrastructure |

Graph explorer (cosmos.gl)
The admin panel's graph explorer uses cosmos.gl, the open-source GPU engine (OpenJS Foundation), as already chosen for Propadmin in DEV-836. The higher-level Cosmograph library is CC-BY-NC and off-limits commercially. We carry over what DEV-934 taught us, where the default cosmos view collapsed the Corten graph to a sub-pixel dot:
- Initial camera: fit to percentile bounds of the main component once the simulation settles, never min/max of all points and never fitViewOnInit before positions are set.
- Layout: store x/y per entity, computed in the rules service after edge recompute, so loads are instant and stable; cosmos simulation only refines. Tune repulsion and link distance so satellites don't blow out the bounds.
- Transport: binary (Float32 positions, Uint32 edge pairs) from a dedicated /entities/graph.bin endpoint, not multi-MB JSON.
- States: an error or timeout gets its own screen with a retry, never the "graph is empty" view.
- Performance: cap pixelRatio, hide labels during pan/zoom, label only on-screen high-degree nodes, colour by entity type and edge rule.
- Interaction: click a node → entity panel (fields, evidence, sources); filter by entity type, edge rule and date; search zooms to a node.
Real-time updates
The graph updates live as ingestion, entity resolution, edge rules, calls, emails and agents write to SurrealDB; nobody refreshes the page.
1. Source of change: every entity and edge table is defined with a SurrealDB CHANGEFEED; the api holds LIVE SELECT subscriptions on entity tables, relation tables and edge_rule.
2. Fan-out: api turns each change into a small delta (node_added, node_updated, node_merged, edge_added, edge_removed) with a monotonically increasing version, and streams it over SSE on GET /entities/graph/stream, filtered to the viewer's current filters.
3. Batching: deltas are coalesced every ~250 ms so a rule recompute that writes thousands of edges arrives as one batch, not thousands of renders.
4. Client apply: the explorer keeps its own typed arrays and applies each batch in place: new nodes are seeded at the centroid of their linked neighbours (or their stored server position), then the cosmos simulation is briefly reheated locally. The camera never refits on updates, so the view doesn't jump.
5. Visibility: new or changed nodes and edges pulse for a few seconds; a counter shows "N updates" with a toggle to pause live mode while someone is inspecting.
6. Reconnect: the client resumes with ?since=<version>; the server replays from the changefeed, or tells the client to reload the snapshot if the gap is too old.
7. Merges: an entity merge sends node_merged (old id → new id) so edges are re-pointed rather than the node vanishing.
Sandboxed agent
Decision: Claude Managed Agents with the Anthropic-hosted sandbox. Anthropic runs the agent loop, sessions and sandbox, so we run no worker. Our tools (graph, tickets, email, phone, CRM) are exposed as an MCP server on api that Anthropic's MCP connector calls over HTTPS (docs); api scales to zero between calls.
Models: the sandboxed agent runs on Claude Sonnet 5.5; it is the only component with access to email, phone, CRM writes and code execution. Every pipeline (ingestion extraction, entity resolution, description generation, the rules compiler) runs on Claude Haiku 5.5. Model ids live in config, not code, so either can be swapped without a deploy.
One agent, many parallel sessions
There is exactly one sandboxed agent: a single Managed Agents agent definition (Sonnet 5.5, one system prompt, every skill, every tool). It does everything itself: phone calls, browser use, email, tickets, CRM, graph reads and writes, code, plans and sleeps. The voice, email and browser services are thin adapters that give the agent those capabilities; they are not separate agents. Work runs as sessions of that one agent, one per task, many in parallel, each with its own sandbox, plan, browser session and wake-ups.
- What starts a session: a new ticket, an inbound email or call that doesn't belong to a running session, a scheduled invocation, or an operator in the admin panel. The agent service creates the session with the triggering context.
- Routing to an existing session: each session owns a set of subjects (ticket ids, email thread ids, call ids). An event about a subject that a live or sleeping session owns wakes that session instead of starting a new one, so one ticket never has two sessions working it.
- Concurrency limit: a configurable cap on parallel active sessions (default 20). Extra triggers queue in Cloud Tasks and start as slots free up; sleeping sessions don't count against the cap.
- Safe shared writes: graph writes use optimistic concurrency (each entity carries a version; a stale write is rejected and the agent re-reads), and claim(subject) / release(subject) record which session owns a ticket or thread.
- Visibility: the admin panel's agent console lists every session (running, sleeping, queued, done) with its plan, owned subjects and next wake-up.
Phone calls stay inside the same agent. Live speech needs sub-second turns, which a Managed Agents session can't give, so ElevenLabs carries the real-time audio loop. To keep it one agent: the session places the call with place_call(objective, brief); the ElevenLabs agent is configured with Claude Sonnet 5.5 as its LLM and the same core instructions; its server tools call back into the same session's tools (graph, ticket, plan) via voice; when the call ends, the transcript and outcome return to the session, which wakes and carries on with its plan. Inbound calls start or wake a session the same way. The session is the brain; the phone line is one of its tools.
The sandbox never holds database credentials: the MCP endpoint takes a bearer token issued per session. Other options we considered are below.
Option
Isolation
Session / persistence
Fit with GCP + Terraform
E2B
Firecracker microVM
1 h Hobby / 24 h Pro; pause keeps FS + memory
Hosted SaaS; BYOC in our GCP VPC (enterprise) or self-host via their Terraform
GKE Agent Sandbox
gVisor on GKE
Pod-per-sandbox; snapshots and Filestore volumes
Fully in our project and Terraform; more ops work
Modal Sandboxes
gVisor
24 h max; snapshots expire after 7 days
Hosted only; strong for GPU or heavy Python
Daytona
Container or VM
No cap; FS kept across stop/start
Hosted; self-host possible
Vercel Sandbox
Firecracker microVM
45 min Hobby / 24 h Pro; FS snapshot on stop
Hosted; natural only if frontend moves to Vercel
Claude Managed Agents
Anthropic-hosted sandbox
Managed by Anthropic
Least code, least control; agent loop runs outside our infra
Sandbox comparison data from fly.io's provider comparison.
Agent design
- Session: the agent service creates a Managed Agents session per task and relays its events to the admin panel over SSE while someone is watching; the session itself runs at Anthropic either way. The transcript and tool calls are saved as an agent_run record.
- Tools (MCP on api), grouped:
  - Graph read: search (hybrid), get_entity, traverse, get_document, query_graph (read-only SurrealQL)
  - Graph write: upsert_entity, update_entity, link_entities, unlink_entities, merge_entities, add_note
  - Tickets: create_ticket, update_ticket
  - Comms: send_email, reply_email, place_call, update_crm_record. Browser: browser_open, browser_act, browser_extract, browser_login, browser_screenshot, browser_close. Plans: create_plan, get_plan, update_step, add_step, revise_plan. Skills: get_skill, list_workflow_issues, report_workflow_issue, propose_skill_change
  - Time: sleep, schedule_invocation, cancel_invocation
- The built-in toolset (bash, files) handles agent-written code inside the sandbox.
- Autonomy: no approval step anywhere. The agent sends emails, places calls, books contractors, uses the browser and writes to the graph on its own; every action is logged with its session and stated reason.
- Limits to design for: tools are declared on the agent (redeclare on change, done by the deploy pipeline); max 128 tools; tool input_schema can't use $ref or top-level oneOf/anyOf/allOf.
Knowledge graph read and write
Agents read and write the same graph as everything else, always through api so every write is validated against the entity-type registry and recorded.
- Reads: hybrid search, entity lookup, n-hop traversal, document fetch, and read-only SurrealQL for anything else (write statements rejected).
- Writes: create or update entities (typed fields validated against the schema), add or remove manual edges, merge duplicates, attach notes. Agents cannot delete rule-generated edges or edit edge rules; those stay admin-only.
- Provenance: every agent write carries actor = agent_run:<id> and the reason the agent gave, is stored in a change_log with the previous value (one-click undo in the admin panel), and is ingested like any other source so its free text is embedded.
- Live: agent writes flow through the same change stream, so they appear in the live graph explorer immediately and trigger incremental edge-rule evaluation.
Sleeps, wake-up callbacks and scheduled invocations
Agents can pause and come back later without holding anything open, which fits scale-to-zero.
Tool
What it does
Limit
sleep(seconds, wake_on, reason)
Ends the agent's turn and pauses the task. It wakes when any wake_on event fires (email reply on a thread, call ended, ticket updated, entity changed) or when the timer runs out, whichever comes first
Mandatory 10-minute timeout: seconds is capped at 600; a sleep with no timer gets 600. The agent always wakes within 10 minutes
schedule_invocation(at, instructions, context)
Schedules a future self-invocation (e.g. "tomorrow 9am, check the contractor attended")
Any time up to 30 days ahead
cancel_invocation(id)
Cancels a scheduled invocation

How it works:
1. sleep and schedule_invocation write a wakeup record (agent_run, due_at, wake_on filters, reason, status) and create a Cloud Tasks task that calls agent /wake/{id} at due_at (serverless, nothing runs while waiting).
2. Event callbacks: email, voice, ingestion and the graph change stream publish events to Pub/Sub; agent matches them against pending wakeups (by thread id, call id, ticket or entity id) and wakes the task early, deleting its Cloud Task.
3. On wake, agent sends a message into the same Managed Agents session saying why it woke ("timer expired after 10 min" or "email reply received on thread X") with the new data; if that session has ended, it starts a new one seeded with the run's summary and context.
4. Wakeups are idempotent (status checked before resuming) so a timer and an event racing each other wake the agent once.
5. The admin panel shows each run's pending wakeups and lets you wake or cancel them.
Skills
Agents load skills: folders with a SKILL.md plus any scripts or reference files, which Claude pulls into context only when a task needs them. Managed Agents attaches them through the agent definition's skills array, either Anthropic's built-in skills or our own custom skills uploaded to the Skills API and versioned (docs).
- Source of truth is the graph. Every skill and every version of it is stored as entities (below). skills/<name>/SKILL.md in the monorepo only seeds version 1; after that, new versions come from approved change proposals. On approval, the agent service uploads the version to the Skills API and updates the agent definition, so new sessions pick it up; running sessions finish on the version they started with.
- Built-in: xlsx, pdf, docx for reports, invoices and contractor quotes (tracked in the graph as skills with source = anthropic, not editable).
- Starter custom skills: triage-maintenance-ticket, book-contractor, tenant-call, graph-conventions, planning-and-sleeping, and workflow-review (the judgement skill, below).
- One agent: all skills attach to the single agent definition (well inside the 500-skill limit). Each skill adds a little sandbox startup time and context, so keep descriptions sharp and prune unused ones.
Skills, versions, workflow issues and change proposals in the graph
Each skill is a workflow the agent follows. Skills, their versions, the problems found with them and the proposed fixes are all canonical entities with fixed schemas; their free-text fields are embedded like everything else.
Entity
Key fields (free text embedded)
Edges
skill
slug (unique), name, description, source (custom, anthropic), status (active, deprecated), api_skill_id
skill ->current-> skill_version, skill ->has_version-> skill_version
skill_version
version (int), content (the full SKILL.md + files, text), change_summary, created_by (seed, admin, proposal), api_version_id, published_at
skill_version ->supersedes-> skill_version, skill_version ->produced_by-> skill_change_proposal
workflow_issue
title, description, evidence (what happened vs what the skill said), category (wrong step, missing step, outdated info, ambiguous instruction, tool failure, policy gap), severity (low, medium, high, critical), status (open, proposal pending, resolved, won't fix), occurrences
workflow_issue ->affects-> skill and -> skill_version, ->relates_to-> ticket / person / company / email / call, ->evidenced_by-> chunk, ->found_in-> agent session, ->addressed_by-> skill_change_proposal
skill_change_proposal
proposed_content (full new SKILL.md), diff, reasoning, expected_effect, risks, status (pending review, approved, rejected, changes requested, superseded), review_notes, reviewed_by, reviewed_at
->for-> skill, ->based_on-> skill_version, ->addresses-> workflow_issue (one or more), ->proposed_by-> agent session
Agent tools: get_skill(slug, version?), list_workflow_issues(skill), report_workflow_issue(skill, title, description, evidence, category, severity, related_entities[]) and propose_skill_change(skill, proposed_content, reasoning, expected_effect, risks, issues[]). Reporting an issue first searches open issues on that skill by embedding similarity; a match increments occurrences and adds the new evidence and links instead of creating a duplicate. A proposal is always against the current version and must reference at least one issue.
The agent never edits a live skill. It reports and proposes; only an admin approves. This is the one place a human reviews anything; the agent's actions stay fully autonomous.
The judgement skill: workflow-review
One skill holds the criteria for when to flag an issue and when to propose a change, so this judgement is consistent across sessions and itself reviewable and versioned like any other skill.
- Flag an issue when: a step in a skill failed or produced the wrong outcome; the skill's instructions contradicted what actually happened (wrong contact route, outdated process, missing case); the agent had to improvise a step the skill doesn't cover; a tenant, contractor or admin complained about something a skill step caused; the same workaround was needed more than once.
- Don't flag: one-off external failures (a site was down, a call dropped), mistakes in the source data rather than the workflow, or preferences with no effect on outcome.
- Severity: critical = could cause harm, safety or legal exposure (e.g. an emergency handled as routine); high = the task failed or a person was misled; medium = extra steps or delay; low = wording or clarity.
- Propose a change when: the issue is critical or high, or a medium/low issue has 3+ occurrences, and the agent can name a concrete fix it's confident in. Otherwise flag only.
- What a proposal must contain: the full new skill text, a short reasoning that cites the issues and evidence (linked chunks, calls, emails, tickets), the expected effect, and any risks or cases the change could break. Change only what the issues require.
Review in the admin panel
A Skills page lists every skill with its current version, version history (with diffs between any two versions), open workflow issues ranked by severity and occurrences, and pending proposals. Opening a proposal shows the diff against the current version, the agent's reasoning, expected effect and risks, and the linked issues with their evidence (jump straight to the call transcript, email or ticket). The admin can approve (creates the new skill_version, publishes it and marks the linked issues resolved), request changes (notes go back to the agent, which can submit a revised proposal) or reject (with a reason, stored on the proposal). Admins can also edit a skill directly, which creates a version with created_by = admin.
Plans with ticked-off steps
For any task with more than one action, the agent writes a plan first, then works through it, ticking steps off as it goes. Plans live in the graph, so they survive sleeps, wake-ups and new sessions, and you can watch them update live.
Tool
What it does
create_plan(goal, steps[])
Creates a plan linked to the agent_run and the entities it concerns (e.g. the ticket); each step has a title, optional detail and optional dependency on earlier steps
get_plan()
Returns the plan with each step's status; the first call on every wake-up
update_step(step_id, status, note)
Moves a step through pending → in_progress → done, or to blocked / skipped with a reason
add_step / revise_plan
Adds or reorders steps when new information arrives; the previous version is kept
Rules (enforced in the tools and the planning-and-sleeping skill): one step in_progress at a time; a step is marked done only after the action it describes succeeded (the tool result is attached as evidence); before sleeping, the current step is left in_progress or blocked with what it's waiting for; the run ends only when every step is done or skipped with a reason.
In the admin panel: each run shows its plan as a live checklist (ticks appear as the agent completes steps, via the same SSE stream), with notes, evidence links, the pending wake-up if it's sleeping, and the plan's revision history. The ticket page shows the plans that touched that ticket.
Browser use with credential storage
Agents can use a real browser (contractor portals, council and utility sites, supplier ordering, landlord portals) through a new browser service. The browser runs on Browserbase (hosted headless Chromium, billed per session minute, nothing to run), driven from our side with Playwright over CDP and Stagehand for natural-language actions. Credentials live in GCP Secret Manager and are filled by our service, so the model never sees a password.
Tool
What it does
browser_open(url, profile?)
Starts a Browserbase session (optionally restoring a saved login profile) and returns page text + a screenshot
browser_act(instruction)
One natural-language action ("click Book a visit", "fill postcode with E1 6AN")
browser_extract(instruction, schema)
Pulls structured data off the page (e.g. available slots, invoice totals)
browser_login(credential)
Logs in with a stored credential: our service fills username, password and TOTP code directly into the page; the agent only gets "logged in" or the error
browser_screenshot() / browser_close()
Evidence for plan steps; ends the session and saves the login profile
Credential storage
- Vault: each credential is a Secret Manager secret (username, password, optional totp_seed). Metadata only (name, allowed_domains, last used) sits in a SurrealDB credential record. Values never enter the graph, logs or model context.
- Adding one: the admin panel's Credentials page is write-only: you can add, rotate or delete a credential but never read a value back.
- Domain lock: browser_login only fills when the page's origin is in the credential's allowed_domains, so a lookalike page can't harvest it.
- 2FA: TOTP codes are generated server-side from the stored seed; email codes can be read from the AgentMail inbox. SMS code retrieval requires a separate SMS integration; SIP voice does not provide SMS.
- Persistent logins: after a successful login, the Browserbase context (cookies, local storage) is saved per credential, so later sessions start logged in and browser_login is only needed when the session expires.
- Fits scale-to-zero and sleeps: a browser session never stays open across a sleep; it's closed and the login profile restored on wake.
Alternatives: Browserbase's 1Password integration if you'd rather keep credentials in 1Password (Browserbase + 1Password); or Browser Use Cloud, which has saved login profiles and domain-scoped secret bindings built in, with less control over each step (docs).
Voice
ElevenLabs Agents handles the conversation (STT, LLM, TTS, turn-taking, tools, transcripts). Vonage supplies the existing phone number and its connection to the telephone network.
Import the existing Vonage number into ElevenLabs as a SIP trunk number and assign the voice agent. Configure ElevenLabs outbound SIP with the Vonage trunk endpoint and digest credentials; route inbound calls from the Vonage number to ElevenLabs' SIP destination. Outbound calls use the ElevenLabs `/v1/convai/sip-trunk/outbound-call` API.
Audio travels directly between Vonage and ElevenLabs. The existing voice service handles HTTPS call requests, tools and webhooks; no audio bridge container is needed. See [voice setup](services/voice/README.md) for configuration and verification.
Call flow
1. Agent calls place_call(entity_id, objective).
2. FastAPI builds the call brief from the graph (who, history, open items) and passes it as dynamic variables / prompt override to the ElevenLabs agent.
3. During the call, the ElevenLabs agent can hit our server tools (e.g. lookup_entity, log_commitment) over HTTPS.
4. The post-call webhook lands on voice; the call becomes a call entity with its full transcript in the graph (see Data model → Calls), and the raw transcript, summary and audio are also kept as a source_file, chunked, embedded and linked to the call and every entity mentioned.
Inbound calls
1. The number is assigned to an inbound ElevenLabs agent.
2. At call start, ElevenLabs calls our voice service with the caller number (conversation-initiation webhook); voice resolves it to a canonical person and returns a call brief as dynamic variables. Unknown callers get a generic brief and a new person is created after the call.
3. During the call the agent uses the same server tools as outbound (lookup_entity, log_commitment, book_follow_up).
4. Post-call webhook → a call entity with the full transcript, plus a source_file that is chunked, embedded and linked to the caller and anything mentioned.
To verify during build: outbound calling and post-call webhook payload on our ElevenLabs plan; inbound caller metadata and conversation-initiation personalisation; two-way audio and caller ID using the existing Vonage number.
Email
AgentMail gives the agents real inboxes that send and receive. Inboxes are created by API, each with a real address; agents send, reply and reply-all within threads; inbound mail arrives by webhook (or WebSocket) after spam and virus checks, with reply text extracted from quoted history (AgentMail inbox capabilities). It supports custom domains with SPF, DKIM and DMARC, attachments, labels, drafts, and has a Python SDK (pip install agentmail).
Setup
- One inbox per agent persona (e.g. ops@, sales@) on withproperly.com (e.g. ops@withproperly.com), created by the email service at deploy time using client_id so re-runs never duplicate.
- MX, SPF, DKIM and DMARC records for withproperly.com from AgentMail's domain setup, managed in Terraform (Cloud DNS). DMARC starts at p=none and tightens once sending is verified.
- Webhook to email service, signature-verified; WebSocket stream as a local-dev fallback (no public URL needed).
Outbound
1. Agent calls send_email or reply_email (custom tools) with recipients, body and the entity ids it concerns.
2. No draft or approval step: the message goes out immediately.
3. On send, email sends via AgentMail and records the message and thread ids.
4. The sent message becomes an email entity and a source_file, chunked and linked to the recipients, so the graph knows what we promised.
Inbound
1. AgentMail webhook → email service → Pub/Sub → ingestion, same pipeline as the synthetic environment's emails (sender resolved to a canonical person by address).
2. If the thread belongs to an open agent task, the agent service resumes or starts a Managed Agents session with the new message and the entity context; otherwise it is ingested only.
3. Attachments are downloaded to GCS and ingested as documents linked to the email.
Every inbound and outbound message becomes an email entity linked to its people, and to a company and ticket when relevant (see Data model → Emails). AgentMail thread and message ids are stored on the email entity so replies stay in the right thread.
Architecture
The API is the single gateway to SurrealDB for the admin panel, the agent service and the voice service; only the ingestion and rules services write directly. Agents never touch the database or the phone line themselves: their custom tools call the API, which enforces validation and logs every action.
Claude is also used by the ingestion service (extraction, entity descriptions) and the rules service (plain-English rule compiler); embeddings are called from ingestion.
Services
Eight deployable services plus the database, each its own container, service account and Terraform resource. All share one Python package (packages/core: SurrealDB repository, schemas, entity-type registry) so the graph logic is written once.
Service
Runs on
Responsibility
Talks to
admin-panel (Next.js)
Cloud Run, scale to zero
Entity-type editor, edge-rule editor (plain English or form, with preview), live graph explorer, entity, ticket and document pages, merge/split, skills review (versions, workflow issues, proposals to approve), agent console with live plans, credentials (write-only), call and email logs. Single shared admin password
api only
api (FastAPI)
Cloud Run, scale to zero
The one gateway: REST + SSE, search, entity CRUD, rule CRUD and preview, action log, live graph stream, and the MCP endpoint the agent's tools call
Surreal Cloud, Pub/Sub, agent, voice, email, browser
ingestion (FastAPI)
Cloud Run, scale to zero, Pub/Sub push; Cloud Run Jobs for backfills
Land → normalise → chunk → extract → resolve → embed → link; regenerates entity descriptions (Haiku 5.5)
GCS, Surreal Cloud, Claude, embedding API
rules (FastAPI)
Cloud Run, scale to zero, Pub/Sub push; Cloud Run Job for full recompute
Plain-English rule compiler (Haiku 5.5), incremental and full edge recompute, stored graph layout
Surreal Cloud, Claude
agent (sandboxed agent)
Claude Managed Agents (Anthropic-hosted sandbox, Sonnet 5.5) + a thin Cloud Run service
Runs the one sandboxed agent as many parallel sessions (one per task, capped, queued beyond the cap), routes events to the session that owns the ticket, thread or call, relays events and plan updates to the admin panel, handles sleeps, wake-ups and scheduled invocations (Cloud Tasks); the sandbox calls our tools over MCP on api
Claude API, api, Cloud Tasks
voice (FastAPI)
Cloud Run, scale to zero
ElevenLabs: outbound calls, inbound routing and call brief, server tools, post-call webhooks → ingestion
ElevenLabs, api, Pub/Sub
email (FastAPI)
Cloud Run, scale to zero
AgentMail: inbox provisioning, send/reply, inbound webhooks, attachments → ingestion, replies wake agent tasks
AgentMail, api, agent, Pub/Sub
browser (FastAPI)
Cloud Run, scale to zero
Drives Browserbase sessions for the agent (open, act, extract, screenshot), fills stored credentials and TOTP codes from Secret Manager, saves login profiles
Browserbase, Secret Manager, api
SurrealDB
Surreal Cloud (managed)
System of record: graph, documents, vectors, full-text, plans, wake-ups, credential metadata
Reached over TLS with credentials from Secret Manager
Why Surreal Cloud: a database is the one thing that can't scale to zero on Cloud Run, so we don't host it. Surreal Cloud's Start plan gives one free instance (0.25 vCPU, 1 GB RAM, 1 GB storage), with paid instances from $0.021/hr and storage at $0.239/GB (pricing). Note it runs on AWS, not GCP, and its page doesn't say instances pause when idle; we pick the EU region nearest europe-west1 and expect to outgrow 1 GB once embeddings land.
Data model
Three layers live in one SurrealDB namespace: canonical entities (one record per real-world thing), source documents (with chunks), and extracted metadata, joined by graph edges. Entity types and edge rules are data, not code, so admins change them without a deploy.
Canonical entities
- Five canonical entity types for v1: email, call, person, company, ticket. Each is one SCHEMAFULL table generated from an entity_type registry. Typed fields give us the fixed schema; adding a type or field later (e.g. property, unit, asset) is a registry entry plus a migration that emits DEFINE TABLE/FIELD. Contractors, suppliers and landlords' firms are companies; tenants, landlords and contractor staff are people (with a roles[] field).
- Common fields on every type: name, aliases[], description (free text, embedded), external_ids (CRM id, ticket ref, email, phone), created_at, updated_at, merged_into.
- Each field in the registry declares type, required, unique_key (used for entity resolution) and embed: true|false. Every string field marked free-text defaults to embed: true.
Rule: every free-text field is embedded. Any field typed text in the registry (as opposed to short identifiers like string, enums, numbers and dates) gets a vector in the embedding table, including each item of a text array and each call-transcript turn. The tables below mark these with yes in the Embedded column; there are no exceptions.
All five types are canonical entities with fixed schemas. Every entity, emails and calls included, carries the common fields below, plus its own typed fields. Nothing is stored in untyped blobs; anything new gets added to the registry.
| Common field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| id | record id |  | e.g. email:⟨uuid⟩ |
| name | string |  | Display name (a person's name, an email's subject, "Call with Jane Doe, 10 Oct") |
| aliases | array<string> |  | Other names seen |
| description | text | yes | Free-text description, LLM-maintained unless pinned by an admin |
| external_ids | object |  | Ids in source systems (CRM id, AgentMail id, ElevenLabs id) |
| created_at / updated_at | datetime |  |  |
| version | int |  | Optimistic concurrency |
| merged_into | option<record> |  | Set when merged into another entity |
| layout_x / layout_y | float |  | Stored graph position |

## Person

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| roles | array<enum> |  | tenant, landlord, contractor, staff, other |
| emails | array<string>, unique each |  | Resolution key |
| phones | array<string>, unique each |  | E.164; resolution key |
| address | text | yes | Home or property address as given |
| preferred_contact | enum |  | email, phone, sms |
| availability | text | yes | e.g. "home after 5pm weekdays" |
| notes | array<text> | yes | Facts added by agents or admins |

## Company

| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| type | enum |  | contractor, supplier, managing agent, landlord, other |
| domains | array<string>, unique each |  | Resolution key (email domains) |
| emails / phones | array<string> |  | Main contact points |
| trades | array<enum> |  | For contractors: plumbing, heating, electrical, ... (same list as ticket category) |
| address | text | yes |  |
| coverage_area | text | yes | Areas a contractor covers |
| notes | array<text> | yes |  |

Tickets (maintenance issues)
A ticket is one maintenance issue (a leak, a broken boiler, damp, a faulty lift) however many calls, emails, photos and CRM notes mention it. It is a canonical entity like any other, so it is deduplicated, embedded, linked and visible in the graph.
| Field | Type | Embedded | Notes |
| --- | --- | --- | --- |
| ref | string, unique |  | Ticket reference from the source system, or generated |
| title | text | yes | Short summary, e.g. "No hot water, Flat 3B" |
| location | text | yes | Property and unit as free text until property/unit entities exist |
| category | enum |  | plumbing, heating, electrical, damp/mould, structural, appliances, pests, access/security, other |
| urgency | enum |  | emergency (same day), urgent, routine |
| status | enum |  | reported, triaged, scheduled, in progress, awaiting parts, resolved, closed |
| tags | array<string> |  | Free labels for rules and filters |
| reported_at / resolved_at | datetime |  |  |
| scheduled_visit_at | option<datetime> |  | Contractor visit slot |
| cost_estimate / cost_actual | option<decimal> |  |  |
| description | text | yes | Tenant's account plus extracted detail |
| access_instructions | text | yes | Keys, entry times, pets |
| resolution | text | yes | What was done |
| notes | array<text> | yes | Progress notes from agents and admins |

Default edges: ticket ->reported_by-> person (tenant), ticket ->assigned_to-> company (contractor) or person, ticket ->for-> company (managing agent or landlord's firm, when known), person ->works_at-> company, ticket ->evidenced_by-> chunk (photos, documents), call ->about-> ticket from each related call (see Calls), and `email ->about-> ticket` from each related email (see Emails). Default edge rules: recurring_issue between tickets at a similar location within 90 days, and similar_to by description similarity.
How tickets are created and updated: ticket records in the synthetic environment seed them directly; ingestion links a call or email to an open ticket (ticket ref in the text, else same reporter or location + similar description) or opens a new one; the sandboxed agent can create_ticket, update_ticket, book a contractor by email or phone, and call the tenant back with a visit time.
Emails
Every email is a canonical email entity, one per message, whether it came from the synthetic environment or an AgentMail inbox, inbound or sent by the agent. The same message arriving twice (e.g. CC'd to an agent inbox and in the env dump) resolves to one entity by message_id.
Field
Type
Embedded
Notes
message_id
string, unique

RFC 5322 Message-ID; resolution key
thread_id
string

AgentMail thread id, or derived from headers
in_reply_to / references
option<string> / array<string>

Threading headers
channel
enum

synthetic_env, agentmail
mailbox
option<string>

Agent inbox it arrived at or was sent from
direction
enum

inbound, outbound
status
enum

received, sent, failed, bounced
subject
text
yes

from_address / from_name
string


to_addresses / cc_addresses / bcc_addresses
array<string>


reply_to_address
option<string>


sent_at / received_at
datetime


body_text
text
yes
Reply text with quoted history stripped
body_full
text
yes
Full plain-text body including quoted history
summary
text
yes
One-line Haiku 5.5 summary
action_items
array<text>
yes
Requests or commitments extracted from the email
intent
enum

report_issue, update, scheduling, quote_or_invoice, complaint, other
urgency
enum

emergency, urgent, routine
sentiment
enum

positive, neutral, negative
language
string

ISO 639-1
attachments
array<object>

{filename, mime, size, gcs_uri, document}; each attachment's text is ingested as a document and embedded
labels
array<string>

AgentMail labels
is_spam
bool

From AgentMail checks
agent_session
option<string>

Session that sent it or is handling it
raw_uri
string

Original .eml in GCS
Edges:
- email ->sent_by-> person (exactly one) and email ->sent_to-> person (one or more, To and CC), resolved from addresses; unknown addresses create a new person.
- email ->about-> company when relevant: the sender's or a recipient's company (via works_at or email domain), or a company the body is clearly about. Not added for generic domains like gmail.com unless the content names the company.
- email ->about-> ticket when relevant: the ticket ref appears in the subject or body, an earlier email in the thread is already linked, or extraction matches it to an open ticket (same reporter, similar description) above a confidence threshold. One email can relate to several tickets.
- email ->reply_to-> email for threading, and email ->derived_from-> source_file for the raw .eml, whose chunks mention the email's people, company and ticket.
Emails appear in the live graph like any other entity, so a ticket's neighbourhood shows its whole email trail, and an email sent by the agent shows up the moment it's sent.
Calls
Every phone call is a canonical call entity, one per call, inbound or outbound, from the synthetic environment or placed and received by the agent through ElevenLabs. The full transcript is stored in the graph, on the call itself, not only in GCS.
Field
Type
Embedded
Notes
call_id
string, unique

ElevenLabs conversation id, or the env's call id; resolution key
provider
enum

elevenlabs, synthetic_env
direction
enum

inbound, outbound
from_number / to_number
string

E.164; used to resolve people
agent_number
option<string>

Our number used
started_at / answered_at / ended_at
datetime


duration_s
int


status
enum

completed, voicemail, no_answer, busy, failed
end_reason
option<string>

Who hung up, timeout, error
objective
text
yes
Why the call was made (outbound) or what the caller wanted (inbound)
call_brief
text
yes
Context the agent gave the voice agent
transcript
array<object>
yes, per turn
{turn, speaker_role (agent, caller, callee), person?, text, start_ms, end_ms}; every turn kept in full and each turn's text embedded
transcript_text
text
yes
Whole transcript as one text; long calls also chunked and each chunk embedded
summary
text
yes
Haiku 5.5 summary
outcome
text
yes
What was agreed (e.g. "contractor visit Tue 10:00")
action_items
array<text>
yes
Follow-ups the call created
intent
enum

report_issue, update, scheduling, quote_or_invoice, complaint, other
urgency / sentiment
enum

As for email
language
string

ISO 639-1
tool_calls
array<object>

Server tools the voice agent used during the call
recording_uri
option<string>

Audio in GCS
agent_session
option<string>

Session that placed or answered it
Edges:
- call ->with-> person: one or more participants (caller, callee, anyone added), resolved by phone number, else by name in the transcript; unknown numbers create a new person.
- call ->about-> company when relevant: a participant's company, or a company the conversation is clearly about.
- call ->about-> ticket when relevant: a ticket ref spoken or in the call brief, the call was placed for a ticket by the agent, or extraction matches an open ticket above the confidence threshold. One call can relate to several tickets.
- call ->follows_up-> call | email when the agent placed it in response to an earlier call or email, and call ->derived_from-> source_file for the raw transcript and recording, whose chunks mention everyone and everything discussed.
Calls from the agent's sessions are linked to the session that placed or answered them, so a ticket's neighbourhood shows its full call history with transcripts alongside its emails.
Source documents and metadata
- source_file: every ingested file, stored in the graph: filename, mime, size, sha256 (unique), gcs_uri, origin (synthetic_env, agentmail, elevenlabs, upload, agent), received_at, parser, page_count, title (text, embedded).
- chunk: ordinal, text (embedded), page, char_start / char_end, t_start_ms / t_end_ms for calls, token_count, chunker_version.
- extracted_fact (the "metadata"): chunk, key (e.g. visit_time, cost_quoted), value (typed), text (embedded), confidence, extractor_version.
- Graph edges: source_file ->contains-> chunk, chunk ->next-> chunk, chunk ->mentions-> <entity> (with span, confidence), extracted_fact ->about-> <entity>, <entity> ->evidenced_by-> chunk for field values, and email | call ->derived_from-> source_file. Every field value traces back to a chunk and its file.
Embeddings: everything free-text
One embedding table holds a vector for every embeddable string in the system: owner (record link), field, text, model, vector. One HNSW index (DiskANN if it outgrows memory) gives one search across entities, chunks, facts, notes and transcripts. Entity tables also keep description_vec inline for fast similarity edges.
A write to any field marked embed: true puts an embed job on Pub/Sub; the worker upserts the vector and records text_hash, so unchanged text is never re-embedded.
Edge criteria (configurable)
An edge_rule record defines how edges are generated between entity types. Admins create, preview (count + 20 sample pairs), enable and version rules in the UI.
Criterion kind
Example
Compiles to
field_match
person.email_domain = company.domain → works_at
Indexed equality join
field_overlap
Two tickets share any tags → related_ticket
Array intersection
expression
$a.region = $b.region AND $b.arr > 100000
Raw SurrealQL WHERE with $a, $b
co_occurrence
Mentioned together in ≥ 3 documents in 90 days → interacts_with
Graph traversal over mentions
similarity
Cosine(description_vec) ≥ 0.85, top 5 → similar_to
HNSW KNN
llm_judge
Candidates from co-occurrence, Claude labels the relation
Batch job, cached per pair
Authoring: plain English or form, same result. An admin can type "link people to the company whose domain matches their email" or build the rule in the form. The rules service sends the text, the entity-type registry and sample records to Claude, which returns a rule spec (one of the six kinds above, with params). The UI opens that spec in the form, shows the compiled SurrealQL and a preview of matches, and nothing runs until the admin saves and enables it. The original sentence is stored on the rule as prompt for audit.
Generated edges live in relation tables named by the rule (works_at, similar_to) and carry rule, rule_version, score, evidence[] and computed_at. Manual edges carry rule = NONE and are never removed by recompute.
Recompute: entity writes trigger incremental evaluation for that entity only; a rule change runs a full job that writes edges at the new rule_version, then deletes edges from older versions.
Schema sketch (SurrealQL, verify against 3.x syntax)
DEFINE TABLE person SCHEMAFULL;
DEFINE FIELD name ON person TYPE string;
DEFINE FIELD aliases ON person TYPE array<string> DEFAULT [];
DEFINE FIELD email ON person TYPE option<string>;
DEFINE FIELD email_domain ON person TYPE option<string>;
DEFINE FIELD roles ON person TYPE array<string> DEFAULT [];
DEFINE FIELD description ON person TYPE string DEFAULT '';
DEFINE FIELD description_vec ON person TYPE option<array<float>>;
DEFINE INDEX person_email ON person FIELDS email UNIQUE;
DEFINE INDEX person_desc_vec ON person FIELDS description_vec HNSW DIMENSION 1536 DIST COSINE;

DEFINE TABLE source_file SCHEMAFULL;
DEFINE FIELD filename ON source_file TYPE string;
DEFINE FIELD mime ON source_file TYPE string;
DEFINE FIELD sha256 ON source_file TYPE string;
DEFINE FIELD gcs_uri ON source_file TYPE string;
DEFINE FIELD origin ON source_file TYPE string;
DEFINE FIELD received_at ON source_file TYPE datetime;
DEFINE INDEX file_sha ON source_file FIELDS sha256 UNIQUE;

DEFINE TABLE chunk SCHEMAFULL;
DEFINE FIELD ordinal ON chunk TYPE int;
DEFINE FIELD text ON chunk TYPE string;
DEFINE FIELD page ON chunk TYPE option<int>;
DEFINE FIELD char_start ON chunk TYPE option<int>;
DEFINE FIELD char_end ON chunk TYPE option<int>;
DEFINE TABLE contains TYPE RELATION IN source_file OUT chunk;
DEFINE TABLE derived_from TYPE RELATION IN email | call OUT source_file;

DEFINE TABLE ticket SCHEMAFULL;
DEFINE FIELD ref ON ticket TYPE string;
DEFINE FIELD title ON ticket TYPE string;
DEFINE FIELD location ON ticket TYPE string DEFAULT '';
DEFINE FIELD category ON ticket TYPE string;
DEFINE FIELD urgency ON ticket TYPE string ASSERT $value IN ['emergency','urgent','routine'];
DEFINE FIELD status ON ticket TYPE string ASSERT $value IN ['reported','triaged','scheduled','in_progress','awaiting_parts','resolved','closed'];
DEFINE FIELD reported_at ON ticket TYPE datetime;
DEFINE FIELD resolved_at ON ticket TYPE option<datetime>;
DEFINE FIELD description ON ticket TYPE string DEFAULT '';
DEFINE FIELD resolution ON ticket TYPE string DEFAULT '';
DEFINE INDEX ticket_ref ON ticket FIELDS ref UNIQUE;

DEFINE TABLE email SCHEMAFULL;
DEFINE FIELD message_id ON email TYPE string;
DEFINE FIELD thread_id ON email TYPE string;
DEFINE FIELD subject ON email TYPE string;
DEFINE FIELD direction ON email TYPE string ASSERT $value IN ['inbound','outbound'];
DEFINE FIELD sent_at ON email TYPE datetime;
DEFINE FIELD body ON email TYPE string;
DEFINE FIELD summary ON email TYPE string DEFAULT '';
DEFINE INDEX email_msgid ON email FIELDS message_id UNIQUE;
DEFINE TABLE sent_by TYPE RELATION IN email OUT person;
DEFINE TABLE sent_to TYPE RELATION IN email OUT person;
DEFINE TABLE call SCHEMAFULL;
DEFINE FIELD call_id ON call TYPE string;
DEFINE FIELD direction ON call TYPE string ASSERT $value IN ['inbound','outbound'];
DEFINE FIELD from_number ON call TYPE string;
DEFINE FIELD to_number ON call TYPE string;
DEFINE FIELD started_at ON call TYPE datetime;
DEFINE FIELD duration_s ON call TYPE int;
DEFINE FIELD status ON call TYPE string;
DEFINE FIELD transcript ON call TYPE array<object>;
DEFINE FIELD transcript_text ON call TYPE string;
DEFINE FIELD summary ON call TYPE string DEFAULT '';
DEFINE FIELD outcome ON call TYPE string DEFAULT '';
DEFINE INDEX call_cid ON call FIELDS call_id UNIQUE;
DEFINE TABLE with TYPE RELATION IN call OUT person;
DEFINE TABLE about TYPE RELATION IN email | call OUT company | ticket;

DEFINE TABLE mentions TYPE RELATION IN chunk OUT person | company | ticket | email | call SCHEMAFULL;
DEFINE FIELD span ON mentions TYPE object;
DEFINE FIELD confidence ON mentions TYPE float;

DEFINE TABLE embedding SCHEMAFULL;
DEFINE FIELD owner ON embedding TYPE record;
DEFINE FIELD field ON embedding TYPE string;
DEFINE FIELD text ON embedding TYPE string;
DEFINE FIELD vector ON embedding TYPE array<float>;
DEFINE INDEX emb_vec ON embedding FIELDS vector HNSW DIMENSION 1536 DIST COSINE;
DEFINE ANALYZER en TOKENIZERS class FILTERS lowercase, snowball(english);
DEFINE INDEX emb_fts ON embedding FIELDS text FULLTEXT ANALYZER en BM25;

DEFINE TABLE edge_rule SCHEMAFULL;
DEFINE FIELD name ON edge_rule TYPE string;
DEFINE FIELD relation ON edge_rule TYPE string;
DEFINE FIELD from_type ON edge_rule TYPE string;
DEFINE FIELD to_type ON edge_rule TYPE string;
DEFINE FIELD kind ON edge_rule TYPE string;
DEFINE FIELD params ON edge_rule TYPE object;
DEFINE FIELD enabled ON edge_rule TYPE bool DEFAULT false;
DEFINE FIELD version ON edge_rule TYPE int DEFAULT 1;
Ingestion pipeline
Every source file (document, email, call recording or transcript, CRM export, photo, attachment) is stored in the graph as a source_file, chunked, and every chunk embedded and linked both to its file and to the primary entities it mentions. Haiku 5.5 extracts primary-entity candidates per chunk; the candidates are deduplicated, merged and flattened within the file before anything is written to the graph, then resolved against existing entities. Each stage is idempotent and has its own Pub/Sub topic, so any stage can be re-run (e.g. a new extractor version) without re-ingesting.
1. Land: raw file to GCS, and a source_file record in the graph (filename, mime type, size, sha256, gcs_uri, origin, received time). Re-sent files dedupe on sha256.
2. Parse: per-type parser to clean text with structure kept: Docling for PDF/DOCX (pages, headings, tables), EML headers + body for email, speaker-turned transcript for calls (ElevenLabs transcript or Scribe for raw audio), typed JSON for CRM records, Haiku 5.5 vision caption for photos.
3. Chunk: structure-aware chunks of ~800 tokens with ~100 overlap, never splitting a table row or speaker turn; calls chunk by windows of whole turns; short emails are one chunk. Each chunk keeps ordinal, text, page or offsets, timestamps for calls, and links source_file ->contains-> chunk plus chunk ->next-> chunk.
4. Embed chunks: batch embedding of every chunk's text into the embedding table.
5. Extract candidates (Haiku 5.5): for each chunk, structured output constrained to the entity-type registry (person, company, ticket, email, call): every primary entity mentioned, with type, name as written, any typed field values found (e.g. phone, email, ticket ref, urgency), the exact span, and confidence. File-level context (email headers, call participants, document title) is passed in so pronouns and signatures resolve.
6. Deduplicate, merge and flatten (in memory, per file):
  - Deduplicate: cluster candidates across all chunks of the file by hard keys first (email address, phone, domain, ticket ref, message id, call id), then normalised name + type, then embedding similarity of name + surrounding text, with a Haiku 5.5 tie-break for ambiguous clusters ("Jane", "J. Doe" and "jane.doe@…" become one person).
  - Merge: fold each cluster into one candidate: union aliases, emails and phones; resolve conflicting field values by confidence, then recency, then frequency; keep every mention span.
  - Flatten: emit one flat record per entity containing only registry fields with registry types (nested objects unpacked into typed fields, lists de-duplicated, empty values dropped, values normalised: lowercase emails and domains, E.164 phones, ISO dates, enum values mapped), plus its list of (chunk, span, confidence) mentions.
7. Resolve against the graph: match each flattened candidate to an existing canonical entity by hard keys, then KNN over name and description embeddings, then a Haiku 5.5 adjudication; create a new entity below the threshold. Upsert with the entity's version for safe concurrent writes; every decision is logged for the merge UI.
8. Link: chunk ->mentions-> entity (span, confidence, extractor version) for every mention; entity ->evidenced_by-> chunk for each field value it supplied; for emails and calls, the email / call entity ->derived_from-> source_file.
9. Embed and propagate: embed every new or changed free-text field on the touched entities, publish the changes to the live graph stream, and trigger incremental edge-rule evaluation.
Re-running a file with a new extractor version writes mentions at the new version, then removes the old version's mentions, so the graph never holds two generations of links for one file.
Entity description is regenerated by an LLM summary over the entity's facts and recent mentions whenever new evidence arrives (debounced), then re-embedded. Admin-edited descriptions are pinned and never overwritten.
API surface
FastAPI, versioned under /v1, OpenAPI-first so the Next.js client and the agent MCP tools are generated from one schema.
Area
Endpoints
Ingestion
POST /ingest/upload, POST /ingest/sync (pull from synthetic env), GET /ingest/jobs/{id}
Entity types
GET/POST/PATCH /entity-types, POST /entity-types/{id}/migrate
Entities
GET /entities?type=&q=, GET/PATCH /entities/{id}, POST /entities/{id}/merge, GET /entities/{id}/graph?depth=, GET /entities/graph.bin (snapshot), GET /entities/graph/stream?since= (SSE deltas)
Documents
GET /documents, GET /documents/{id} (text, chunks, highlighted mentions, facts)
Edge rules
GET/POST/PATCH /edge-rules, POST /edge-rules/{id}/preview, POST /edge-rules/{id}/recompute
Search
POST /search (hybrid: vector + BM25 + graph expand, filters by type/kind/date; returns citations)
Agents
POST /agent-runs, GET /agent-runs/{id}, GET /agent-runs/{id}/stream (SSE)
Action log
GET /actions?session=&subject= (every external action the agent took)
Calls
POST /calls (place via ElevenLabs), GET /calls/{id}, POST /webhooks/elevenlabs/post-call (HMAC-verified), POST /tools/voice/* (server tools the voice agent calls)
MCP
/mcp exposing search, entity, traverse, document and action tools to agents
Infrastructure
Minimal, serverless, scale-to-zero. Every service is a Cloud Run service or job with min-instances = 0, so nothing runs (or bills) when idle and everything autoscales with cold starts. No VMs, clusters, VPCs, NAT, load balancers, private pools or always-on workers, and no security or compliance work beyond what's needed to stop strangers using the agents. The only stateful pieces are managed services we don't run: Surreal Cloud, GCS, Pub/Sub, Secret Manager.
Terraform creates a new, dedicated GCP project in europe-west1 (Belgium, the nearest region that supports Cloud Run custom domain mappings). A one-off bootstrap stack creates the project and the Cloud Build pipeline; from then on every change ships through Cloud Build. Manual steps: secret values, the GitHub connection approval, the GoDaddy nameserver change, and creating the Surreal Cloud instance.
Domain: withproperly.com
withproperly.com stays registered at GoDaddy; its DNS moves to a Cloud DNS zone created by Terraform (managed, nothing to run). After bootstrap, replace the nameservers in GoDaddy with the four Cloud DNS nameservers Terraform outputs; propagation can take up to 48 hours, so do it first.
Hostname
Points to
Purpose
admin.withproperly.com
Cloud Run domain mapping → admin-panel
Admin panel
api.withproperly.com
Cloud Run domain mapping → api
API, MCP endpoint for agents
hooks.withproperly.com
Cloud Run domain mapping → voice / email
ElevenLabs and AgentMail webhooks, ElevenLabs server tools
withproperly.com MX + TXT
AgentMail
Agent inboxes (ops@, sales@), SPF, DKIM, DMARC
Cloud Run domain mappings issue TLS certificates automatically; no load balancer.
Terraform module
Resources
bootstrap (run once)
google_project with billing link, required APIs, tf-state bucket, Cloud Build service account, Cloud Build GitHub connection + repository link, Cloud DNS zone for withproperly.com
cloud_build
pr-checks, one deploy trigger per service (path-filtered), infra and migrations triggers
cloud_run
Services admin-panel, api, ingestion, rules, agent, voice, email, all min-instances = 0, startup CPU boost on; Cloud Run Jobs for migrations, backfill and full recompute; domain mappings
pubsub
Topics + push subscriptions to Cloud Run per ingestion stage, rule-recompute and embed; dead-letter topic
storage
GCS buckets: raw, artifacts
scheduler
Cloud Scheduler job for the nightly recompute; Cloud Tasks queue agent-wakeups for sleeps and scheduled invocations
secrets
Secret Manager: Claude API key, ElevenLabs, AgentMail, Browserbase, Surreal Cloud credentials, admin password, internal service token; one secret per stored browser credential (created from the admin panel). Vonage management credentials are used for provisioning; Vonage SIP credentials are stored in the ElevenLabs trunk configuration.
dns
Records for the domain mappings and AgentMail
artifact_registry
Docker repo for all service images
Not included on purpose: VPC, NAT, load balancer, Cloud Armor, IAP, private worker pools, Compute Engine, GKE, alerting, staging environment.
Monorepo layout
One Git repo, one top-level folder per service under services/. Each service folder is self-contained: its own dependencies, Dockerfile, tests and cloudbuild.yaml, so it builds and deploys on its own. Shared Python code lives in one package that the Python services import.
propadm/
├── services/
│   ├── admin-panel/      # Next.js (pnpm), live graph explorer with cosmos.gl
│   ├── api/              # FastAPI gateway, SSE, MCP endpoint for the agent
│   ├── ingestion/        # FastAPI, Pub/Sub push: normalise, extract, resolve, embed, link
│   ├── rules/            # FastAPI, Pub/Sub push: rule compiler, edge recompute, layout
│   ├── agent/            # FastAPI, Managed Agents sessions + agent definition
│   ├── voice/            # FastAPI, ElevenLabs calls, webhooks, server tools
│   ├── email/            # FastAPI, AgentMail inboxes, send/reply, webhooks
│   └── browser/          # FastAPI, Browserbase sessions, credential fill from Secret Manager
├── skills/               # agent skills: one SKILL.md folder each, uploaded on deploy
├── packages/
│   └── core/             # shared Python: SurrealDB client + queries, entity-type registry,
│                         # Pydantic schemas, Claude/embedding clients, config
├── db/
│   ├── schema/           # SurrealQL migrations (generated from the registry + hand-written)
│   └── seed/             # loader for the synthetic environment
├── infra/
│   ├── bootstrap/        # one-off: GCP project, Cloud Build, DNS zone
│   └── main/             # Cloud Run, Pub/Sub, GCS, Scheduler, secrets, DNS records, triggers
├── pyproject.toml        # uv workspace: services/* (Python) + packages/core
├── pnpm-workspace.yaml   # services/admin-panel
└── Makefile              # make dev / test / deploy SERVICE=api
Each service folder follows the same shape:
services/<name>/
├── app/              # code (main.py, routes, handlers)
├── tests/
├── pyproject.toml    # depends on packages/core via the uv workspace
├── Dockerfile        # built from the repo root so it can copy packages/core
└── cloudbuild.yaml   # build, push, deploy this service only
- Tooling: a uv workspace for the six Python services + packages/core (one lockfile), pnpm for the admin panel. Ruff and pytest for Python; ESLint and Vitest for the admin panel.
- Per-service CD: one Cloud Build deploy trigger per service, filtered with includedFiles on services/<name>/** and packages/core/**, so a change to voice redeploys only voice, and a change to core redeploys every Python service. skills/** seeds new skills into the graph as version 1 (later versions come from approved proposals in the admin panel); infra/** has its own trigger that runs terraform apply; db/schema/** runs migrations.
- API types: api publishes its OpenAPI schema; the admin panel generates its TypeScript client from it in CI, so the two can't drift.
- Local dev: docker compose up runs every service plus a local SurrealDB; webhooks reach it through the AgentMail WebSocket stream and an ElevenLabs tunnel.
Continuous deployment (Cloud Build)
Every merge to main deploys automatically through Cloud Build (serverless, billed per build minute). Pipelines live in the repo as cloudbuild/*.yaml.
Trigger
Fires on
Steps
pr-checks
Pull request to main
Lint + tests, terraform plan
deploy
Push to main
One trigger per service folder (path-filtered, see Monorepo layout); each builds its image, push to Artifact Registry tagged with commit SHA, terraform apply, run SurrealDB migrations as a Cloud Run Job, gcloud run deploy each changed service, sync agent definitions (Managed Agents agent, ElevenLabs agent config) from code, smoke test /healthz
Rollback is shifting traffic back to the previous Cloud Run revision.
Implementation plan
Six phases in dependency order, each ending in a gate we can demo. The admin panel (phase 3) can start as soon as the API schema exists and run alongside phases 1–2.
Phase 0: Foundations
[ ] Monorepo with one folder per service under services/, plus packages/core, db/, infra/; uv + pnpm workspaces
[ ] Terraform bootstrap: new GCP project, billing link, APIs, state bucket, Cloud Build SA, GitHub connection, Cloud DNS zone
[ ] Point withproperly.com nameservers at GoDaddy to Cloud DNS; add withproperly.com to AgentMail
[ ] Create the Surreal Cloud instance; spike 3.x HNSW, FULLTEXT, RELATION, LIVE and CHANGEFEED syntax
[ ] Cloud Build pr-checks and deploy; hello-world deploy of every service at min-instances = 0 with domain mappings
[ ] Configure the existing Vonage number and import it into ElevenLabs over SIP
Phase 1: Ingestion and resolution
[ ] Entity-type registry (YAML) → SurrealQL migration generator
[ ] Adapters: email (EML/JSON), call (audio → Scribe / transcript), document (Docling), CRM record
[ ] Chunker, Claude extraction with structured output, extractor versioning
[ ] Entity resolution (keys → KNN → LLM tie-break) with decision log
[ ] Embedding worker with text_hash skip; embedding table + indexes
Phase 2: Edge rules and search
[ ] edge_rule model and compiler for the 6 criterion kinds
[ ] Plain-English → rule spec compiler (Claude, structured output), shown in the form for confirmation
[ ] Preview endpoint (count + samples), incremental and full recompute, versioned cleanup
[ ] Hybrid search: KNN + BM25 fused (reciprocal rank fusion) + 1-hop graph expansion, citations
Phase 3: Frontend (Next.js)
[ ] Password login, app shell, generated API client
[ ] Graph explorer (cosmos.gl, with the DEV-934 camera and error-state fixes), entity page (fields, evidence, edges, timeline)
[ ] Document viewer with highlighted mentions and extracted facts
[ ] Edge-rule editor with live preview; entity-type editor
[ ] Agent console (SSE stream), action log, call log with transcripts
Phase 4: Agents and sandbox
[ ] Managed Agents agent definition (Sonnet 5.5, prompt, built-in toolset, MCP server) kept in code and synced on deploy; graph read and write tools with change_log and undo; sleep (10-minute cap), wake-on events and schedule_invocation via Cloud Tasks; skills, versions, workflow issues and change proposals in the graph with the workflow-review skill and the admin Skills review page; parallel sessions with subject ownership, concurrency cap and optimistic writes; plan tools with live checklist in the admin panel
[ ] MCP endpoint on api with per-session bearer tokens
[ ] agent service: create sessions, relay events to SSE, persist agent_run
[ ] Action log for every tool call; no approval step
Phase 5: Voice, email and demo
[ ] ElevenLabs agent config (prompt, voice, server tools) in code, not console
[ ] place_call tool, call brief builder, post-call webhook → source document
[ ] Inbound agent with caller-number lookup and call brief
[ ] Demo script, seed data reset, load test at demo volume
[ ] AgentMail: custom subdomain + DNS in Terraform, inbox provisioning on deploy, signed webhook
[ ] send_email / reply_email tools sending immediately, no approval
[ ] Inbound email → ingestion, and replies on open threads resume the agent's task
Risks

## Addenda

[Addendum A — Properties, Ledgers and Service Providers](PRD-ADDENDUM-A.md)
(10 October 2026, Fergus) extends this specification and takes precedence where
it changes entity types, ticket location/assignment, ledger rules, and provider
workflows. It is kept in a linked chapter to respect the 1,000-line file limit.
