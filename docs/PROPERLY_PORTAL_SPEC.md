# Properly — Property Manager Portal: Build Spec

> **For coding agents.** This is the single source of truth for building the Properly property manager portal. It pulls together the product thesis, workflows, rules, UX and data model from the hackathon planning. Read sections 0–3 before writing code. When this spec and the organisers' data or our existing knowledge-graph (KG) tool disagree, **the data and the existing tool win** — adapt the portal to them, keep the behaviour described here.

**Product:** Properly — an AI-native operating system for UK letting agents / property managers.
**What already exists:** a knowledge-graph-based agent that (a) triages maintenance, (b) answers tenant and landlord tickets, (c) schedules viewings.
**What this spec covers:** the **portal property managers use** to supervise, steer and step into that agent's work, plus the tenant/landlord-facing views it powers.
**Event context:** Dwelly "Real-World Agents" hackathon, 10 Oct 2026, Property Management track. Code and demo video freeze at **16:30**, final deadline **17:00**.

---

## Contents

0. TL;DR and build priority
1. Product thesis and principles
2. Users and roles
3. Human-in-the-loop model (autonomy, flags, take-over)
4. Information architecture and navigation
5. Screen specs
   - 5.1 Today (home)
   - 5.2 Inbox (tenant, landlord, prospect, contractor tickets)
   - 5.3 Maintenance (board, job detail, progress card)
   - 5.4 Viewings and lettings (pipeline, trip builder, follow-up)
   - 5.5 Calendar (unified)
   - 5.6 Availability hub (tenants, prospects, contractors)
   - 5.7 Properties (property 360, per-property flags)
   - 5.8 People (tenants, landlords, contractors, prospects)
   - 5.9 Contractors (trusted list, scoring)
   - 5.10 Compliance and inspections
   - 5.11 Money (rent, invoices, statements)
   - 5.12 Settings (autonomy, limits, SLAs, templates, voice)
6. The maintenance progress card (Uber-style)
7. Workflows the portal must reflect
8. Escalation rules and flag catalogue
9. Voice agent in the portal
10. Delight features
11. Tenant and landlord portals (external views)
12. UK legal guardrails the UI must enforce
13. Data model
14. KG tool integration and API contract
15. Notifications, messages and templates
16. Design system and copy
17. Demo script and test scenarios
18. Reference data (issue spreadsheets)

---

## 0. TL;DR and build priority

**The idea in one line:** the AI does the work; the property manager sees everything, gets pinged only when judgement is needed, and can take over any thread, job or viewing in one click.

**Three pillars the user asked for:**
1. **Maintenance triage with human in the loop** — board + job detail + progress card + approve/override controls.
2. **Viewings scheduling** — built-in calendar, per-property viewing rules and flags, multi-property trips from one set of prospect availability, follow-up after viewing through to contract.
3. **Unified inbox** — tenant and landlord (plus prospect and contractor) tickets, AI drafts, one-click take-over, and flags when a human is needed.

**Build order for the demo (do in this order, stop when time runs out):**

| Priority | Build | Why |
|---|---|---|
| P0 | Global flag system + "Needs you" queue | It's the human-in-the-loop story; judges score judgement & safety |
| P0 | Inbox: list, thread view, AI draft (approve / edit / send), Take over / Hand back | Core pillar 3 |
| P0 | Maintenance job detail with **progress card** + approve/override buttons | Core pillar 1, the hero visual |
| P1 | Maintenance board (kanban by stage) | Overview |
| P1 | Viewings calendar (week view, per-property lanes) + property viewing flags | Core pillar 2 |
| P1 | Multi-property trip builder from prospect availability | Neat feature |
| P2 | Post-viewing follow-up → application → contract tracker | Neat feature |
| P2 | Availability hub (tenant ↔ contractor auto-scheduling status) | Neat feature |
| P2 | Today dashboard KPIs, Property 360, Contractors, Compliance, Money | Completeness |
| P3 | Tenant/landlord external progress pages | Nice to show |

**Rules of thumb:** real data from the KG tool wherever possible; seed realistic demo data otherwise (clearly marked as demo data). Never fake agent results in submitted outputs.

---

## 1. Product thesis and principles

### 1.1 Problems we solve (from operating a property-management roll-up)
1. **Repair intake is chaos** — reports come by phone, email, WhatsApp; vague, no photos, no access details.
2. **Spend limits are handled from memory** — landlords surprised by bills, or repairs stall waiting for approval that wasn't needed.
3. **Scheduling ping-pong** — agent asks contractor, then tenant, then contractor again.
4. **Severity is misread** — emergencies hidden in chatty messages or calm-looking photos.
5. **Emergencies sit in the same queue as dripping taps.**
6. **10–20% of scheduled jobs fail** because the tenant isn't home.
7. **Completion reporting is manual** — landlords chase proof, tenants aren't told.
8. **Planned maintenance lives in spreadsheets** — certificates lapse.
9. **Staff spend hours on the phone** confirming urgency, chasing and booking.
10. **Enquiries go cold; viewings are one-per-trip; follow-up is slow; application review is inconsistent; renters retype details for every flat.**

### 1.2 Principles for the portal
- **AI does, human decides.** The agent drafts and acts within limits; the portal makes every decision point visible and one click away.
- **Exceptions first.** The default view is "what needs you", not "everything".
- **Everything is explainable.** Every AI action shows: what it did, why, the facts it used (with KG sources), and confidence.
- **Everything is reversible or pausable.** Take over, hand back, undo window on sends, pause automation per job/thread/property.
- **Emergencies never wait.** No approval or form ever blocks an emergency; the UI shows emergencies above everything, with a persistent banner.
- **One record, many views.** A job, ticket or viewing appears in inbox, board, calendar and property page — always the same object.
- **Tenants never see costs; landlords always do.**
- **Plain English.** No jargon in the UI ("Needs your OK", not "Pending HITL approval").

---

## 2. Users and roles

| Role | What they do in the portal | Default view |
|---|---|---|
| **Property manager (PM)** | Owns a portfolio; approves, takes over, handles escalations | Today |
| **Lettings negotiator** | Viewings, prospects, applications | Viewings |
| **On-call PM** | Out-of-hours emergencies (P0 pages) | Emergency queue (mobile-first) |
| **Team lead / owner** | Oversight, settings, autonomy levels, performance | Today + Settings |
| **Accounts** (later) | Invoices, rent, statements | Money |
| **AI agent** (system actor) | Shown as "Properly AI" in timelines | — |

External users (not in the PM portal, but powered by it): **Tenant**, **Landlord**, **Prospect/renter**, **Contractor** — see section 11.

Permissions: PM sees own portfolio + team; lead sees all; on-call sees all emergencies. Every action logged with actor (human or AI).

---

## 3. Human-in-the-loop model

### 3.1 Autonomy levels (set per workflow, overridable per landlord, property, thread or job)
| Level | Name in UI | Behaviour |
|---|---|---|
| 3 | **Autopilot** | AI acts and sends; PM sees it in the log. Undo window on outbound messages (default 60s, configurable). |
| 2 | **Draft for me** | AI drafts replies/actions; PM approves with one click (or edits). |
| 1 | **Tell me** | AI only summarises and suggests; PM does it. |
| 0 | **Paused** | AI does nothing on this item (human has taken over). |

