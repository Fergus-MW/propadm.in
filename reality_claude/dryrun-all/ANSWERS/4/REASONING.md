# Reasoning for case 4

## What the system received

- `index.md`: read, 1514 bytes
- `history.md`: read, 10827 bytes
- `attachments/attachment-01-checkout-inspection-report.pdf`: read, 110783 bytes
- `attachments/attachment-02-cleaning-quotation.pdf`: read, 70244 bytes
- `attachments/attachment-03-cleaning-invoice.pdf`: read, 73298 bytes
- 42 history events; latest timestamp 2025-11-14 00:01:08 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, escalation-and-handover, reconcile-ledger, communications

## Plan

Goal: Close out Checkout Clean case: validate £90 invoice vs approved £90 quote, record expected expense, update ticket, inform parties, flag deposit/photo points to staff

- [done] Read property, ledger, contractor, landlord records
  - evidence: Property/ledger empty (no transactions, balances 0); contacts on record for landlord, contractor, staff. State: approval 'Pls go ahead' (event 012) for £90 quote; contractor reports done (036); invoice £90 same scope (attachment-03); invoice forwarded to landlord (037); property not tenanted; no photos; system closed ticket.
- [done] Validate invoice vs quote/approval and record expense charge
  - evidence: TX-2025-000001 recorded £90 expense
- [done] Update ticket (status, cost_actual, resolution) and add note
  - evidence: ticket v2 resolved, cost_actual 9000, needs-staff; note added
- [done] Notify landlord/contractor as needed; staff email on deposit recovery decision and missing photos
  - evidence: email:sandbox-1 (staff) and email:sandbox-2 (contractor), both SIMULATED, not delivered. Landlord already sent invoice in event 037; tenant none (vacant).
- [done] Final report
  - evidence: Report written in final message

## Agent messages

1. Now the note and staff email.
2. ## Decision
The £90 checkout clean is complete and approved, and I recorded the invoice as an expected expense. The landlord approved the £90 quote on 24 Oct ("Pls go ahead"), and the invoice dated 14/11/2025 is £90 for the same scope. The contractor reported the job done on 13 Nov, and the landlord was sent the invoice on 14 Nov. The property is vacant, so there was no tenant to confirm completion. The ticket is resolved, with the cost route being invoice to landlord. Whether to recover any of the cost from the outgoing tenant's deposit is a staff decision, so I have not made one.

## Actions
- **Ledger:** I recorded TX-2025-000001, a £90 expense charge to the contractor linked to the ticket and property. No payment was made or initiated.
- **Ticket:** I set it to resolved with `cost_actual` of £90 and a resolution summary, and tagged it `needs-staff`. I added a handover note covering the deposit-recovery question, the missing photos and the date conflict.
- **Emails:** I emailed staff the handover (email:sandbox-1). I also emailed the contractor to confirm the invoice matches the quote and ask for any before/after photos (email:sandbox-2). Both are SIMULATED and were not actually delivered.
- **Not sent:** I sent no tenant message, because the property is vacant, and no new landlord email, because the invoice already went to them on 14 Nov.
- **Category lookup:** `record_transaction` rejected the categories "contractor_expense", "repairs", "maintenance" and "repair" as unknown, and accepted "expense". I found that by trial and error, and I have not reported it as a workflow issue.

## Staff involvement
Staff need to decide whether any of the £90 is recovered from the outgoing tenant's deposit. The quote email to the landlord said "the clean will be for the tenant", but the landlord's reply did not mention recovery.

