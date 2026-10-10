# Reasoning for case 13

## What the system received

- `index.md`: read, 675 bytes
- `history.md`: read, 8487 bytes
- `attachments/glazing-invoice.pdf`: read, 133358 bytes
- 24 history events; latest timestamp 2025-09-10 10:10:00 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, landlord-approval, escalation-and-handover, communications

## Plan

Goal: Resolve kitchen glazing ticket: invoice arrived with no amount and no visit/completion evidence; get completion facts and invoice amount before any financial step or closure.

- [done] Record state and update ticket fields/notes
  - evidence: Ticket updated to version 3 (in progress, routine, cost_estimate 180) and state note added.
- [done] Email contractor: visit date, completion, amount, VAT, photos
  - evidence: send_email email:sandbox-1, status simulated (not delivered).
- [done] Email tenant completion check / confirm whether glass fitted
  - evidence: send_email email:sandbox-2, simulated.
- [skipped] Hold landlord update until amount known (skipped now)
  - note: No amount on invoice and no completion evidence; landlord informing and ledger expense deferred until contractor supplies amount and completion. Nothing to tell landlord yet that is established.
- [in_progress] Sleep awaiting contractor/tenant replies

## Agent messages

1. ## Decision
The case is not complete, and I have not resolved or closed it. Invoice NBL-013-INV-09 shows no amount. Nothing on record shows a visit, a fitting, photos or a tenant confirmation. The last contractor update (2 Sept) said the glass had not arrived. The 9 Sept note moving the case to "awaiting post-visit documents" had no visit behind it.

The landlord's approval stands for supplying and fitting glass at £150 plus VAT, which is £180 in total. I have not ledgered any expense, accepted a quote or paid anything.

## Actions
- **Ticket:** set to routine, category other, status in progress, `cost_estimate` 180. I added a note on the approval, the gaps in the record, and what I'm waiting for.
- **Contractor email:** I asked for the fitting or visit date, the invoice amount with VAT shown separately, photos and a corrected invoice. I also asked about anything noticed around the frame, such as damp or cold. This is email:sandbox-1, **SIMULATED**, not delivered.
- **Tenant email:** I asked a yes/no question on whether the new pane is fitted and the misting gone. I said we will chase the contractor if no visit has happened, and asked her to report any cold or damp since. No costs were mentioned. This is email:sandbox-2, **SIMULATED**, not delivered.
- **Landlord update:** skipped for now, because there is no amount or completion fact to report yet.

## Staff involvement
None needed yet. Staff should step in only if the invoice comes in materially above £180, the tenant disputes completion, or the contractor keeps not responding.

## Open items
- Waiting on the contractor for the visit and fitting date, the amount and VAT, photos, and a corrected invoice.
- Waiting on the tenant to confirm whether the glass is fitted and the misting is gone.
- Once those arrive:
  - validate the invoice against the £180 approval;
  - record the expense;
  - send the landlord the invoice and what was done;
  - resolve the ticket.
- The wider damp and cold concern has never been assessed. I will raise it with the landlord as information if the tenant reports it continues.
- Next step: sleep, with a check for replies.
2. The case is not complete, and I have left the ticket open. I'm now asleep, waiting for replies from the contractor and the tenant.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "job-completion"} -> OK
6. `get_skill` {"skill": "contractor-invoice"} -> OK
7. `get_skill` {"skill": "landlord-approval"} -> OK
8. `get_skill` {"skill": "escalation-and-handover"} -> OK
9. `get_skill` {"skill": "communications"} -> OK
10. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
11. `get_entity` {"id": "company:case-contractor"} -> OK
12. `get_entity` {"id": "person:case-landlord"} -> OK
13. `get_ledger` {"property": "property:case"} -> OK
14. `create_plan` {"goal": "Resolve kitchen glazing ticket: invoice arrived with no amount and no visit/completion evidence; get completion facts and invoice amount before any financial step or closure.", "steps": [{"id": "state", "title": "Record state and update ticket fields/notes", "detail": "Issues: misted glazi -> OK
15. `update_step` {"step_id": "state", "status": "in_progress"} -> OK
16. `update_entity` {"id": "ticket:case", "version": 1, "fields": {"urgency": "routine", "category": "other", "status": "in progress", "cost_estimate": 180}, "reason": "Triage from case history: routine misted-glazing repair, landlord approved £150+VAT (£180 total) on 2025-08-11 (events 010-012); glass ordered (event 0 -> OK
17. `add_note` {"id": "ticket:case", "note": "State 2025-09-10: Approval on record: landlord (event 010) happy to proceed if £180 is the total; approval request (event 011) stated £150 + VAT (= £180 total at 20%); staff note event 012 recorded approved. Scope: supply and fit glass to misted kitchen glazing. Invoic -> OK
18. `update_step` {"status": "done", "step_id": "state", "evidence": "Ticket updated to version 3 (in progress, routine, cost_estimate 180) and state note added."} -> OK
19. `update_step` {"status": "in_progress", "step_id": "contractor"} -> OK
20. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "8 Brackenmere Walk, Vellumbrook, ZZ1 1ZZ – invoice NBL-013-INV-09: visit details and amount needed", "body": "Hello,\n\nWe have received invoice NBL-013-INV-09 dated 10 September for \"Supply and fit 1 pane of glass to the kitchen glazing\" at  -> SIMULATED Sandboxed email provider: recorded, not delivered.
21. `update_step` {"evidence": "send_email email:sandbox-1, status simulated (not delivered).", "status": "done", "step_id": "contractor"} -> OK
22. `update_step` {"status": "in_progress", "step_id": "tenant"} -> OK
23. `send_email` {"body": "Hello,\n\nRe: the misted kitchen glazing at 8 Brackenmere Walk. We have received paperwork from the contractor suggesting a pane of glass may have been supplied and fitted, but we have no confirmed visit date on our side and we know you wanted to be present.\n\nCould you let us know with a -> SIMULATED Sandboxed email provider: recorded, not delivered.
24. `update_step` {"evidence": "send_email email:sandbox-2, simulated.", "status": "done", "step_id": "tenant"} -> OK
25. `update_step` {"note": "No amount on invoice and no completion evidence; landlord informing and ledger expense deferred until contractor supplies amount and completion. Nothing to tell landlord yet that is established.", "status": "skipped", "step_id": "landlord"} -> OK
26. `update_step` {"status": "in_progress", "step_id": "sleep"} -> OK
27. `sleep` {"minutes": 10, "reason": "Waiting for contractor reply (amount, visit date, completion evidence) and tenant yes/no on whether the glass is fitted.", "wake_on": ["ticket:case", "email:sandbox-1", "email:sandbox-2"]} -> OK