Defaults: maintenance routine = Autopilot; maintenance urgent = Autopilot with notifications; emergencies = Autopilot for safety steps **plus mandatory human alert**; landlord money/approval messages = Draft for me; legal/complaints = Tell me; lettings answers from KB = Autopilot; tenant selection = Tell me (landlord decides).

### 3.2 Always-human decisions (code-enforced, cannot be set to Autopilot)
- Legal threats, formal complaints, council/environmental health notices, disrepair claims, tribunal letters.
- Disputed liability (tenant vs landlord vs contractor).
- Landlord instructions that are unlawful or unsafe.
- Anything about possession/eviction, arrears enforcement beyond reminders, Breathing Space, hardship.
- Domestic abuse, harassment, illegal eviction reports (these are also emergencies).
- Unverified identity asking for personal data; bank detail changes (landlord or contractor).
- Spend over limit with landlord unreachable past deadline.
- Third failed visit on the same issue; contractor damage; cost >X% over quote.
- Tenant selection (landlord chooses from ranked shortlist).
- Fraud signals on applications.

### 3.3 Take over / Hand back
- **Take over** button on every thread, job, viewing, prospect: sets autonomy to Paused for that item, shows "You're handling this" banner, AI stops sending; AI still drafts suggestions in a side panel if wanted.
- **Hand back to AI**: PM writes optional instruction ("Book Dave for Tuesday, then carry on"); AI resumes from the current state with that instruction in its context.
- Collision guard: if two humans open the same item, show who's on it.

### 3.4 Every AI action card shows
- What it did / wants to do (one line).
- **Why** (2–3 bullets) + **facts used** with KG source links (tenancy record, message, photo, management agreement).
- Confidence (High / Medium / Low) — Low always routes to Draft-for-me at minimum.
- Buttons: **Approve**, **Edit**, **Reject (with reason)**, **Take over**.
- Rejections and edits are logged and used as feedback for the agent.

### 3.5 Handover note (fixed format, appears on every escalation)
1. What happened (2 lines)
2. Facts and where they came from
3. What the AI already did, and results (incl. failures)
4. What's pending / waiting on whom
5. Recommended next step
6. Urgency (P0/P1/P2) and deadline
7. Contacts (one-tap call/SMS)

Target: a human can act within **10 seconds** without reading the thread.

---

## 4. Information architecture and navigation

**Left nav:**
1. **Today** — needs-you queue, emergencies, today's jobs and viewings, KPIs
2. **Inbox** — all conversations (tenants, landlords, prospects, contractors)
3. **Maintenance** — board, list, job details
4. **Viewings** — pipeline, trips, follow-ups
5. **Calendar** — everything with a time
6. **Availability** — who we're waiting on for times
7. **Properties** — property 360
8. **People** — tenants, landlords, prospects
9. **Contractors** — trusted list and performance
10. **Compliance** — certificates, inspections
11. **Money** — rent, invoices, statements (lighter in v1)
12. **Settings**

**Global top bar:** search / command bar (⌘K: "job at 12 Elm Rd", "call Priya", "new viewing"), **Needs you** counter, **Emergency** indicator (red, pulses when any open P0), notifications bell, user menu, autonomy quick-toggle (global pause for incidents).

**Persistent emergency banner:** any open emergency shows a red bar at the top of every page with the job, time since report and current step, linking to the job.

---

## 5. Screen specs

### 5.1 Today (home)
**Purpose:** answer "what needs me right now?" in five seconds.

Sections (top to bottom):
1. **Emergencies** (if any): red cards with progress card mini-view, time since report, on-call owner.
2. **Needs you** queue — sorted by priority then deadline. Each row: flag chip, one-line summary, property, waiting time / SLA countdown, primary action button (Approve / Reply / Decide / Call). Types:
   - Approvals (spend over limit, guided messages in Draft mode, contractor choice when no match)
   - Escalations (handover notes)
   - Low-confidence AI drafts
   - Landlord decisions overdue (chase status)
   - Failed actions the AI couldn't recover
3. **Today's schedule** — maintenance visits and viewings (agent-led and self-guided) on a timeline; risks highlighted (unconfirmed tenant, contractor running late).
4. **AI activity summary** — "Since 8am: 37 messages answered, 9 jobs booked, 3 escalations, 1 emergency handled" with link to the log.
5. **KPIs strip** — open jobs by stage, average time to book, no-show rate this week, emergencies handled, tenant rating, enquiries → viewings → applications funnel.

### 5.2 Inbox
**Purpose:** one inbox across tenants, landlords, prospects and contractors, all channels (email, WhatsApp, SMS, phone transcripts, portal messages, voice-agent calls).

**Layout:** three panes.
- **Left — list**
  - Tabs: **Needs you** · **All** · **Tenants** · **Landlords** · **Prospects** · **Contractors** · **AI handling** · **Closed**
  - Filters: property, flag, priority, channel, category (from the issue spreadsheets), SLA breached, assigned to me, language.
  - Row: sender avatar + role chip (Tenant/Landlord/…), property, subject/summary (AI one-liner), last message snippet, channel icon, flags, SLA timer, status chip: *AI replied* / *AI draft waiting* / *Waiting on them* / *You're handling* / *Escalated*.
- **Middle — thread**
  - Messages from all channels in one timeline (channel icon per message); call recordings with transcript; photos inline with AI photo analysis ("Shows damp patch near window, close-up needed").
  - System events inline: "AI classified as Repair → Water leak (Urgent)", "Job #431 created", "Callback placed (2m 14s)".
  - **AI draft box** at the bottom (when autonomy = Draft): editable text, tone toggle (warmer/shorter), language, channel picker, **Send**, **Regenerate**, **Discard**. Shows "Why this reply" and facts used.
  - **Take over / Hand back** toggle at the top.
  - Quick actions: create job, create viewing, send form link, request availability, call now (voice agent or PM), escalate, merge thread, split thread, mark spam.
- **Right — context panel (from KG)**
  - Who: name, role, verified ✓/✗, contact, language, vulnerability flag (with consent), communication preference.
  - Property: address, tenancy dates, rent status, landlord, management level, spend limit.
  - Related: open jobs (mini progress cards), upcoming viewings, recent tickets, documents (gas cert, EPC…).
  - Matched issue type from spreadsheet with **Suggested handling**, **Urgency**, **Key rules/notes** — shown as "Playbook" card.
  - Flags with reasons.

**Behaviour:**
- Unknown sender → AI replies asking for name, address, phone; safety screen still runs; thread flagged "Unverified".
- Messages covering two topics → AI proposes split (e.g. leak + rent question).
- Repeat messages from the same person in a short time → urgency signal, flag "Repeated contact".
- SLA: target reply times per category (configurable); breached = red timer.
- Landlord threads: bank detail change requests auto-flag **Fraud check** and block until verified by phone.
- Every outbound AI message has an undo window in Autopilot.

### 5.3 Maintenance

#### 5.3.1 Board
Kanban columns matching progress stages (section 6): **New** · **Collecting details** · **Needs approval** · **Booking** · **Scheduled** · **In progress** · **Checking fix** · **Reporting** · **Done**. Emergency lane pinned at top across all columns.
Card: property, issue (from spreadsheet name), urgency chip (Emergency/Urgent/Routine), waiting-on chip (Tenant/Landlord/Contractor/Us), time in stage vs SLA bar, contractor avatar, flags. Drag between columns = manual override (logged, asks for reason).
Views: Board / List / Map (jobs by location, contractor routes) / Calendar.

