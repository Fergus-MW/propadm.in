# Reasoning for case 37

## What the system received

- `index.md`: read, 1056 bytes
- `history.md`: read, 9507 bytes
- 25 history events; latest timestamp 2024-04-06 10:46:31 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, communications

## Plan

Goal: Shower hose replacement at Flat 14, 44 Lantern Quay: verify completion with tenant, correct wrong-address landlord FYI, obtain unreadable invoice details from contractor, then resolve when criteria met.

- [done] Record case state and note conflicts on ticket
  - evidence: Note added to ticket:case v2
- [done] Send tenant completion check
  - evidence: email:sandbox-1 (SIMULATED)
- [done] Send landlord correction with correct address
  - evidence: email:sandbox-2 (SIMULATED)
- [done] Ask contractor for cost, parts, photos in email body
  - evidence: email:sandbox-3 (SIMULATED)
- [done] Update ticket fields/notes
  - evidence: ticket:case updated to v3: status in progress, resolution pending note
- [in_progress] Sleep awaiting tenant and contractor replies; then resolve if criteria met
  - note: Waiting on tenant yes/no and contractor cost/parts details; then resolve and send landlord cost/invoice.

## Agent messages

1. Now the three emails.
2. Now update ticket status and plan.
3. **Decision**
- The shower hose repair is reported done by the contractor (Beacon Utilities, email of 6 April) but not verified, so I have not resolved or closed the ticket. The platform's "completed by supervisor" line is only a tick, and the tenant hasn't confirmed the leak has stopped.
- The contractor's attachment (attachment-91) was unreadable. I know nothing about cost, parts or scope, so I haven't stated or recorded any cost.
- The agency's 10:45 note to the landlord (event 023) named the wrong address, Flat 8, 68 Willowmere Road, Bellmere. The property of record is Flat 14, 44 Lantern Quay, Alderwick. I treated that as an error and sent a correction.
- The only approval on record is the landlord's 27 March email, "Please get the shower hose replaced". It carries no price.

**Actions**
- Created a plan and added a state note to ticket:case. I then set the ticket status to "in progress", with a resolution line saying tenant confirmation and invoice details are pending.
- Sent the tenant a yes/no check on whether the shower is working and no longer leaking (email:sandbox-1). It mentions no costs.
- Sent the landlord a correction with the right address. It says the contractor reports the hose was replaced and that we haven't yet seen the invoice or cost (email:sandbox-2).
- Asked the contractor to put the visit date, parts, cause of the leak, photos, total cost with VAT basis and invoice addressee in the email body (email:sandbox-3).
- All three emails went through the sandboxed provider and are SIMULATED, so none were actually delivered.
- Put the run to sleep for 10 minutes, set to wake on the ticket or on replies to the tenant and contractor emails.

**Staff involvement**
- None needed so far.
- Staff would need to decide if the cost exceeds what the landlord approved, if the contractor reports further work, or if the tenant says the shower still leaks.

**Open items**
- Waiting for the tenant's yes/no on whether the shower works and no longer leaks.
- Waiting for the contractor's cost, parts and photo details.
- The cost route is not on record: the landlord may pay the contractor directly, or the agency may pay and deduct from rent. I'll confirm it once the invoice details arrive.
- Once the tenant confirms, or the check goes unanswered and the contractor's evidence supports completion, I'll set the ticket to resolved. I'll then send the landlord the cost and invoice, and tell the tenant what was done and how to report a recurrence, without any cost.
- If the tenant doesn't reply after reasonable attempts, I'll record the job as reported done and close it with a recurrence route.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "job-completion"} -> OK
6. `get_skill` {"skill": "communications"} -> OK
7. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
8. `create_plan` {"goal": "Shower hose replacement at Flat 14, 44 Lantern Quay: verify completion with tenant, correct wrong-address landlord FYI, obtain unreadable invoice details from contractor, then resolve when criteria met.", "steps": [{"id": "state", "title": "Record case state and note conflicts on ticket",  -> OK
9. `get_entity` {"id": "person:case-landlord"} -> OK
10. `get_entity` {"id": "company:case-contractor"} -> OK
11. `update_step` {"step_id": "state", "status": "in_progress"} -> OK
12. `add_note` {"id": "ticket:case", "version": 1, "reason": "Record state from case history events 007, 021-025 before acting", "note": "State 2024-04-06: Contractor (Beacon Utilities) emailed 04-06 06:16 'Replaced snapped shower hose' - reported completion, NOT verified by tenant. Attachment-91 unavailable: cost -> OK
13. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "Flat 14, 44 Lantern Quay – is your shower now fixed?", "body": "Hello Eliza,\n\nBeacon Utilities reports that the snapped shower hose at Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8ZZ was replaced. Is the shower now working and no longer leaking? A s -> SIMULATED Sandboxed email provider: recorded, not delivered.
14. `send_email` {"to": ["landlord@case.sandbox.invalid"], "subject": "Correction: Flat 14, 44 Lantern Quay – shower hose replaced", "body": "Hello Freya,\n\nPlease disregard the address in our earlier note today: it named another property in error. The correct property is Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8Z -> SIMULATED Sandboxed email provider: recorded, not delivered.
15. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 14, 44 Lantern Quay – shower hose: details needed in email body", "body": "Dear Beacon Utilities,\n\nThank you for your report that the snapped shower hose at Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8ZZ was replaced. We could not open you -> SIMULATED Sandboxed email provider: recorded, not delivered.
16. `update_entity` {"id": "ticket:case", "version": 2, "fields": {"status": "in progress", "resolution": "Contractor reports snapped shower hose replaced 2024-04-06; tenant confirmation and invoice details pending"}, "reason": "Platform 'completed' is a supervisor tick; completion only reported by contractor (event 02 -> OK
17. `update_step` {"step_id": "state", "status": "done", "evidence": "Note added to ticket:case v2"} -> OK
18. `update_step` {"step_id": "tenant", "status": "done", "evidence": "email:sandbox-1 (SIMULATED)"} -> OK
19. `update_step` {"step_id": "landlord", "status": "done", "evidence": "email:sandbox-2 (SIMULATED)"} -> OK
20. `update_step` {"step_id": "contractor", "status": "done", "evidence": "email:sandbox-3 (SIMULATED)"} -> OK
21. `update_step` {"step_id": "ticket", "status": "done", "evidence": "ticket:case updated to v3: status in progress, resolution pending note"} -> OK
22. `update_step` {"step_id": "wait", "status": "in_progress", "note": "Waiting on tenant yes/no and contractor cost/parts details; then resolve and send landlord cost/invoice."} -> OK
23. `sleep` {"minutes": 10, "reason": "Awaiting tenant yes/no on shower and contractor cost/parts details (emails SIMULATED)", "wake_on": ["ticket:case", "email:sandbox-1", "email:sandbox-3"]} -> OK
