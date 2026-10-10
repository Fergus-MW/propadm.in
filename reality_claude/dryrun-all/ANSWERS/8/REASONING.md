# Reasoning for case 8

## What the system received

- `index.md`: read, 1940 bytes
- `history.md`: read, 12752 bytes
- `attachments/attachment-01-check-out-inspection-report.pdf`: read, 213515 bytes
- `attachments/attachment-02-estimate.pdf`: read, 74406 bytes
- `attachments/attachment-03-check-out-inspection-report.pdf`: read, 129002 bytes
- `attachments/attachment-04-invoice.pdf`: read, 73257 bytes
- 49 history events; latest timestamp 2025-06-17 02:24:25 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, contractor-invoice, job-completion, landlord-approval, escalation-and-handover, reconcile-ledger, landlord-statement, communications

## Plan

Goal: Process landlord's 'Ok to pay' for Alder Compliance/Eliza invoice £1,190 on Flat 5, 55 Lantern Quay check-out works: validate, record expense, chase photos, update ticket, inform landlord.

- [done] Read state: property, ledger, provider, landlord, contractor records
  - evidence: Read ticket, property (empty ledger, balances 0), landlord/contractor contacts. State: issues: invoice £1,190 (no VAT stated) vs quote £1,370 no VAT approved by landlord 2025-05-25 (event 038) - within approval; tap not replaced (cheaper); carpet not replaced (quote said stays); no completion photos (event 046); wrong address Flat 13 83 Harbour View in event 045 email (typo, property of record Flat 5 Lantern Quay; invoice itself says Flat 5); dates odd (invoice 09/03/2026, inspection 5 Jan 2026). Landlord 'Ok to pay' 2025-06-17 (event 049). Property untenanted - no tenant contact needed. Depos
- [done] Validate invoice vs quote/approval and record expected expense charge
  - evidence: Recorded transaction:tx-2025-000001 charge £1,190.00 category expense, paid_to company:case-contractor, ticket:case, skill contractor-invoice. Within £1,370 approved quote; no payment initiated.
- [done] Update ticket (status resolved, cost_actual, note) 
  - evidence: update_entity ticket:case v1->v2 status=resolved, cost_actual 119000, cost_estimate 137000; add_note v3 recorded.
- [done] Email landlord (pay-direct route, wrong-address correction) and contractor (photos, VAT confirm)
  - evidence: send_email email:sandbox-1 (landlord) and email:sandbox-2 (contractor), both status SIMULATED, not delivered.
- [done] Final report / sleep if waiting
  - evidence: Final report written; contractor photo reply is a non-blocking open item (resolution per job-completion: landlord-owned job reported done, not disputed).

## Agent messages

1. Try plausible category names.
2. ## Decision
The landlord's "Ok to pay" is valid, so I processed the invoice. The invoice is £1,190.00, with VAT not stated. That is below the £1,370 quote the landlord approved on 25 May ("Please go ahead with Eliza"), so no new approval is needed. The tap was not replaced and the carpet was left in place, as the quote said. The property is empty, so there was no tenant to confirm the work. The landlord pays the contractor directly. The agency did not initiate any payment.

## Actions
- **Ledger:** I recorded `transaction:tx-2025-000001`, a £1,190.00 charge in the "expense" category for the contractor, against the property and `ticket:case`. The tool marked its status "cleared" even though I meant it as an expected expense, and no payment has been made.
- **Ticket:** I set `ticket:case` to resolved, with `cost_actual` £1,190 and `cost_estimate` £1,370, and recorded the resolution text. I added a note covering the approval basis and these data issues:
  - The 2 June email named the wrong address (Flat 13, 83 Harbour View). The property of record is Flat 5, 55 Lantern Quay.
  - The invoice is dated 09/03/2026 and the inspection 5 Jan 2026, which don't fit the case timeline.
  - One attachment (attachment-87) is unavailable.
- **Landlord email:** I sent `email:sandbox-1`, which is SIMULATED and not delivered. It confirms the £1,190 against the approved quote, says payment goes direct to the contractor, corrects the address and flags that no completion photos have arrived.
- **Contractor email:** I sent `email:sandbox-2`, also SIMULATED and not delivered. It asks for completion photos, the VAT position and the correct invoice date. It contains no bank details.

## Staff involvement
None needed now. Recovering any of this cost from the outgoing tenant's deposit would be a staff decision. It has not been raised or promised.