#### 5.3.2 Job detail
Header: issue name, property, tenant, urgency (editable with reason), status, autonomy level (per job), **Take over**.
Main column:
1. **Progress card** (section 6) — big, at top.
2. **Next automatic action** — "AI will chase the landlord by phone at 15:30" with **Do it now** / **Skip** / **Change**.
3. **Decision points** (human-in-the-loop checkpoints, each with Approve/Override):
   - Urgency decision (with reasons, tripwire words found, photo analysis, vulnerability)
   - Emergency check result ("Confirmed: smell of gas reported on call") before telling tenant to call emergency services
   - Liability (who pays) with evidence
   - Spend vs landlord limit; approval request status; emergency override used?
   - Contractor choice (top 3 ranked with reasons) — PM can pick a different one
   - Slot proposal (tenant windows × contractor offers)
   - Completion check (photos vs report vs quote) and tenant confirmation
4. **Timeline / audit log** — every event, actor (AI/human/tenant/landlord/contractor), channel, result, failures and retries.
Side column:
- Tenant card (availability windows, access consent, pets, alarm, vulnerability flag).
- Photos gallery with AI analysis and "Ask for better photo" button.
- Fixflo-style issue details + extra questions answered.
- Costs: estimate, quote(s), approved amount, final invoice, variance.
- Contractor card: name, trade, Gas Safe no., rating, ETA, contact.
- Documents: quotes, invoices, before/after photos, report PDFs.
- Linked: thread(s), previous jobs on this property (repeat-fault warning).

Manual controls (always available): change urgency, pause automation, call tenant (voice agent or me), call contractor, swap contractor, reschedule, add note, attach file, cancel job (reason required), reopen, mark tenant responsibility (requires evidence + confirmation dialog), send report now.

#### 5.3.3 Emergency mode
- Triggered by tripwire words, voice callback, emergency check, or PM.
- Full-width red header; steps checklist live: Safety message sent ✓ → Emergency check confirmed ✓ → Contractor dispatched (accepted in 6m) ✓ → On-call alerted ✓ → Landlord notified ✓ → Made safe ☐.
- Spend limit and approvals bypassed (shown as "Emergency override — landlord notified").
- Timer since report; escalation if contractor not accepted in 15 min or nobody within 1h.

### 5.4 Viewings and lettings

#### 5.4.1 Prospect pipeline
Columns: **Enquired** · **Profile done** (auto-account + discovery interview) · **Availability received** · **Viewing booked** · **Viewed** · **Applied** · **Referencing** · **Shortlisted** · **Accepted** · **Contract sent** · **Signed / moving in**. Side lanes: **No-show — rebooking**, **Not a fit — recommended other homes**, **Waitlist / alerts on**.
Card: name, budget, move-in date, must-haves chips, matched properties count, next step, flags.

#### 5.4.2 Prospect detail
- Profile (auto-created after first contact; reused everywhere; renter can edit/delete): contact, household size (for occupancy limits only), budget, areas, move date, must-haves/deal-breakers, pets, **weekly availability** (recurring windows + exceptions), ID/selfie verification status, documents.
- Discovery interview transcript + summary.
- Matched properties with match score and reasons.
- Viewings history (attended / no-show), feedback, questions asked.
- Applications (one-tap, pre-filled), referencing status, recommendations sent.
- Thread (same as inbox).

#### 5.4.3 Trip builder (multi-property viewings)
**Input:** prospect's weekly availability + matched properties + each property's viewing rules (5.7) + agent diaries + travel times.
**Output:** AI proposes 1–3 trips, e.g. *Tue 18:00 Flat A (self-guided) → 18:30 Flat B (agent) → 19:00 Flat C (agent)*, with travel time between, map, and conflicts.
Actions: **Approve & send** (prospect gets one confirmation with all slots + calendar invite), swap a property, change times, choose agent, split into separate days.
Also: **opportunistic fill** — when a new matching property is listed or a slot frees, AI proposes adding it to an existing trip; PM approves (or Autopilot).
Batching for agents: cluster viewings per area into blocks; show agent route for the day.

#### 5.4.4 Viewing detail
- Mode: Agent-led / Self-guided (vacant only) / Video.
- Status: Proposed → Confirmed → Reminded (T-24h, T-2h, call if unconfirmed) → Checked in → Attended / No-show.
- Self-guided panel: ID verified ✓, access code (time-limited, revealed only on arrival), lock events (door opened/closed/locked), voice tour status, "I'm done" received, door locked confirmed.
- Agent-led panel: briefing card (prospect needs, questions, objections), occupied-property tenant notice status, lone-worker check-in/out.
- **No-show loop**: auto-detected → SMS within 10 min with new slots from saved availability → call after 2h → rebook; after 2 automatic reschedules require a confirmation call. Visible as a mini progress strip.