## Open items
- **Staff decision:** the deposit recovery above is still open.
- **Completion evidence:** it rests on the contractor's word alone, with no photos and no tenant to check. I have asked the contractor for photos, and there has been no reply yet.
- **Report dates:** the checkout report shows an appointment date of 23 June 2026 and compares against 15 Aug 2025, yet it was signed on 24 Oct 2025. I did not rely on its dates.
- **Condition issues:** the report also lists a failed en-suite pop-up plug and flaking paint. The £90 clean did not cover these, and no repair is in scope here. I have not raised them with the landlord.
- **Payment:** the landlord's payment to the contractor has not been confirmed. Payment confirmation is not needed to close the ticket.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "job-completion"} -> OK
6. `get_skill` {"skill": "contractor-invoice"} -> OK
7. `get_skill` {"skill": "escalation-and-handover"} -> OK
8. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
9. `create_plan` {"goal": "Close out Checkout Clean case: validate £90 invoice vs approved £90 quote, record expected expense, update ticket, inform parties, flag deposit/photo points to staff", "steps": [{"id": "s1", "title": "Read property, ledger, contractor, landlord records"}, {"id": "s2", "title": "Validate in -> OK
10. `get_property` {"property": "property:case"} -> OK
11. `get_ledger` {"property": "property:case"} -> OK
12. `get_entity` {"id": "company:case-contractor"} -> OK
13. `get_entity` {"id": "person:case-landlord"} -> OK
14. `get_entity` {"id": "person:agency-staff"} -> OK
15. `update_step` {"step_id": "s1", "status": "done", "evidence": "Property/ledger empty (no transactions, balances 0); contacts on record for landlord, contractor, staff. State: approval 'Pls go ahead' (event 012) for £90 quote; contractor reports done (036); invoice £90 same scope (attachment-03); invoice forwarded -> OK
16. `update_step` {"step_id": "s2", "status": "in_progress"} -> OK
17. `record_transaction` {"property_id": "property:case", "ticket_id": "ticket:case", "paid_to": "company:case-contractor", "skill": "contractor-invoice", "fields": {"kind": "charge", "category": "contractor_expense", "amount_minor": 9000, "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean (living space -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
18. `get_skill` {"skill": "reconcile-ledger"} -> OK
19. `record_transaction` {"evidence": [{"note": "Invoice total £90, no VAT shown", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}, {"note": "Quote £90, same scope", "source": "ticket:case attachment-02-cleaning-quotation.pdf"}, {"note": "Landlord email 'Pls go ahead'", "source": "ticket:case history event 012"} -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
20. `record_transaction` {"evidence": [{"note": "Invoice total £90", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}], "fields": {"amount_minor": 9000, "category": "maintenance", "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice 14/11/2025, matches approved £ -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
21. `record_transaction` {"evidence": [{"note": "Invoice total £90", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}], "fields": {"amount_minor": 9000, "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice 14/11/2025, matches approved £90 quote; expected expense, -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
22. `record_transaction` {"fields": {"amount_minor": 9000, "category": "expense", "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice 14/11/2025 matches approved £90 quote; expected expense, no payment made", "kind": "charge"}, "paid_to": "company:case-contractor", "proper -> ERROR {'code': 'invalid', 'message': 'effective_date must be an ISO date'}
23. `record_transaction` {"fields": {"amount_minor": 9000, "category": "repair", "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice 14/11/2025 matches approved £90 quote; expected expense, no payment made", "kind": "charge"}, "paid_to": "company:case-contractor", "propert -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
24. `record_transaction` {"evidence": [{"note": "Invoice total £90, scope matches quote", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}, {"note": "Landlord approval 'Pls go ahead' for £90 quote", "source": "ticket:case history event 012"}], "fields": {"amount_minor": 9000, "category": "expense", "currency": "G -> OK
25. `update_entity` {"id": "ticket:case", "version": 33, "fields": {"status": "resolved", "cost_actual": 9000, "resolution": "Checkout clean (living space vacuum and light clean; en-suite limescale removal) reported complete by contractor 2025-11-13 (event 036). Invoice £90 matches approved £90 quote and scope; forward -> ERROR {'code': 'conflict', 'message': 'Stale entity version; current version is 1'}
26. `update_entity` {"fields": {"cost_actual": 9000, "resolution": "Checkout clean (living space vacuum and light clean; en-suite limescale removal) reported complete by contractor 2025-11-13 (event 036). Invoice £90 matches approved £90 quote and scope; forwarded to landlord 2025-11-14. Property vacant, so no tenant c -> OK
27. `add_note` {"id": "ticket:case", "version": 2, "reason": "Handover of deposit-recovery decision and record of conflicts found while validating invoice", "note": "STAFF DECISION NEEDED: whether any of the £90 checkout clean is recovered from the outgoing tenant's deposit. Urgency: today (not urgent).\nTicket ti -> OK
28. `get_skill` {"skill": "communications"} -> OK
29. `send_email` {"to": ["maintenance-team@agency.sandbox.invalid"], "subject": "Staff decision: deposit recovery for checkout clean, Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ", "body": "STAFF DECISION NEEDED: whether any of the £90 checkout clean is recovered from the outgoing tenant's deposit. Urgency: today.\nTic -> SIMULATED Sandboxed email provider: recorded, not delivered.
30. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ - invoice received, any photos?", "body": "Hi Clara,\n\nThank you for completing the checkout clean at Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ. Your invoice for £90 matches the approved quote and has  -> SIMULATED Sandboxed email provider: recorded, not delivered.
31. `update_step` {"evidence": "TX-2025-000001 recorded £90 expense", "status": "done", "step_id": "s2"} -> OK
32. `update_step` {"evidence": "ticket v2 resolved, cost_actual 9000, needs-staff; note added", "status": "done", "step_id": "s3"} -> OK
33. `update_step` {"evidence": "email:sandbox-1 (staff) and email:sandbox-2 (contractor), both SIMULATED, not delivered. Landlord already sent invoice in event 037; tenant none (vacant).", "status": "done", "step_id": "s4"} -> OK
34. `update_step` {"evidence": "Report written in final message", "status": "done", "step_id": "s5"} -> OK