## Open items
- **Completion photos:** still missing. I'll pass them to the landlord and add them to the record when the contractor replies. I did not make payment conditional on them.
- **VAT basis and invoice date:** both unconfirmed by the contractor.
- **Email delivery:** both emails are sandboxed, so neither has reached anyone.
- **Ledger category list:** `record_transaction` rejected several category names before accepting "expense". There is no documented list of valid categories, which may be worth raising as a workflow issue.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "contractor-invoice"} -> OK
6. `get_skill` {"skill": "job-completion"} -> OK
7. `get_skill` {"skill": "landlord-approval"} -> OK
8. `get_skill` {"skill": "escalation-and-handover"} -> OK
9. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
10. `create_plan` {"goal": "Process landlord's 'Ok to pay' for Alder Compliance/Eliza invoice £1,190 on Flat 5, 55 Lantern Quay check-out works: validate, record expense, chase photos, update ticket, inform landlord.", "steps": [{"id": "s1", "title": "Read state: property, ledger, provider, landlord, contractor recor -> OK
11. `get_property` {"property": "property:case"} -> OK
12. `get_ledger` {"property": "property:case"} -> OK
13. `get_entity` {"id": "company:case-contractor"} -> OK
14. `get_entity` {"id": "person:case-landlord"} -> OK
15. `update_step` {"step_id": "s1", "status": "done", "evidence": "Read ticket, property (empty ledger, balances 0), landlord/contractor contacts. State: issues: invoice £1,190 (no VAT stated) vs quote £1,370 no VAT approved by landlord 2025-05-25 (event 038) - within approval; tap not replaced (cheaper); carpet not  -> OK
16. `update_step` {"step_id": "s2", "status": "in_progress"} -> OK
17. `record_transaction` {"skill": "contractor-invoice", "property_id": "property:case", "ticket_id": "ticket:case", "paid_to": "company:case-contractor", "fields": {"kind": "charge", "category": "contractor_invoice", "amount_minor": 119000, "currency": "GBP", "description": "Check-out works invoice (Alder Compliance / Eliz -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
18. `get_skill` {"skill": "reconcile-ledger"} -> OK
19. `record_transaction` {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to pay", "source": "ticket:case history event 049"}], "fields": {"amount_minor": 119000, "category": "repairs", "currency": "GBP", "descriptio -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
20. `record_transaction` {"fields": {"amount_minor": 119000, "category": "maintenance", "currency": "GBP", "description": "Check-out works invoice Flat 5, 55 Lantern Quay (Alder Compliance/Eliza Bennett). VAT not stated. Below £1,370 quote approved 2025-05-25; landlord said Ok to pay 2025-06-17. Expected expense only.", "ki -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
21. `record_transaction` {"fields": {"amount_minor": 119000, "category": "contractor_expense", "currency": "GBP", "description": "Check-out works invoice", "kind": "charge"}, "paid_to": "company:case-contractor", "property_id": "property:case", "skill": "contractor-invoice", "ticket_id": "ticket:case"} -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
22. `search` {"query": "transaction category expected expense charge contractor", "limit": 10} -> OK
23. `get_skill` {"skill": "landlord-statement"} -> OK
24. `record_transaction` {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to pay", "source": "ticket:case history event 049"}], "fields": {"amount_minor": 119000, "category": "expense", "currency": "GBP", "descriptio -> ERROR {'code': 'invalid', 'message': 'effective_date must be an ISO date'}
25. `record_transaction` {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to pay", "source": "ticket:case history event 049"}], "fields": {"amount_minor": 119000, "category": "expense", "currency": "GBP", "effective_ -> OK
26. `update_step` {"evidence": "Recorded transaction:tx-2025-000001 charge £1,190.00 category expense, paid_to company:case-contractor, ticket:case, skill contractor-invoice. Within £1,370 approved quote; no payment initiated.", "status": "done", "step_id": "s2"} -> OK
27. `update_step` {"status": "in_progress", "step_id": "s3"} -> OK
28. `update_entity` {"id": "ticket:case", "version": 1, "fields": {"status": "resolved", "cost_estimate": 137000, "cost_actual": 119000, "resolution": "Check-out works completed by Alder Compliance/Eliza Bennett: bathroom sanded, filled and painted with damp paint; main room walls and ceiling painted; bathroom lino rep -> OK
29. `get_skill` {"skill": "communications"} -> OK
30. `send_email` {"to": ["landlord@case.sandbox.invalid"], "subject": "Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – check-out works invoice noted as OK to pay", "body": "Hi,\n\nThank you for confirming \"Ok to pay\" for the check-out works at Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ.\n\nFor the record:\n- Invoic -> SIMULATED Sandboxed email provider: recorded, not delivered.
31. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – completion photos and invoice details (Job NBL-008-3466)", "body": "Hello,\n\nThank you for completing the check-out works at Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ. The landlord has seen your  -> SIMULATED Sandboxed email provider: recorded, not delivered.
32. `add_note` {"id": "ticket:case", "note": "Agent note 2025-06-17: Landlord email 'Ok to pay' (event 049) covers invoice £1,190 (attachment-04), below £1,370 quote approved 'Go ahead with Eliza' 2025-05-25. Expense recorded as transaction:tx-2025-000001 (landlord pays contractor directly; agency initiated no pay -> OK
33. `update_step` {"evidence": "update_entity ticket:case v1->v2 status=resolved, cost_actual 119000, cost_estimate 137000; add_note v3 recorded.", "status": "done", "step_id": "s3"} -> OK
34. `update_step` {"evidence": "send_email email:sandbox-1 (landlord) and email:sandbox-2 (contractor), both status SIMULATED, not delivered.", "status": "done", "step_id": "s4"} -> OK
35. `update_step` {"evidence": "Final report written; contractor photo reply is a non-blocking open item (resolution per job-completion: landlord-owned job reported done, not disputed).", "status": "done", "step_id": "s5"} -> OK
