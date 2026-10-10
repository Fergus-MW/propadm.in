# Reasoning for case 18

## What the system received

- `index.md`: read, 1433 bytes
- `history.md`: read, 10076 bytes
- 17 history events; latest timestamp 2026-01-06 01:31:56 UTC

## Skills consulted

graph-conventions, job-completion, planning-and-sleeping, communications, contractor-invoice, escalation-and-handover

## Plan

Goal: Ticket:case garden maintenance (Flat 17, 67 Willowmere Road): verify reported completion with tenant, obtain unavailable invoice/completion report from contractor, keep landlord informed, resolve only when criteria met.

- [done] Rebuild state and record in note
  - evidence: State note added to ticket:case (add_note); issues, conflicts, missing info recorded.
- [done] Ask tenant to confirm garden work done (yes/no)
  - evidence: email:sandbox-1 simulated to tenant
- [done] Ask contractor for completion report and invoice (contents unavailable)
  - evidence: email:sandbox-2 simulated to contractor
- [done] Update ticket fields/note; staff handover on invoice/cost if needed
  - evidence: ticket:case v3 status=in progress; handover not needed yet (no invoice amount/dispute known). Landlord already informed 3 Jan; invoice to follow once contents known.
- [in_progress] Sleep for replies; resolve only if job-completion criteria met
  - note: Waiting on tenant yes/no reply (by 9 Jan) and contractor completion report/invoice details. Resolve only when criteria met.

## Agent messages

1. Now the emails to tenant and contractor.
2. **Decision**
- The garden work is reported as done but not verified, so I left the ticket open at status "in progress" and did not resolve or close it.
- The "Completed by supervisor" line is a platform tick. The record has no contractor report, no date, no photos and no tenant confirmation. The invoice attachment is unavailable, so I don't know the amount or scope.
- The contractor never replied to the assignment email or the three reminders.
- The only landlord approval is a platform tick with no amount or scope. Langley told the landlord on 3 Jan that the work was done and would be "invoiced off the rent", and the landlord acknowledged. I treated that as acknowledgement, not approval of a price.
- The tenant phone number given to the contractor differs between the 17 Dec email and the later reminders. I relied on neither.

**Actions**
- **State note:** I added a note to ticket:case recording issues, confirmed facts, claims, conflicts and missing information.
  - The first attempt failed because I used the wrong ticket version (24 instead of 1).
  - I had already marked plan step s1 "done" before that call returned. The retry with version 1 succeeded, so the step's evidence is now accurate, but I ticked it too early.
- **Tenant:** I emailed the tenant (email:sandbox-1) asking whether the overgrowth is cleared, with a request for a photo and a reply by 9 Jan. It contained no costs.
- **Contractor:** I emailed the contractor (email:sandbox-2) asking for the attendance date, work done, photos, and the invoice number, total, VAT basis and scope in the email body. I told them not to do further work without written approval.
- **Simulated delivery:** Both emails are SIMULATED. They were recorded, not delivered.
- **Ticket fields:** I set status "in progress", urgency "routine" and category "other". My first update with category "garden" was rejected because it isn't an allowed value. "Other" is the nearest fit, not a precise classification.
- **Plan steps:** I marked s2 to s4 done. Step s5 stays in progress while I wait.
- **Sleep:** I went to sleep for 10 minutes, waking on the ticket or either email thread.
- **Not done:** I made no ledger entries, sent nothing to the landlord, placed no calls and set no tags.

**Staff involvement**
- No handover so far and no `needs-staff` tag. I judged that nothing needs a staff decision until the invoice contents are known.
- My earlier report said the agency isn't paying a contractor under this cost route. That was wrong. "Invoiced off the rent" could mean the agency pays and deducts from the landlord's rent, and I haven't established which. Staff should decide if the amount turns out to exceed any approval, is disputed, or if anyone proposes charging the tenant.

