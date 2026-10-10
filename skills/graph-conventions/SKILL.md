---
name: graph-conventions
description: Read a maintenance case from the graph and write back to it safely. Use at the start of every task and before any write - rebuild the current state from tickets, emails, calls and documents, separate confirmed facts from claims, spot noisy or conflicting records, and record what you learn with evidence.
---

# Graph conventions

## Rebuild the state before acting
1. `get_entity` each subject from the kickoff or wake message. `traverse` the ticket (depth 2) to reach the property, tenant, landlord, contractor, emails and calls. `get_document` any source document they cite. A case history document is read the same way.
2. "Now" is the latest event in the record or the wake message time, never another date.
3. The property of record is the ticket's property. Another address in a message is either a typo (same people, same job: treat as a conflict, rely on it for nothing, correct it in your next message) or a different job mixed in (ignore its facts).
4. Before choosing an action, write the state into your current plan step note:
   issues (one line each with status) / stage / who is blocking and since when / open commitments (who, what, by when) / approvals on record (scope, amount, who, source) / confirmed facts / reported claims / conflicts / missing information.

## Trust order
1. A party's own words: their email body, their reply.
2. The agency's own outbound messages.
3. Machine summaries of calls and emails ("The customer informs..."). Names and roles in them are often wrong.
4. Notes and hold comments: intentions and reminders. A note recording what someone agreed ("landlord agreed the engineer can attend") counts unless contradicted.
5. Platform status lines: clicks and timers, not proof that anything happened.

## Platform lines
- "Please complete landlord approval step first": ask the landlord before choosing a provider.
- "Please approve selection of provider and category": the agency picks the provider. It is not a landlord approval; never describe it as one.
- "Landlord approval confirmed": staff click; weakest approval evidence, covers the job as then described unless contradicted, never a later quote or higher price.
- "Maintenance provider assigned": allocated in the system; the contractor may not know yet.
- "3+ reminders sent": automated chasers ignored; call.
- "No work results": visit date passed with no report; does not mean the visit failed.
- "Completed", "Keys return confirmed", "Need confirmation from landlord": ticks, often made early.
- Unavailable attachment, "[Text unavailable]", extraction failed: contents unknown. Never quote a price or scope from them.

## Noise rules
- Identify people by role, email or phone plus property. Names drift inside a case; never merge people across properties on a name. Relay phone numbers are not identities.
- A weekday that does not match its date confirms neither; ask before relying on it.
- Identical messages minutes apart are one message; identical reminders days apart are separate chases.
- A message after closure is a new request or noise unless it reports the same fault again.
- Someone asking about a platform status ("the portal still shows the quote pending") gets an answer from the record (the approval on file). Do not ask them to resubmit what was already approved, and never claim you updated a system unless a tool did.
- Two parties giving incompatible facts (who is home, which date, what was agreed): record both, rely on neither, and ask whoever can settle it before committing.
- Use these rules in your reasoning. Do not tell people a message was machine-written or that names are unreliable.

## Writing
- Read the entity and its version first; on a version conflict re-read, never retry stale.
- Every write has a specific `reason` naming its evidence (email, call, chunk or tool result).
- Ticket fields: `urgency`, `category`, `status` (triaged, scheduled, in progress, awaiting parts, resolved, closed), `scheduled_visit_at`, `access_instructions`, `cost_estimate`, `cost_actual`, `resolution`, `tags`. Move `status` as the job moves.
- Person fields: `availability`, `preferred_contact`. Use `add_note` for anything else, saying who said it ("tenant reports...", "contractor confirmed by email...").
- Never overwrite a confirmed fact with a claim; add a note describing the conflict.
- Never store bank details, credentials or health details beyond "needs extra care".
