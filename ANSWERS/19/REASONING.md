# Reasoning for case 19

## What the system received

- `index.md`: read, 787 bytes
- `history.md`: read, 6645 bytes
- `attachments/remedial-works-invoice.pdf`: read, 176800 bytes
- 16 history events; latest timestamp 2025-09-11 07:00:00 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, landlord-approval, escalation-and-handover, communications, chasing-and-follow-up

## Plan

Goal: Resolve 18 Brindle Row move-out remedial case: verify contractor's reported completion/invoice (£174), inform landlord, record finances correctly, close only when evidence supports.

- [done] Rebuild state and record in ticket
  - evidence: Read ticket:case, traverse, property, party entities and skills; state summarised in step detail.
- [done] Email contractor for clarification
  - evidence: email:sandbox-1 (SIMULATED, not delivered)
- [done] Email landlord with invoice, flagged pending verification
  - evidence: email:sandbox-2 (SIMULATED)
- [blocked] Record invoice as expected expense (landlord charge) per contractor-invoice
  - note: Three category names rejected as unknown; no valid list available. Not recorded; invoice kept on ticket note and issue reported. Retry if a category is supplied.
- [done] Update ticket fields and add note
  - evidence: Ticket updated (status in progress, cost_actual 174, tags) and note added; version 3.
- [blocked] Wait for contractor reply; then decide resolve/close or escalate
  - note: Waiting on contractor reply to email:sandbox-1 (requested by 15 Sep). Follow-up chase due about 12 Sep if nothing arrives (contractor chase timing 1 day), then call. On reply: verify photos/access, update landlord, resolve with resolution note; if the price/scope cannot be reconciled or the access story conflicts, hand to staff.

## Agent messages

1. Now the ticket update and note.
2. **Decision**
- The ticket stays open as "in progress". I did not resolve it, because the contractor's report of completion is unverified. There are no photos or visit record, and no tenant to confirm, as Tomas Venn left on 27 August. The invoice (£174, ref NBL-019-INV-11) has no item prices, no VAT basis and no attendance date. It is also unclear how the contractor got in, since the agency held the keys.
- The contractor did the work despite our 7 September email asking for a quote only and no start without written authority. He told Maya by phone on 10 September that he misread the instruction.
- I did not escalate to staff. The amount is small, and the landlord's 7 September reply ("proceed with the remedial works") set no price limit. The living-room blind was replaced with a new Venetian blind when only a repair was requested. I flagged that to the landlord and asked the contractor to explain it.

**Actions**
- I emailed the contractor (SIMULATED, email:sandbox-1, not delivered). I asked for the attendance date and how access was gained, a price per item with the VAT basis, the reason for the blind replacement, and before and after photos. I told him not to do any further work without written authority, and asked for a reply by 15 September.
- I emailed the landlord, Mr Marlow (SIMULATED, email:sandbox-2, not delivered). I told him the work is reported done but not verified, the invoice is £174 with VAT not stated, and the blind was replaced rather than repaired. I also told him the contractor started before authorisation, that no decision is needed from him now, and that staff would come back to him on any deposit recovery.
- I updated the ticket to status "in progress", category "other", urgency "routine" and cost_actual 174. I tagged it "move-out" and "completion-unverified" and added a full state note.
- I could not post the £174 charge to the ledger. `record_transaction` rejected "repairs", "contractor_expense" and "maintenance" as unknown categories, and I had no list of valid ones. I reported this as workflow issue `workflow_issue:768915f2211f4440`. No payment was made or initiated.
- I did not contact the former tenant, because nobody is at the property to confirm completion.
- I set the plan step waiting on the contractor to blocked and put the run to sleep. The wake triggers are the ticket, the contractor and email:sandbox-1.

**Staff involvement**
- No handover has been made and none is needed yet.
- Whether any of this cost is recovered from the outgoing tenant's deposit is a staff decision. I have not asked staff for it.
- I would hand over if the contractor's answers conflict on access, price or scope, or if the landlord objects to the invoice.