**Open items**
- Tenant's yes/no confirmation of the outcome.
- Contractor's completion report and invoice details. If they stay silent, a phone call is the next channel, but I have not placed one.
- Once the invoice contents are known, I need to check the amount against what was approved, work out the cost route, and send the landlord the invoice and cost.
- Resolve the ticket only once the tenant has confirmed, or one check has gone unanswered and the contractor's evidence supports completion. The cost route must also be clear and the landlord informed.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_entity` {"id": "ticket:case"} -> OK
4. `get_skill` {"skill": "job-completion"} -> OK
5. `get_skill` {"skill": "planning-and-sleeping"} -> OK
6. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
7. `create_plan` {"goal": "Ticket:case garden maintenance (Flat 17, 67 Willowmere Road): verify reported completion with tenant, obtain unavailable invoice/completion report from contractor, keep landlord informed, resolve only when criteria met.", "steps": [{"id": "s1", "title": "Rebuild state and record in note",  -> OK
8. `get_skill` {"skill": "communications"} -> OK
9. `get_skill` {"skill": "contractor-invoice"} -> OK
10. `get_skill` {"skill": "escalation-and-handover"} -> OK
11. `get_entity` {"id": "company:case-contractor"} -> OK
12. `get_entity` {"id": "person:case-landlord"} -> OK
13. `get_property` {"property": "property:case"} -> OK
14. `add_note` {"id": "ticket:case", "version": 24, "reason": "Recording state per graph-conventions after reading case history events 001-017.", "note": "STATE 2026-01-06: Issue: overgrown tree/weeds in communal garden (tenant Q&A) - routine, no safety risk reported. Stage: reported complete, unverified. Confirme -> ERROR {'code': 'conflict', 'message': 'Stale entity version; current version is 1'}
15. `update_step` {"step_id": "s1", "status": "done", "evidence": "State note added to ticket:case (add_note); issues, conflicts, missing info recorded."} -> OK
16. `update_step` {"step_id": "s2", "status": "in_progress"} -> OK
17. `add_note` {"id": "ticket:case", "note": "STATE 2026-01-06: Issue: overgrown tree/weeds in communal garden (tenant Q&A) - routine, no safety risk reported. Stage: reported complete, unverified. Confirmed: landlord approval step ticked 17 Dec (platform line, weakest evidence; no amount/scope on record); Riversi -> OK
18. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "Flat 17, 67 Willowmere Road – garden work: is it sorted?", "body": "Hello Freya,\n\nThis is about the overgrown tree and weeds in the garden at Flat 17, 67 Willowmere Road, Alderwick, ZZ7 4ZZ.\n\nOur records show the garden work has been marked as  -> SIMULATED Sandboxed email provider: recorded, not delivered.
19. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 17, 67 Willowmere Road – garden maintenance: completion report and invoice details needed", "body": "Dear Riverside Services,\n\nRe: Garden Maintenance Request, Flat 17, 67 Willowmere Road, Alderwick, ZZ7 4ZZ (overgrown tree and weeds).\n\ -> SIMULATED Sandboxed email provider: recorded, not delivered.
20. `update_entity` {"id": "ticket:case", "version": 2, "fields": {"status": "in progress", "urgency": "routine", "category": "garden"}, "reason": "Platform shows 'Completed by supervisor' but tenant confirmation and contractor report/invoice contents are missing; not resolved. Verification emails sent (email:sandbox-1 -> ERROR {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"}
21. `update_step` {"evidence": "email:sandbox-1 simulated to tenant", "status": "done", "step_id": "s2"} -> OK
22. `update_step` {"evidence": "email:sandbox-2 simulated to contractor", "status": "done", "step_id": "s3"} -> OK
23. `update_entity` {"fields": {"category": "other", "status": "in progress", "urgency": "routine"}, "id": "ticket:case", "reason": "Platform shows 'Completed by supervisor' but tenant confirmation and contractor report/invoice contents are missing; not resolved. Verification emails sent (email:sandbox-1 tenant, email: -> OK
24. `update_step` {"evidence": "ticket:case v3 status=in progress; handover not needed yet (no invoice amount/dispute known). Landlord already informed 3 Jan; invoice to follow once contents known.", "status": "done", "step_id": "s4"} -> OK
25. `update_step` {"note": "Waiting on tenant yes/no reply (by 9 Jan) and contractor completion report/invoice details. Resolve only when criteria met.", "status": "in_progress", "step_id": "s5"} -> OK
26. `sleep` {"reason": "Awaiting tenant completion confirmation and contractor completion report/invoice details (emails simulated).", "wake_on": ["ticket:case", "email:sandbox-1", "email:sandbox-2"], "minutes": 10} -> OK
