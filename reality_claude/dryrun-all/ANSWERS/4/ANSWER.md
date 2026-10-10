# Case 4: Checkout Clean

Run: **done** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:14:32+00:00

## Decision

## Decision
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

## Escalation to staff

- Tagged ticket:case needs-staff
- Tagged ticket:case needs-staff
- Handover note on ticket:case
- Emailed agency staff: Staff decision: deposit recovery for checkout clean, Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | record_transaction: {"property_id": "property:case", "ticket_id": "ticket:case", "paid_to": "company:case-contractor", "skill": "contractor-invoice", "fields": {"kind": "charge", " | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 2 | record_transaction: {"evidence": [{"note": "Invoice total £90, no VAT shown", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}, {"note": "Quote £90, same scope", "source | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 3 | record_transaction: {"evidence": [{"note": "Invoice total £90", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}], "fields": {"amount_minor": 9000, "category": "maintena | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 4 | record_transaction: {"evidence": [{"note": "Invoice total £90", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}], "fields": {"amount_minor": 9000, "currency": "GBP", "d | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 5 | record_transaction: {"fields": {"amount_minor": 9000, "category": "expense", "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice | ERROR - {'code': 'invalid', 'message': 'effective_date must be an ISO date'} |
| 6 | record_transaction: {"fields": {"amount_minor": 9000, "category": "repair", "currency": "GBP", "date": "2025-11-14", "description": "Checkout clean - Stonebridge Solutions invoice  | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 7 | record_transaction: {"evidence": [{"note": "Invoice total £90, scope matches quote", "source": "ticket:case attachment-03-cleaning-invoice.pdf"}, {"note": "Landlord approval 'Pls g | OK |
| 8 | Update ticket:case: cost_actual, resolution, status, tags | ERROR - {'code': 'conflict', 'message': 'Stale entity version; current version is 1'} |
| 9 | Update ticket:case: cost_actual, resolution, status, tags | OK |
| 10 | Note on ticket:case | OK |
| 11 | Email to maintenance-team@agency.sandbox.invalid: Staff decision: deposit recovery for checkout clean, Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 12 | Email to contractor@case.sandbox.invalid: Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ - invoice received, any photos? | SIMULATED - Sandboxed email provider: recorded, not delivered. |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to maintenance-team@agency.sandbox.invalid: Staff decision: deposit recovery for checkout clean, Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ

```text
STAFF DECISION NEEDED: whether any of the £90 checkout clean is recovered from the outgoing tenant's deposit. Urgency: today.
Ticket ticket:case, property Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ. Stage: resolved; invoice with landlord. Waiting on: staff.
Confirmed: landlord approved the £90 quote ("Pls go ahead", 24 Oct); Stonebridge Solutions invoice dated 14/11/2025 is £90, same scope as the quote, no VAT shown; contractor reports the job complete (13 Nov); invoice sent to landlord 14 Nov; expected expense recorded as TX-2025-000001 (£90, no payment made).
Reported, not confirmed: completion rests on the contractor's word only; property is vacant so no tenant check was possible; no before/after photos were uploaded.
Conflicts: the checkout report shows an appointment date of 23 June 2026 but was signed 24 Oct 2025, so I have not relied on its dates. The quote email to the landlord said "the clean will be for the tenant", but the landlord's reply did not address recovery.
Done: invoice validated against quote, expense recorded, ticket set to resolved. Not done: no deposit deduction or tenant charge, no payment initiated (not my decision).
Please decide whether to recover the cost from the deposit. Note: this email is sent through a sandboxed provider (SIMULATED).
Regards, Maintenance assistant
```

**send_email** to contractor@case.sandbox.invalid: Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ - invoice received, any photos?

```text
Hi Clara,

Thank you for completing the checkout clean at Flat 2, 172 Alder Lane, Bellmere, ZZ3 1ZZ. Your invoice for £90 matches the approved quote and has been passed to the landlord.

If you took any before or after photos of the living space or en-suite, please send them over for our records. If you did not, just let us know.

Regards,
Maintenance assistant, Northbridge Lettings
```


## What failed

- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'effective_date must be an ISO date'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- update_entity: {'code': 'conflict', 'message': 'Stale entity version; current version is 1'}

## Final state

- Ticket status: resolved, urgency: unset, tags: needs-staff
- Plan step [done]: Read property, ledger, contractor, landlord records
- Plan step [done]: Validate invoice vs quote/approval and record expense charge
- Plan step [done]: Update ticket (status, cost_actual, resolution) and add note
- Plan step [done]: Notify landlord/contractor as needed; staff email on deposit recovery decision and missing photos
- Plan step [done]: Final report
