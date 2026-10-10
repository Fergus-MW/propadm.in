# Reasoning for case 19

## What the system received

- `index.md`: read, 1677 bytes
- `history.md`: read, 11746 bytes
- 44 history events; latest timestamp 2025-04-16 09:16:13 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, landlord-approval, escalation-and-handover, communications

## Plan

Goal: Garden clearance case: system shows closed but invoice unseen, tenant completion unconfirmed, levelling/gravel scope unaddressed. Verify, correct, and only then resolve.

- [done] Record case state on ticket (status not closed; facts/claims/conflicts)
  - evidence: Note added and ticket set to status in progress (version 3)
- [done] Email contractor: invoice details in email body (scope, amount, VAT, date done, photos)
  - evidence: email:sandbox-1 (SIMULATED, not delivered)
- [done] Email tenant: completion check (rubbish cleared?) and note levelling/gravel not yet approved
  - evidence: email:sandbox-2 (SIMULATED)
- [done] Email landlord: correct earlier email (invoice unseen, figures to follow), ask yes/no on levelling/gravel as optional extra
  - evidence: email:sandbox-3 (SIMULATED)
- [in_progress] Sleep for replies; then validate invoice vs approval, record expense, resolve
  - note: Waiting on contractor invoice details, tenant yes/no, landlord yes/no on levelling/gravel. Do not record expense or resolve until invoice seen and checked vs ~£600 approval.

## Agent messages

1. Now the three emails.
2. Report before sleeping.

**Decision**
The platform shows this case as completed and closed. I am keeping it open as "in progress". The garden clearance is only reported as done. The tenant hasn't confirmed it, and no photos have been seen. I have not seen the invoice, because its attachment is unreadable. The levelling and gravel the tenant asked for were never approved. The landlord's approval ("go ahead with the removal", replying to the March email quoting around £600) covers removal only.

**Actions**
- **Ticket:** I added a note setting out the confirmed facts, reported claims and gaps. I set the status to "in progress" and added the tags awaiting-invoice-details and awaiting-tenant-confirmation.
- **Contractor:** I emailed asking for company name, dates, what was removed, amount and VAT basis, invoice number and photos in the email body. I also asked them not to do any levelling or gravel work for now.
- **Tenant:** I emailed a yes/no check on whether the rubbish has gone. I told them levelling and gravel are still being checked with the landlord, and mentioned no costs.
- **Landlord:** I emailed a correction. The 09:10 email said the invoice was attached and would be deducted from rent, but the amount and VAT are unconfirmed, so the deduction is pending. I also asked yes/no whether to quote for levelling and gravel, with the option of their own contractor.
- **Not done:** I recorded no expense, ledger entry or rent deduction, and did not resolve or close the ticket.
- **Email delivery:** all three emails are SIMULATED (email:sandbox-1, -2 and -3) and were not actually delivered.

**Staff involvement**
No handover yet. If the invoice comes in materially above the roughly £600 approved, or the contractor's identity doesn't add up, I will hand it to staff. The 31 January staff note names Harbour Compliance, but the latest note calls the contractor a "new provider".

