# Property manager portal

The portal is part of the existing Next.js admin app and FastAPI gateway. Run
`make dev`, open the printed Admin URL, and use the printed local password.
The default page is Today; the former overview remains at `/overview`.

The [product specification](PROPERLY_PORTAL_SPEC.md) describes the full target.
This change implements its core supervision, maintenance, inbox, and viewing
workflows. It does not represent every later integration in that specification
as working software.

## Available workflows

- Today: priority/deadline ordered Needs you queue, open repair counts, emergency
  banner, recorded activity, and confirmed viewing itineraries.
- Inbox: ticket-linked email conversations, role/search/attention filters,
  dangerous-phrase highlighting, source links, editable drafts, explicit email
  approval/send, discard, take-over, and instruction-bearing hand-back.
- Maintenance: board and list, standard/emergency progress cards, spend authority
  evidence, approval/rejection, reasoned stage and urgency overrides, notes,
  tenant-fix confirmation, reopening, and a persistent decision timeline.
- Viewings: prospects and availability linked to existing graph people;
  property viewing windows, occupancy, consent and compliance attestations;
  ordered multi-home trips with explicit travel buffers; atomic confirmation.
- Calendar and availability: week navigation, confirmed trips, prospect windows,
  access-rule editor and links to repair conversations for coordination.
- Settings: global pause/resume and an explanation of per-item control levels.
  Existing property, landlord, provider, money/ledger, voice, email and
  integration screens remain available in the original navigation.
- Share progress: expiring (24-hour), revocable tenant/landlord repair links.
  Tenant responses use an explicit field allow-list, without financial fields,
  internal notes, drafts, messages or contact details. Landlord views include
  estimate and approval status. These are read-only progress views.

## Emergency override

Every repair detail has an **Emergency override** control. Record the observed
hazard and source, then choose **Activate emergency make-safe & take over**.
This works while global automation is paused, moves the repair onto emergency
progress, clears prior ordinary repair approval and keeps the item under human
control. It does not require a quote, spend limit, photos or form completion.
Make-safe progress can be recorded above the landlord's limit. The control does
not send an alert, call a tenant, or dispatch a contractor: the manager must
arrange assistance and notify the on-call person and landlord through available
communication channels. Ordinary agent actions remain paused.

**Confirm made safe — continue repair** requires evidence and returns the job
to urgent triage, with spend approval and tenant-fix confirmation reset. It does
not close the repair. A suspected emergency can instead be ruled out with a
recorded human assessment; it remains urgent. Neither action removes fraud,
privacy or other human-only flags. Routine urgency edits and reopening cannot
clear an active emergency. An automatic danger flag is a review request, never
authority for autonomous emergency spend.

A live safety resolution applies only to the reviewed source evidence. New
inbound facts or a changed danger report trigger review again, including on a
previously closed repair. See [workflow edge-case review](portal-edge-cases.md)
for coverage and remaining operational dependencies.

## Data and integration

`GET /v1/portal` projects canonical ticket entities and related email, property
and person records. Portal control metadata is an overlay in the same durable
repository, not a replacement graph or another database. Graph evidence remains
canonical; a manual portal stage records a manager's override, not a claim that
a provider performed work. Entity revisions plus portal revisions reject stale
control writes. Portal decisions publish to the repository event stream and
appear in each item's timeline. The stream at `/v1/portal/stream` invalidates
clients after durable changes; five-second polling provides a fallback.

Agents still use exactly one MCP endpoint, `/mcp`. `get_portal_item` supplies
control state; `draft_portal_reply` accepts a version, confidence, reasons and
canonical source IDs. It saves a proposal without sending anything and limits
its item to Draft for me or a stricter mode. It cannot overwrite a saved draft
on an item a human has taken over. Existing deployed managed agents need their
tool catalogue refreshed through the normal agent deployment path to see the
new tools.

Take-over and global pause block new consequential MCP actions, including
admin-agent actions. Read/plan/proposal tools remain available. Related graph
subjects and a run's claimed subjects are checked. This is a gateway boundary:
a request already admitted to a provider cannot be recalled. A paused emergency
therefore needs a human to carry out safety steps immediately.

Replies use the existing email service's reply adapter and original incoming
email ID, with reply-all disabled. They require a linked inbound email. A send
reservation prevents duplicate/stale requests; an uncertain provider response
requires a manager to check the email log and record delivery evidence before
retrying. No telephony/email provider is called in demo mode. Free-text tenant
replies are screened for financial wording, but a manager must still review
recipient and content; the screening is not a general PII classifier.

Always-human flags prevent hand-back. Deterministic risk tripwires can raise
attention from source text; they are conservative routing signals, not a claim
that an AI has confirmed an emergency. An explicit negated gas smell does not
raise an emergency. Over-limit approval needs a recorded approval source;
booking without known authority is blocked; closing before tenant confirmation
is blocked. These controls do not substitute for legal/compliance review.

Trip proposal and confirmation both check tenant consent, compliance, minimum
notice and windows. Confirmation checks fresh rules and competing bookings
inside a repository transaction. Dates require timezones. Travel is a supplied
buffer, not a claimed map routing result. Confirmation records an itinerary;
it does not pretend invitations or contracts have been sent.

Magic links carry a narrowly scoped signed grant. The public API accepts only
that grant and returns an audience projection. It never accepts the grant for
admin APIs. Responses are not cached, the page suppresses referrers and
analytics, and administrators can revoke links. The app retains its existing
shared-admin authentication; named staff roles and portfolio isolation need a
separate identity model before a multi-user production rollout.

## Demo

Choose **Workspace settings → Open sample workspace**, then **Open workspace**.
Sample records are opt-in and persisted under a separate repository namespace.
Data provenance and delivery limitations appear in Settings; operational views
use ordinary workflow labels. Loading them is idempotent and cannot reset live work.

1. Open the gas scenario to inspect emergency progress.
2. Open the boiler scenario, enter the sample landlord approval evidence in the
   reason field, approve, and see progress move to Finding a contractor.
3. Take over a thread, edit and simulate a reply; no message leaves the app.
4. Open Viewings, select Willow Close and Ash Gardens, propose and confirm a trip.
   Elm Road intentionally lacks tenant consent and is rejected by the API.
5. Inspect Calendar (the demo window is three days after initialisation; choose
   the next week if needed).
6. Create tenant and landlord progress links to inspect their different fields.

Fixtures are not agent evaluation results. Existing local seed records also
remain synthetic, as documented by the original local development environment.

## Remaining specification work

The source specification includes integrations and extended workflows beyond
this core portal: spreadsheet playbook ingestion (the referenced spreadsheets
were not attached), photo analysis, live call join/take-over, automatic contractor
races and chase timers, generated reports, multi-channel send/translation,
outbound undo scheduling, recurring availability/blackouts and route estimates,
self-guided locks, post-viewing applications/shortlists/e-signatures, full
compliance inspection automation, and external tenant/landlord self-service.
These are not faked by the portal. Existing domain/provider screens are reused;
the portal does not invent new accounting or compliance records.

## Verification

- `uv run pytest` — backend and existing repository tests, including portal
  isolation, stale writes, human-control guards, approvals/completion, live and
  simulated replies, viewing races/changed consent, drafts and share redaction.
- `pnpm --dir services/admin-panel test` — client tests including queue order,
  dataset links and analytics redaction.
- `pnpm --dir services/admin-panel typecheck`
- `pnpm --dir services/admin-panel lint`
- `pnpm --dir services/admin-panel build`
- `pnpm --dir services/admin-panel generate:api --check`
- `make dev` plus browser checks of approval, demo navigation, trip booking and
  desktop/mobile layouts.