#### 5.4.5 Follow-up after viewing → contract
Automated sequence with visible progress and controls:
1. Within minutes: thank-you + "any questions?" → answers from property knowledge base.
2. Feedback (1–5 + what they liked/didn't).
3. **Application link** (one-tap, pre-filled from profile).
4. Not interested → recommend other matching homes + offer trip.
5. Interested but not applying → nudges at 24h and 72h, then stop.
6. After applying → recommend other relevant homes they can also apply to (one tap).
7. Referencing → ranked shortlist using landlord priorities → **landlord decides** (one tap).
8. Accepted → **holding deposit** request (max 1 week's rent) → **tenancy agreement sent for e-signature** → deposit protection + prescribed info → check-in and keys.
UI: a horizontal "Let progress" bar per prospect-property pair, mirroring the maintenance progress card style.
Legal guard: contract/holding deposit only after landlord accepts; max 1 month rent in advance; never invite offers above advertised rent (UI blocks "offers over" wording and bid fields).

#### 5.4.6 Application review
- Gates first (pass/fail): identity, Right to Rent, occupancy limit.
- Then ranking by **landlord's tenant priorities** (weights shown), default: affordability → referencing risk → fit; tie-break: first complete application.
- Each applicant card: affordability (income vs 30× monthly rent rule, guarantor), references, credit summary, risks, missing items, fraud signals.
- **Excluded from ranking (UI shows "not used"):** offers above rent, rent upfront, benefits, children, protected characteristics.
- Send top 3 to landlord with reasons; landlord picks.

### 5.5 Calendar (unified)
- Views: Day / Week / Month / Agenda; **per-agent lanes**, **per-property lanes**, **per-contractor lanes**.
- Layers (toggle): Viewings (agent-led / self-guided), Maintenance visits, Emergency call-outs, Inspections, Compliance checks (gas, EICR…), Tentative holds, Tenant availability windows (shaded), Contractor availability, Property viewing blackout times.
- Drag to reschedule → AI notifies all parties and asks for confirmation; conflicts highlighted (double booking, outside tenant consent window, travel time impossible).
- Click empty slot → create viewing/visit with AI suggestions.
- Colour by type; urgency border; unconfirmed = dashed outline.
- Sync: export iCal per user; tenant/contractor invites sent from here.

### 5.6 Availability hub
**Purpose:** kill scheduling ping-pong; show whose times we're waiting for.
Tabs:
- **Tenants (repairs):** jobs waiting for tenant availability; request status (sent / opened / answered / chased / called); saved weekly windows; access-without-me consent.
- **Prospects (viewings):** availability requested / received; trips proposed.
- **Contractors:** offers sent (2–3 concrete slots by phone/SMS/email in parallel), replies parsed ("maybe Thursday" → tentative + follow-up), first-accept-wins, others told "taken, thanks".
**Auto-scheduler panel** per job: tenant windows × contractor offers → matched slot → tentative calendar hold for tenant → confirm both → 24h notice. PM sees each step, can override.
Bulk actions: "Ask all tenants with open jobs for availability", "Re-offer slots to next contractor".

### 5.7 Properties (property 360)
- Header: address, photo, type, beds, tenancy status (Let / Vacant / Marketing / Notice given), landlord, management level, spend limit, open flags.
- Tabs: Overview · Tenancy · Maintenance (history, repeat faults) · Viewings & lettings · Compliance · Documents · Money · Knowledge (KG facts) · Timeline.
- **Viewing rules & special flags (editable):**
  - Occupied — current tenant consent required; minimum notice (e.g. 24h); tenant's allowed windows
  - Vacant — self-guided allowed? (smart lock / key safe installed; insurer OK)
  - Access: key safe location, smart lock ID, alarm code (masked, revealed to authorised agent only), parking, entry instructions
  - Viewing blackout times (e.g. no viewings before 10:00, not Sundays)
  - Pets in property / allergy note
  - Accessibility (lift, stairs, step-free)
  - Max viewers per slot; open-house allowed
  - Safety notes (lone worker caution, dog on site)
  - Landlord preferences (lawful only) and tenant priorities
- Knowledge tab: property facts the AI answers from (broadband, bills, bins, heating type, boiler make/model + manual link, stopcock location, fuse box location, appliance list with manuals), each with source and last updated; "Unknown" items queued for a human to fill.

### 5.8 People
- **Tenants:** profile, tenancy, contact prefs, language, vulnerability (consented), availability, rent status, tickets, jobs, documents, rating.
- **Landlords:** properties, spend limits, approval preferences, update frequency/channel, tenant priorities, verified bank (masked), statements, approvals history, response times.
- **Prospects:** see 5.4.2.
- Identity verification state everywhere (✓ verified / ⚠ unverified).

### 5.9 Contractors
- Trusted list (5–10 per area per trade): trades, areas, Gas Safe/electrical certs + insurance with expiry dates (auto-alert before expiry), rates, emergency/out-of-hours yes/no, preferred channel.
- Scorecard: response time, on-time %, first-time fix %, tenant rating, cost vs quote, photo/report quality, jobs this month (fair spread).
- Backup list; landlord-preferred contractors; "do not use" per landlord.
- Contractor detail: jobs, calendar, availability, documents, notes.

### 5.10 Compliance and inspections
- Calendar of certificates per property: gas safety (12 months), EICR (5 years), EPC (min E), smoke/CO alarms, licences (HMO/selective), boiler service.
- Status chips: Valid / Due in 60 days / Due in 14 days (red) / Expired (blocking).
- Auto-booking runs through availability + contractor scheduling; PM sees and can override.
- Inspections: schedule (every 3–6 months + annual), room-by-room checklist, photos, findings → new maintenance jobs automatically; landlord condition report.
- Letting gate: property cannot be published (Viewings) while hard-block items are invalid.

### 5.11 Money (lighter in v1; accounting is in scope)
- Rent: received / late / arrears per property; daily reminders + AI calls on day 1, 3, 7 (firm but fair; one call/day max; true consequences only; vulnerable or hardship → human).
- Contractor invoices: AI reads invoice → matches job + approved amount + tenant fix confirmation → ready to pay; mismatches held with flag.
- Landlord statements: monthly per property; yearly summary.
- Deposits: registration within 30 days; end-of-tenancy deductions with evidence; disputes → scheme.
- Non-Resident Landlord scheme flag for overseas landlords.

### 5.12 Settings
- **Autonomy** per workflow (table: workflow × level), per landlord overrides.
- **Spend limits** default + per landlord (from management agreement); emergency override on/off (default on).
- **SLAs**: reply targets per category; chase timings (landlord approval 24h chase / 48h escalate; tenant form 24h reminder / 48h call; contractor 4h urgent / 24h routine).
- **Escalation routing**: on-call rota, P0/P1/P2 channels (push/SMS/call), quiet hours (never for P0).
- **Templates**: message templates per event/channel/language; tone.
- **Voice agent**: voice, call windows, max call attempts, scripts (urgency callback, scheduling, no-show, rent reminder), recording consent wording.
- **Guided self-fix list** (Fix it with me): enabled fixes.
- **Data**: retention schedule, consent texts, deletion requests.
- **Integrations**: email, WhatsApp, SMS, telephony, calendar, smart locks, e-sign, referencing, portals (Rightmove/Zoopla), accounting.

---

## 6. The maintenance progress card (Uber-style)

### 6.1 Stages (standard repair)
| # | Stage (PM label) | Tenant-facing label | Waiting on | Typical auto-action |
|---|---|---|---|---|
| 1 | Reported | "We've got your report" | — | Safety screen, classify |
| 2 | Collecting details | "Tell us a bit more" | Tenant | Pre-filled form, photo check, chase 24h, call 48h |
| 3 | Triaged | "Assessed: Urgent — aim 1–3 days" | Us | Urgency + who pays |
| 4 | Landlord approval *(only if over limit)* | "Getting approval" | Landlord | One-tap request, chase 24h, escalate 48h |
| 5 | Finding a contractor | "Finding the right person" | Contractors | Offer 2–3 slots to top contractors |
| 6 | Scheduled | "Booked: Tue 18:00–19:00, Dave (Plumber)" | — | Calendar hold → confirmed, 24h notice |
| 7 | Confirmed by tenant | "You're confirmed" | Tenant | T-24h + morning reminders, call if unconfirmed |
| 8 | On the way | "Dave is 12 min away" (photo, ETA) | Contractor | ETA updates |
| 9 | In progress | "Work in progress" | Contractor | — |
| 10 | Fixed? | "Is everything working?" | Tenant | One-tap yes/no; no → reopen |
| 11 | Report sent | "All done — here's what we did" | — | Landlord report (with costs) + tenant report (no costs) |
| 12 | Closed | "Closed" | — | Rating request, invoice to accounts |

Branch stages shown inline when they happen: **Fixed by you** (guided self-fix — skips 4–9), **Rescheduled**, **No-show (tenant/contractor)** with rebook loop, **Waiting for parts**, **Second visit needed**, **Referred to block manager** (communal), **Tenant responsibility** (offer paid booking), **Escalated to a person**, **Paused by PM**.

### 6.2 Emergency variant
Reported → **Safety steps sent** → **Emergency confirmed** (emergency-check skill) → **Make-safe dispatched** → **On the way (ETA)** → **Made safe** → then continues at stage 3 for the full repair. Red styling, live timer, on-call owner avatar.

### 6.3 What each stage shows
- Status dot (done ✓ / current ● pulsing / upcoming ○ / blocked ✕ red / skipped –).
- Timestamp + actor for completed stages.
- For current stage: **waiting on** chip, **time in stage vs SLA** mini bar (green → amber → red), **next automatic action and when** ("Chasing landlord by phone in 2h"), **Do it now** / **Take over**.
- Expand a stage → its events, messages, documents.

### 6.4 Three audiences, one card
- **PM view:** all stages, costs, internal notes, decisions, controls.
- **Landlord view:** stages incl. approval and costs, photos, report, invoice.
- **Tenant view:** simplified labels, contractor name/photo/ETA, confirm/reschedule buttons, never costs or landlord details. Shareable link (magic link, no login) sent by SMS.

### 6.5 Visual
Horizontal stepper on desktop, vertical on mobile; current step large with live detail (map ETA when "On the way"); colour by health: on track (green), at risk (amber), blocked (red), emergency (red header).

---

## 7. Workflows the portal must reflect

The agent runs these; the portal shows them and offers control at each decision point.

### 7.1 Tenant ticketing (TT1–TT10)
1. Message comes in (any channel) → saved, transcribed, translated.
2. Identify sender and property; unknown → reply asking for name, address, phone; still safety-screen.
3. Group with related messages; merge flatmate reports; split multi-topic messages.
4. **Check for danger first** (tripwire words, vulnerability, repeated contact, urgent wording, capitals, late-night).
5. Classify against the **Tenant issues spreadsheet** (716 repairs + 100 other enquiries) → playbook (handling, urgency, rules).
6. Route: repair → maintenance; "Agent answers" → answer; "Agent gathers info, human decides" → collect + handover; "Human only" → acknowledge + escalate.
7. Answer from records (tenancy, ledger, documents, property knowledge); unknown → say so, escalate, save answer.
8. Gather details and hand over (handover note), tell tenant who decides and when.
9. Chase (internal SLA; tenant reminders 1 day, 3 days).
10. Close, rating, learn (new Q&A to knowledge base; repeat-issue flag per property).

### 7.2 Maintenance (MT1–MT15)
1. **First-touch screen**: any sign of urgency (danger words, vulnerability, issue type urgency from spreadsheet, repeat messages, wording) → voice callback; otherwise form.
2. **Voice urgency callback** (within ~2 min): danger now? gas/burning? water near electrics? getting worse? who's home? only toilet/heating? No answer → SMS + retry 10 min → escalate P1.
3. **AI form**: pre-filled; only missing questions; safety questions; access + weekly availability; **always ask for photos** for visible problems (never block an emergency on photos); **AI checks every photo** (right thing, close enough, in focus, shows what a contractor needs, matches description, recent) and asks for a specific re-take; appliances: ask make/model or read from label photo (no dropdowns). Chase 1 day, call 2 days.
4. **Urgency decision**: answers, photos, history, who lives there, weather, time; spreadsheet urgency is the starting level; extra signals raise it; slight suspicion → callback; photos never lower urgency; when unsure pick higher.
5. **Fix it with me** (guided self-fix by voice, approved safe list only; auto-finds the appliance manual online from make/model; stops on any red flag; fixed → close; not fixed → book while on call).
6. **Emergency**: **emergency-check** first (clear danger signs only: gas smell, smoke/fire, water in electrics, ceiling coming down, someone hurt; seconds not minutes; never stop someone calling 999) → confirmed: safety instructions by call + SMS (gas → leave, no switches, 0800 111 999; fire → 999; water → stopcock), dispatch make-safe from trusted list (emergency-capable only), alert on-call, notify landlord; not confirmed → always-safe steps, treat as urgent.
7. **Who pays and cost** (serious emergencies skip this until after make-safe): landlord (structure, installations, wear and tear) / tenant (damage, misuse per agreement) / communal (block manager) / warranty first; quote or rate card; disputes → human.
8. **Landlord OK if needed**: over limit → one-tap request with quote/photos/recommendation; chase 24h; escalate 48h; refusal of legal repair → human with legal note.
9. **Pick and book contractor**: trusted list (5–10 per area); filter (trade, qualification, area, valid certs/insurance today, emergency capability, landlord preferences/blocks, warranty provider first); rank (track record, knows the flat, distance, price, workload, fair spread); offer 2–3 concrete slots by phone/SMS/email in parallel; first accept wins; tenant calendar hold; 24h notice; none → backups + human; update track record after each job.
10. **Reminders**: day before + morning of; call if unconfirmed; contractor name/photo/ETA; no-show → rebook; third failed visit → human.
11. **Contractor finishes**: report, parts, cost, cause, before/after photos; check consistency; over quote/damage/mismatch → human.
12. **Tenant confirms fix**; invoice paid only after.
13. **Reports and close**: landlord (with costs) and tenant (no costs); repeat-fault flag.
14. **Planned safety checks** (calendar; book 1–2 months ahead; <2 weeks unbooked → human).
15. **Inspections** (3–6 months + annual; findings → new jobs; landlord condition report).

### 7.3 Landlord ticketing (LT1–LT8)
1. Receive and verify (new email or bank change → phone verification; fraud risk).
2. Classify: becoming a client; rent; letting; repairs; getting ready to let; certificates; money; tenancy changes; big decisions; account changes; legal trouble; complaints. Match to **Landlord enquiries spreadsheet** (91 items) for handling and urgency.
3. Answer from records (rent ledger, listing stats, job timeline, certificates); would-be landlords → rent estimate, fees, legal checklist, offer visit → onboarding; tax/money → facts only.
4. Approvals (repair spend, tenant requests, rent, tenant choice) → one tap; chase 24h; escalate 48h; emergencies never wait.
5. Say no to unlawful/unsafe requests (second rent rise in a year, "no DSS/no kids", refusing legal repair, eviction without grounds, entering without notice, keeping deposit without proof, bidding, >1 month rent upfront); **illegal eviction ("change the locks") = emergency**, human now.
6. Rent increases (Section 13, once a year, 2 months' notice, market rent) and tenancy changes; selling/moving in (Section 8 ground, 4 months' notice, not in first 12 months) → human; arrears possession → courts only, human; deposit endings with evidence.
7. Proactive updates (rent in/late, job approved/done, certificate due, viewing feedback, offer accepted) + monthly summary; landlord chooses channel/frequency.
8. Close and log; repeat questions → portal features.

### 7.4 Letting and viewings (LV1–LV13)
1. Instruction + **landlord tenant priorities** (lawful only; weights).
2. Compliance gate (EPC E+, gas, EICR, alarms, licence, deposit scheme, info sheet) — blocks publishing.
3. Pricing: one fixed advertised rent; no bidding.
4. Listing creation from property data + material info; wording lint (no "no DSS", "no kids", "professionals only", banned fees, "offers over").
5. Landlord approves; publish (Rightmove, Zoopla, OnTheMarket, site, To Let board with QR); property knowledge base.
6. Enquiry → instant reply → **auto account/profile** → **voice discovery interview** → match all listings.
7. Viewing booking: **weekly availability once**; slots in first reply; **multi-home trips**; ID + selfie; reminders; auto-offer new matching slots.
8. Viewing: agent-led (briefing card, tenant notice, lone-worker) or self-guided (vacant; "I'm here" → slot code → voice tour → "I'm done" → lock confirmed).
9. **Attended?** → no-show reschedule loop (SMS 10 min, call 2h, rebook; 2 auto-reschedules then confirmation call) | follow-up: questions, application link, rating, other homes.
10. One-tap application (profile reused); checks (ID, Right to Rent, income, credit, references, address history; guarantor); chase docs; recommend other homes after applying.
11. Rank with landlord priorities after legal gates; landlord chooses.
12. Holding deposit (max 1 week; only after landlord accepts; 15-day deadline) → e-sign → rent upfront max 1 month after signing → deposit protected within 30 days + prescribed info → certificates served → check-in, keys, rent setup, welcome pack (how to report repairs).
13. Weekly landlord updates while marketing; price changes need landlord OK.

### 7.5 Accounting (AC1–AC7)
Rent matching; late rent (daily reminders, AI calls day 1/3/7, late fee only after 14 days capped at 3% above base rate, hardship/Breathing Space → human, possession → human); contractor invoices (match job + approval + tenant fix confirmation; changed bank details → hold); pay contractors and landlords (NRL scheme); monthly statements; deposits and client money; year-end summary.

---

## 8. Escalation rules and flag catalogue

### 8.1 Four outcomes (decided in code)
1. **Act alone** — routine, reversible, under limit, clear liability, verified identity.
2. **Act and alert a person** — emergencies.
3. **Ask for info** — gaps a message or call can fill.
4. **Stop and hand over** — always-human list (3.2), unresolved conflicts, low confidence on consequential actions.

### 8.2 Priority levels
| Level | Meaning | Delivery | Examples |
|---|---|---|---|
| **P0** | Danger to life / security now | Push + SMS + phone call to on-call; persistent red banner | Gas smell, fire, uncontrolled leak, no power, can't secure property, illegal eviction, domestic abuse |
| **P1** | Within the hour | Push + inbox top | Vulnerable tenant with risk, security issue, legal threat, unconfirmed emergency callback, emergency contractor not found |
| **P2** | Same day | Needs-you queue | Liability dispute, landlord no reply 48h, cost over quote, third failed visit, fraud signal |
| **Info** | FYI | Activity log | AI handled, overrides used |

### 8.3 Flag catalogue (chip, colour, meaning)
| Flag | Colour | Raised when |
|---|---|---|
| Emergency | Red | Tripwire/confirmed emergency |
| Needs your OK | Amber | Approval required (spend, Draft mode, contractor choice) |
| Human only | Purple | Always-human category (legal, possession, complaint…) |
| Vulnerable | Pink | Vulnerable occupant (consented) |
| Unverified | Grey | Sender identity not confirmed |
| Fraud check | Red outline | Bank detail change, document mismatch, application fraud signals |
| Repeated contact | Amber outline | Multiple messages/calls in short time |
| SLA breached | Red outline | Over target time |
| Low confidence | Grey outline | AI unsure; draft needs review |
| Conflict | Amber | Sources disagree (tenant vs record vs landlord) |
| Waiting on landlord / tenant / contractor | Blue | Who holds the ball |
| No-show | Amber | Missed visit/viewing |
| Repeat fault | Amber | 3rd job same issue/property |
| Over quote | Amber | Final cost > quote by X% |
| Compliance due | Amber/Red | Certificate due/expired |
| Unlawful request | Purple | Landlord asked for something illegal |
| Paused / You're handling | Black | Human took over |

### 8.4 Signals that raise urgency (shown as "why" chips on jobs/tickets)
Danger words (gas, burning, sparks, smoke, flooding, ceiling sagging/coming down, water in lights/sockets, can't lock, CO alarm, sewage); vulnerability words (baby, elderly, pregnant, disabled, medical equipment, asthma, ill); trajectory ("getting worse", "spreading", "faster"); urgency words ("urgent", "emergency", "help", "can't"); capitals; repeat messages/calls; late-night contact; cold weather + heating loss; only toilet/heating; hedged danger ("probably nothing but…").

---

## 9. Voice agent in the portal

- **Calls list** (per job/thread/prospect): purpose (urgency callback, scheduling, no-show, rent reminder, discovery interview, contractor booking, guided self-fix, self-guided viewing tour), status, duration, outcome, recording + transcript, extracted answers, follow-up actions.
- **Live call view**: real-time transcript, extracted facts appearing as chips, suggested next question, **Join call** (warm handover) and **Take over call** buttons; emergency keywords highlight red.
- **Warm handover**: AI briefs the human in 15s before connecting ("Priya Shah, 12 Elm Road, ceiling leak near light, stopcock off, toddler home, plumber ETA 10:15").
- **Call now** buttons everywhere (tenant, landlord, contractor) — choose "AI calls" or "I call".
- Failed calls fall back to SMS automatically; shown in timeline.
- Language: AI switches to the person's language; transcript shows both.

---

## 10. Delight features (crowd-pleasers)

1. **Uber-style progress card** for every repair (section 6) — shared live link for tenant and landlord.
2. **Fix it with me** — voice-guided self-fix with auto-found manual and step pictures; "call-out avoided" counter.
3. **Photo coach** — AI rejects a blurry kitchen shot: "Could you send a close-up of the pipe under the sink?"; reads boiler make/model from label.
4. **Buried emergency highlight** — in the thread, the dangerous sentence is highlighted red with the actions it triggered.
5. **Contractor race** — live view of offers going out and replies coming in; first accept locks; others told "taken, thanks".
6. **One-tap landlord approval** — mobile card: "Boiler repair £420 — over your £300 limit. Approve?"
7. **Calendar block appears** in the tenant's calendar automatically.
8. **No-show save** — morning call: "Still home for 9am?" → rebooks instantly.
9. **Same job, two reports** — side-by-side landlord (costs) vs tenant (no costs).
10. **Multi-home trip** — three nearby flats in one evening from one availability answer.
11. **Language switch** — tenant writes in Polish; agent replies in Polish; contractor gets English.
12. **Overnight scoreboard** — "While you slept: 24 cases handled · 6 emergencies caught · 3 call-outs avoided · 0 missed".
13. **Escalation inbox** — 10-second handover notes with **Take it**.
14. **Properly mascot** — the blinking character appears in empty states, loading and the AI avatar (eyes look toward the thing that needs attention).

---

## 11. Tenant and landlord portals (external views)

Powered by the same records; magic-link access (no password), mobile-first.

### 11.1 Tenant portal
| Screen | What tenant does/sees | Workflow |
|---|---|---|
| Report a repair | Chat-style AI form, photos, safety questions | MT1–MT3 |
| Track a repair | Progress card (tenant labels), contractor name/photo/ETA | MT9–MT13 |
| My availability | Usual weekly windows, access consent, pets, alarm | MT3, MT9 |
| Confirm or rearrange | One-tap visit confirmation; "Is it fixed?" | MT10, MT12 |
| Messages | One thread per topic, any language | TT |
| Documents | Tenancy, gas cert, EPC, EICR, deposit certificate, info sheet | TT7, MT14 |
| Rent | Balance, history, statement, pay | AC1 |
| Requests | Pets, alterations, sublet, notice | TT8, LT4 |
| My details | Contact, consent, delete my data | SF |

### 11.2 Landlord portal
| Screen | What landlord does/sees | Workflow |
|---|---|---|
| Overview | Rent in, arrears, next payout, open jobs, compliance | LT3, AC |
| Approvals | One-tap: spend, tenant requests, rent, tenant choice | LT4, MT8, LV11 |
| Repairs | Progress cards with costs, photos, invoices, reports | MT11–MT13 |
| Certificates | Due dates, bookings | MT14 |
| Letting | Listing stats, viewing feedback, shortlist | LV5, LV13, LV11 |
| Tenant priorities | Weights for tenant selection (lawful only) | LV1 |
| Statements | Monthly/annual, invoices | AC5, AC7 |
| Messages & settings | Questions; update channel/frequency | LT1, LT7 |

### 11.3 Prospect (renter) app
Profile (auto-created), weekly availability, matched homes, trips, viewing check-in ("I'm here"), self-guided access code, application (one tap), application status, recommendations.

### 11.4 Contractor view
Job offers with slots (accept by tap/SMS/voice), job details (photos, access, tenant contact), on-the-way button (ETA), completion form (photos before/after, work done, parts, cost), invoice upload.

---

## 12. UK legal guardrails the UI must enforce (England, Oct 2026)

- **Renters' Rights Act (phase 1, 1 May 2026):** no Section 21; periodic tenancies; rent increase once a year via Section 13 with 2 months' notice, tenant can challenge; advertised fixed rent, no bidding (UI has no "offers" field, blocks "offers over"); max 1 month rent in advance, not before signing; no blanket bans on benefits or children; pet requests considered reasonably; selling/moving-in grounds need 4 months' notice and not in first 12 months; arrears possession mandatory ground threshold raised (3 months). Later phases (landlord database, ombudsman, Decent Homes, Awaab's Law extension) — keep configurable.
- **Tenant Fees Act 2019:** most fees banned; holding deposit ≤ 1 week's rent; deposit ≤ 5 weeks (6 if annual rent ≥ £50k); late fee only after 14 days, capped at 3% above BoE base rate; lost keys = reasonable cost.
- **Deposit protection** within 30 days + prescribed information.
- **Right to Rent**: check every adult, same process for all.
- **Equality Act**: no discrimination; reasonable adjustments.
- **Repairs (LTA 1985 s.11)**: landlord repairs structure, exterior, water, gas, electricity, sanitation, heating, hot water.
- **Access**: ≥24h written notice, reasonable times (except emergencies).
- **Gas**: Gas Safe engineers only; gas smell → National Gas Emergency 0800 111 999.
- **Compliance**: gas safety 12 months; EICR 5 years (remedials within 28 days); smoke alarm each storey, CO alarm with fixed combustion appliances; EPC E minimum.
- **Harassment**: debt chasing must not cause alarm/distress; true consequences only; reasonable hours; max one call per day.
- **UK GDPR**: verify before disclosing; consent for referencing/credit; retention schedule; subject access within one month.
- **Illegal eviction** is a criminal offence → emergency escalation.
- UI shows a short "Why we can't do that" explainer when blocking a request; legal notes are guidance, not legal advice.

---

## 13. Data model

Core entities (fields abridged; all have `id`, `created_at`, `updated_at`, `source_refs[]` linking to KG nodes):

- **Property**: address, geo, type, beds, status (let/vacant/marketing/notice), landlord_id, management_level, spend_limit, emergency_override (bool), viewing_rules {occupied, consent_required, min_notice_h, allowed_windows[], blackout[], self_guided_allowed, lock_id, key_safe, alarm_code_ref, parking, accessibility, pets_on_site, max_viewers, safety_notes}, knowledge_facts[], compliance_items[].
- **Tenancy**: property_id, tenants[], start, type (periodic), rent, deposit {amount, scheme, protected_at}, rent_status, documents[].
- **Person**: role (tenant/landlord/prospect/contractor), name, contacts[], verified (bool + method), language, vulnerability (consented, notes), preferences {channel, frequency}, availability (weekly windows[], exceptions[]).
- **Landlord** (extends Person): properties[], spend_limits, approval_prefs, tenant_priorities {weights}, bank (masked, verified_at), nrl_status.
- **Prospect** (extends Person): profile {budget, areas, move_date, size, must_haves[], deal_breakers[], pets, household_size}, verification {id, selfie}, matches[], trips[], applications[].
- **Contractor** (extends Person): trades[], areas[], certs[] {type, number, expires}, insurance {expires}, rates, emergency_capable, score {response, on_time, first_fix, rating, cost_vs_quote}, workload.
- **Thread**: participants[], property_id, channel(s), category, playbook_ref (spreadsheet row), status, autonomy, flags[], sla_due, assigned_to, messages[].
- **Message**: thread_id, direction, channel, author (person/ai/human_user), text, attachments[], transcript, language, ai_meta {draft, confidence, reasons[], facts[]}, sent_at, undo_until.
- **Job** (maintenance): property_id, tenant_id, issue_ref (spreadsheet), urgency, urgency_reasons[], stage, stage_history[], waiting_on, autonomy, flags[], liability, estimate, quotes[], approval {required, status, requested_at, decided_by}, emergency {confirmed, checks[], override_used}, contractor_id, offers[] {contractor, slots[], status}, scheduled_slot, tenant_confirmed, eta, completion {report, photos_before[], photos_after[], cost}, tenant_fixed (bool), reports {landlord, tenant}, invoice_id, related_jobs[].
- **Viewing**: property_id, prospect_id, mode (agent/self/video), slot, trip_id, agent_id, status, reminders[], checkin, lock_events[], attended (bool), no_show_count, feedback.
- **Trip**: prospect_id, viewings[] ordered, travel_minutes[], status.
- **Application**: prospect_id, property_id, applicants[], checks {id, rtr, income, credit, references}, gates_passed, score, rank, risks[], landlord_decision, holding_deposit, contract {sent_at, signed_at}.
- **CalendarEvent**: type, refs, start/end, attendees[], tentative (bool), location.
- **Approval**: type, ref, requested_from, amount, status, chased_at[], decided_at.
- **Escalation**: ref, priority, reason, handover_note, assigned_to, status.
- **AuditEvent**: ref, actor (ai/human/person), action, inputs, result, success, error, timestamp.
- **ComplianceItem**: property_id, type, issued, expires, status, document.
- **Invoice / Payment / Statement** (accounting).

---

## 14. KG tool integration and API contract

The portal is a client of the existing KG agent. Adapt names to the real tool; keep the shape.

**Read**
- `GET /needs-you` → prioritised items (approvals, escalations, low-confidence drafts, failures).
- `GET /threads?filters` · `GET /threads/:id` (messages, ai drafts, context, flags).
- `GET /jobs?stage&urgency` · `GET /jobs/:id` (progress, decisions, timeline).
- `GET /viewings?range&agent&property` · `GET /trips/:id` · `GET /prospects/:id`.
- `GET /calendar?from&to&layers`.
- `GET /properties/:id` (incl. viewing rules, knowledge facts with sources).
- `GET /kg/facts?entity` → facts with source node ids (for "facts used").
- `GET /audit?ref`.

**Write / control**
- `POST /threads/:id/send` (text, channel) · `POST /threads/:id/draft/approve|reject` · `POST /threads/:id/takeover` · `POST /threads/:id/handback {instruction}`.
- `POST /jobs/:id/approve-step {step}` · `POST /jobs/:id/override {field, value, reason}` · `POST /jobs/:id/pause|resume` · `POST /jobs/:id/call {who, mode: ai|human}` · `POST /jobs/:id/contractor {id}` · `POST /jobs/:id/reschedule`.
- `POST /availability/request {person, purpose}` · `POST /scheduler/propose {job|prospect}` · `POST /scheduler/confirm`.
- `POST /trips/propose {prospect_id}` · `POST /trips/:id/approve`.
- `POST /viewings/:id/followup/start` · `POST /applications/:id/send-to-landlord` · `POST /applications/:id/contract`.
- `PATCH /settings/autonomy` · `PATCH /properties/:id/viewing-rules`.
- `POST /escalations/:id/take`.

**Realtime:** websocket/SSE stream of events (`job.stage_changed`, `message.received`, `ai.drafted`, `flag.raised`, `call.live`, `emergency.opened`) to update Today, Inbox, Board and progress cards live.

**Guardrails in the API (not just UI):** blocked actions return `403 {reason, rule, alternative}` (e.g. booking over limit without approval; sending costs to a tenant; bidding; contract before landlord acceptance).

---

## 15. Notifications, messages and templates

**PM notifications:** P0 (push+SMS+call), P1 (push), P2 (queue), daily digest (morning summary), end-of-day summary.
**Outbound templates (per channel and language):** acknowledgement, form link, photo re-take request, safety instructions (gas/fire/water/electric), emergency dispatch notice, landlord approval request, landlord chaser, availability request, slot offers to contractors, booking confirmation, 24h access notice, reminders (T-24h, morning, unconfirmed call), contractor ETA, "Is it fixed?", landlord report, tenant report, no-show rebook, viewing confirmation (trip), viewing reminders, self-guided access, post-viewing follow-up, application link, recommendations, shortlist to landlord, holding deposit request, contract for signature, rent reminder, compliance booking, inspection notice.
**Tone:** warm, short, plain English; tenants never see costs; landlords always do; no threats; one clear next step per message.

---

## 16. Design system and copy

**Brand:** **Properly**. Wordmark in heavy grotesk, colour `#202020`. Mascot: black rounded pentagon with two white oval eyes (blinks, looks toward attention items). Assets: mascot SVG (rounded pentagon via `stroke-linejoin: round`), intro animations (London flight + logo wipe).
**Palette:** background `#F4F4F4` / white; ink `#202020`; muted `#5D6864`; semantic: emergency red `#C2362B`, warning amber `#B7791F`, success green `#1F6F5C`, info blue `#2563EB`, human-only purple `#6B4FA3`, vulnerable pink `#B83280`. Dark mode required.
**Type:** a clean grotesk for UI (e.g. Inter or similar), tabular numbers for times/costs.
**Components:** flag chip, priority badge, progress stepper (horizontal/vertical), AI action card (what/why/facts/confidence/buttons), handover note card, availability grid (weekly windows), calendar lanes, kanban card, thread message bubble with channel icon, photo with AI caption, call card with transcript, approval card (mobile), empty states with mascot.
**Copy rules:** say what happens ("Approve £420 repair"), not system words; never "HITL", "escalation queue" in user-facing UI → "Needs you"; time as "in 2h" / "3m ago"; errors explain fix.
**Accessibility:** keyboard shortcuts (j/k navigate, a approve, r reply, t take over, e escalate), focus states, colour never the only signal (icons + text on flags).

---

## 17. Demo script and test scenarios

### 17.1 60-second demo path through the portal
1. **Today** shows an emergency banner and 4 "Needs you" items.
2. Open **Inbox** → a 400-word tenant email; the buried "eggy smell" line is highlighted red; AI already called (play 5s of callback); emergency check confirmed; safety SMS sent; Gas Safe engineer dispatched; on-call alerted.
3. Open the **job** → progress card live: Safety steps ✓ → Confirmed ✓ → Dispatched ✓ → On the way (ETA 14 min).
4. Routine job: photo coach request; over-limit → landlord one-tap approval; **contractor race**; tenant calendar hold; progress card moves to Scheduled.
5. **Viewings**: one prospect's weekly availability → **trip builder** proposes 3 flats Tue evening → Approve & send; after viewing, follow-up → application → landlord shortlist → contract sent.
6. **Escalation**: landlord asks "can I just change the locks?" → flagged Human only + Emergency; handover note; PM taps **Take it**.
7. Overnight scoreboard from the real batch run.

### 17.2 Test scenarios (portal must show the right flags/controls)
1. Gas smell buried in long email → P0, emergency banner, safety steps, dispatch, on-call alert.
2. Ceiling leak, calm photo, text says "dripping faster near the light" → urgency raised; photo can't lower it.
3. Elderly tenant, no heating, cold → Emergency, Vulnerable flag.
4. "Probably nothing but a burning smell from the socket" → callback, emergency check.
5. Dripping tap, full details, under limit → Autopilot end to end; progress card to Closed.
6. £900 boiler quote, £300 limit, landlord silent 48h → chase shown, escalated P2.
7. Night uncontrolled leak, over limit → emergency override, landlord notified.
8. Landlord: "don't fix the mould" → Unlawful request flag, human only.
9. Tenant wants landlord to pay for window their child broke → Conflict, liability → human.
10. Contractor API fails twice → failure in timeline, retry, next contractor.
11. No contractor replies → backups, human.
12. Tenant no-show; third visit → Repeat fault + human.
13. Duplicate reports from flatmates → merged thread.
14. Non-tenant asks for tenant's phone → Unverified, refused.
15. Contractor says fixed; tenant says no → reopened.
16. Final invoice 40% over quote → Over quote flag, invoice held.
17. Communal lift broken → referred to block manager.
18. Locked out at 11pm (lost key vs broken lock) → emergency access; who pays shown.
19. Mould in baby's room → Vulnerable, Urgent.
20. Message in Polish → reply in Polish.
21. Gas cert expires in 10 days, tenant not responding → Compliance due red, human.
22. Inspection finds damp + loose banister → two new jobs.
23. "I'll report you to the council" → Human only.
24. Mixed message: repair + rent question → split.
25. Prospect with weekday-evening availability + 3 matches → trip of 3.
26. Viewing no-show → rebook loop; second no-show → confirmation call required.
27. Landlord asks to take highest offer → blocked, explainer.
28. Applicant on Universal Credit → treated normally; "not used in ranking" shown.
29. Self-guided: lock offline → fallback to agent/video; human alerted.
30. Landlord bank detail change by email → Fraud check, blocked until phone-verified.

---

## 18. Reference data (issue spreadsheets)

- **Tenant issues** (`Tenant_Maintance_Questions_and_Beyond.xlsx` → sheet "Tenant issues (816)"): 716 repair types (Fixflo taxonomy) + 100 non-repair tenant enquiries. Columns: Category · Sub-category · Question or request · Info to collect · Suggested handling · Urgency · Key rules / notes · Source · Fixflo advice popup · Communal?.
  - Suggested handling values: *Agent handles (repair flow)* · *Agent acts + alerts human* · *Agent answers* · *Agent gathers info, human decides* · *Human only (escalate)*.
  - Urgency is a **starting level**; only ever raise it.
- **Landlord enquiries** (`Landlord_enquiries.xlsx`): 91 items across 12 categories; same columns.
- **Question set** sheet: Fixflo form fields (for reference; our form is conversational, asks only what's missing, photos only, no dropdowns).
- **Workflow doc** ("Property Management Workflows"): TT, MT, LT, LV, AC, portals, shared basics, proposed skill set list (29 skills).
- **BPMN diagrams**: maintenance (W1–W10) and lettings (L1–L13).

The portal should load the spreadsheets as **playbooks**: when a ticket/job is classified, show the matching row (handling, urgency, info to collect, rules) in the context panel, and use it to pre-set autonomy and flags.