**Open items**
- Contractor's written invoice details: the amount and VAT must be checked against the roughly £600 approval before I record an expense under contractor-invoice.
- Tenant yes/no on the clearance.
- Landlord yes/no on levelling and gravel.
- Once the invoice is checked and the tenant has confirmed (or one check goes unanswered), I will set the ticket to resolved with the cost.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "job-completion"} -> OK
6. `get_skill` {"skill": "contractor-invoice"} -> OK
7. `get_skill` {"skill": "landlord-approval"} -> OK
8. `get_skill` {"skill": "escalation-and-handover"} -> OK
9. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
10. `get_entity` {"id": "company:case-contractor"} -> OK
11. `get_entity` {"id": "person:case-landlord"} -> OK
12. `get_skill` {"skill": "communications"} -> OK
13. `get_ledger` {"property": "property:case"} -> OK
14. `create_plan` {"goal": "Garden clearance case: system shows closed but invoice unseen, tenant completion unconfirmed, levelling/gravel scope unaddressed. Verify, correct, and only then resolve.", "steps": [{"id": "state", "title": "Record case state on ticket (status not closed; facts/claims/conflicts)"}, {"id":  -> OK
15. `update_step` {"step_id": "state", "status": "in_progress"} -> OK
16. `add_note` {"id": "ticket:case", "version": 1, "reason": "Rebuilding state from case history events 001-044 before acting", "note": "STATE 2025-04-16 09:16 UTC. Platform shows \"Completed/closed\" (ev 039/044, early ticks; ev 043 \"Need confirmation from landlord\"). Not verified.\nCONFIRMED: tenant request 20 -> OK
17. `update_entity` {"id": "ticket:case", "version": 1, "reason": "Platform shows closed but tenant confirmation, invoice contents and levelling/gravel scope are outstanding; keep open", "fields": {"status": "in progress", "category": "garden", "tags": ["awaiting-invoice-details", "awaiting-tenant-confirmation"]}} -> ERROR {'code': 'conflict', 'message': 'Stale entity version; current version is 2'}
18. `update_entity` {"fields": {"category": "garden", "status": "in progress", "tags": ["awaiting-invoice-details", "awaiting-tenant-confirmation"]}, "id": "ticket:case", "reason": "Platform shows closed but tenant confirmation, invoice contents and levelling/gravel scope are outstanding; keep open", "version": 2} -> ERROR {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"}
19. `update_entity` {"fields": {"category": "other", "status": "in progress", "tags": ["awaiting-invoice-details", "awaiting-tenant-confirmation"]}, "id": "ticket:case", "reason": "Platform shows closed but tenant confirmation, invoice contents and levelling/gravel scope are outstanding; keep open", "version": 2} -> OK
20. `update_step` {"status": "done", "step_id": "state", "evidence": "Note added and ticket set to status in progress (version 3)"} -> OK
21. `update_step` {"status": "in_progress", "step_id": "contractor"} -> OK
22. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 25, 185 Copperfield Walk, Alderwick, ZZ4 0ZZ - garden clearance invoice details", "body": "Hello,\n\nRe: garden clearance at Flat 25, 185 Copperfield Walk, Alderwick, ZZ4 0ZZ.\n\nWe understand you have completed the clearance and sent an i -> SIMULATED Sandboxed email provider: recorded, not delivered.
23. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "Flat 25, 185 Copperfield Walk - garden clearance: is it done?", "body": "Hello,\n\nThank you for your garden request at Flat 25, 185 Copperfield Walk. The contractor reports that the rubbish and builders' material has been cleared from the garden.\ -> SIMULATED Sandboxed email provider: recorded, not delivered.
24. `send_email` {"body": "Hi Jenkins,\n\nRe: garden at Flat 25, 185 Copperfield Walk, Alderwick, ZZ4 0ZZ.\n\nTwo things, following our earlier message that the garden has been cleared:\n\n1. Invoice: the invoice attachment on our earlier email could not be opened on our side, so we have not yet confirmed the amount -> SIMULATED Sandboxed email provider: recorded, not delivered.
25. `update_step` {"step_id": "contractor", "status": "done", "evidence": "email:sandbox-1 (SIMULATED, not delivered)"} -> OK
26. `update_step` {"step_id": "tenant", "status": "done", "evidence": "email:sandbox-2 (SIMULATED)"} -> OK
27. `update_step` {"step_id": "landlord", "status": "done", "evidence": "email:sandbox-3 (SIMULATED)"} -> OK
28. `update_step` {"step_id": "wait", "status": "in_progress", "note": "Waiting on contractor invoice details, tenant yes/no, landlord yes/no on levelling/gravel. Do not record expense or resolve until invoice seen and checked vs ~£600 approval."} -> OK
29. `sleep` {"minutes": 10, "reason": "Waiting for contractor invoice details, tenant completion confirmation and landlord answer on levelling/gravel", "wake_on": ["ticket:case", "email:sandbox-1", "email:sandbox-2", "email:sandbox-3"]} -> OK