**Open items**
- The contractor's reply is outstanding: access and date, item prices, VAT, blind rationale and photos. A chase is due around 12 September, then a call.
- Once the reply is satisfactory, I will update the landlord, resolve the ticket with a resolution note and give a recurrence route.
- The £174 charge still needs posting once a valid ledger category is known.
- Both emails were sandboxed, so neither was actually delivered.

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
10. `get_skill` {"skill": "communications"} -> OK
11. `get_skill` {"skill": "chasing-and-follow-up"} -> OK
12. `get_entity` {"id": "company:case-contractor"} -> OK
13. `get_entity` {"id": "person:case-landlord"} -> OK
14. `get_entity` {"id": "person:agency-staff"} -> OK
15. `get_property` {"property": "property:case"} -> OK
16. `create_plan` {"goal": "Resolve 18 Brindle Row move-out remedial case: verify contractor's reported completion/invoice (£174), inform landlord, record finances correctly, close only when evidence supports.", "steps": [{"id": "s1", "title": "Rebuild state and record in ticket", "detail": "Issues: six items done pe -> OK
17. `update_step` {"step_id": "s1", "status": "done", "evidence": "Read ticket:case, traverse, property, party entities and skills; state summarised in step detail."} -> OK
18. `update_step` {"step_id": "s2", "status": "in_progress"} -> OK
19. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "18 Brindle Row, Larkspur Vale, ZZ1 1ZZ – invoice NBL-019-INV-11: details needed", "body": "Hello Rowan,\n\nThank you for sending invoice NBL-019-INV-11 (£174.00, dated 11 September) for 18 Brindle Row. We have the invoice, but before we can pas -> SIMULATED Sandboxed email provider: recorded, not delivered.
20. `update_step` {"evidence": "email:sandbox-1 (SIMULATED, not delivered)", "status": "done", "step_id": "s2"} -> OK
21. `update_step` {"status": "in_progress", "step_id": "s3"} -> OK
22. `send_email` {"body": "Dear Mr Marlow,\n\nRe: remedial works at 18 Brindle Row, Larkspur Vale, ZZ1 1ZZ.\n\nFollowing your approval on 7 September to proceed with the remedial works, here is an update.\n\n- Alder & Finch Repairs report that they have completed all six items (floorboard and carpet beside the firep -> SIMULATED Sandboxed email provider: recorded, not delivered.
23. `update_step` {"evidence": "email:sandbox-2 (SIMULATED)", "status": "done", "step_id": "s3"} -> OK
24. `update_step` {"status": "in_progress", "step_id": "s4"} -> OK
25. `get_ledger` {"property": "property:case"} -> OK
26. `record_transaction` {"fields": {"kind": "charge", "category": "repairs", "amount_minor": 17400, "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoice NBL-019-INV-11 remedial works (six items); VAT not stated; completion pending verification"}, "paid_to": "company:case-contractor", "prop -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
27. `record_transaction` {"fields": {"amount_minor": 17400, "category": "contractor_expense", "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoice NBL-019-INV-11 remedial works (six items); VAT not stated; completion pending verification", "kind": "charge"}, "paid_to": "company:case-contrac -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
28. `record_transaction` {"fields": {"amount_minor": 17400, "category": "maintenance", "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoice NBL-019-INV-11 remedial works (six items); VAT not stated; completion pending verification", "kind": "charge"}, "paid_to": "company:case-contractor", " -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
29. `report_workflow_issue` {"category": "missing_step", "description": "contractor-invoice says to record an expected expense charge but does not name the valid transaction category. record_transaction rejected 'repairs', 'contractor_expense' and 'maintenance' as 'Unknown transaction category', so the £174 invoice could not b -> OK
30. `update_step` {"note": "Three category names rejected as unknown; no valid list available. Not recorded; invoice kept on ticket note and issue reported. Retry if a category is supplied.", "status": "blocked", "step_id": "s4"} -> OK
31. `update_step` {"status": "in_progress", "step_id": "s5"} -> OK
32. `update_entity` {"fields": {"status": "in progress", "urgency": "routine", "category": "other", "cost_actual": 174, "tags": ["move-out", "completion-unverified"]}, "id": "ticket:case", "reason": "Contractor reports works done and invoiced £174 (events 013-016); completion unverified so not resolved. Handyman move-o -> OK
33. `add_note` {"id": "ticket:case", "note": "State 11 Sep 2025. Landlord (Ivo Marlow) approved 'remedial works' 7 Sep, no price limit. Agency asked Alder & Finch for a quote only and no start until written authority (events 007/008). Contractor told Maya by phone on 10 Sep he misread the instruction and completed -> OK
34. `update_step` {"evidence": "Ticket updated (status in progress, cost_actual 174, tags) and note added; version 3.", "status": "done", "step_id": "s5"} -> OK
35. `update_step` {"note": "Waiting on contractor reply to email:sandbox-1 (requested by 15 Sep). Follow-up chase due about 12 Sep if nothing arrives (contractor chase timing 1 day), then call. On reply: verify photos/access, update landlord, resolve with resolution note; if the price/scope cannot be reconciled or th -> OK
36. `sleep` {"minutes": 10, "reason": "Waiting for contractor reply to email:sandbox-1 (access, date, item prices, VAT, photos). No chase until about 12 Sep.", "wake_on": ["ticket:case", "company:case-contractor", "email:sandbox-1"]} -> OK
