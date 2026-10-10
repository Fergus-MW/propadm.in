# Case 8: Check-Out Works

Run: **done** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:15:48+00:00

## Decision

## Decision
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

## Escalation to staff

- Handover note on ticket:case

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | record_transaction: {"skill": "contractor-invoice", "property_id": "property:case", "ticket_id": "ticket:case", "paid_to": "company:case-contractor", "fields": {"kind": "charge", " | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 2 | record_transaction: {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 3 | record_transaction: {"fields": {"amount_minor": 119000, "category": "maintenance", "currency": "GBP", "description": "Check-out works invoice Flat 5, 55 Lantern Quay (Alder Complia | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 4 | record_transaction: {"fields": {"amount_minor": 119000, "category": "contractor_expense", "currency": "GBP", "description": "Check-out works invoice", "kind": "charge"}, "paid_to": | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 5 | record_transaction: {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to | ERROR - {'code': 'invalid', 'message': 'effective_date must be an ISO date'} |
| 6 | record_transaction: {"evidence": [{"note": "Invoice total £1,190.00, one line item", "source": "ticket:case attachments/attachment-04-invoice.pdf"}, {"note": "Landlord email: Ok to | OK |
| 7 | Update ticket:case: cost_actual, cost_estimate, resolution, status | OK |
| 8 | Email to landlord@case.sandbox.invalid: Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – check-out works invoice noted as OK to pay | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 9 | Email to contractor@case.sandbox.invalid: Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – completion photos and invoice details (Job NBL-008-3466) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 10 | Note on ticket:case | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to landlord@case.sandbox.invalid: Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – check-out works invoice noted as OK to pay

```text
Hi,

Thank you for confirming "Ok to pay" for the check-out works at Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ.

For the record:
- Invoice from Alder Compliance (Eliza Bennett): £1,190.00, VAT not stated on the invoice. This is below the £1,370.00 quote you approved on 25 May.
- Works invoiced: sand, fill and paint the bathroom with damp paint; paint all walls and the ceiling in the main room; replace the bathroom lino; repair the plug socket and shelf. The bathroom tap did not need replacing, and the carpet was not replaced (the quote left it in place).
- Please note our earlier email of 2 June quoted the wrong address (Flat 13, 83 Harbour View) in one line. The invoice and job are for Flat 5, 55 Lantern Quay, and I have recorded it against that property.

Payment: the invoice is payable by you directly to the contractor using the payment instructions on the invoice. We do not make the payment ourselves, and I have recorded it as an expected expense of £1,190.00 against this property.

We have not yet received completion photos from the contractor; I have asked them to send these and will pass them on when they arrive. If you would rather hold payment until you have seen them, that is your call.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Sent through the sandboxed email service; delivery is SIMULATED.)
```

**send_email** to contractor@case.sandbox.invalid: Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ – completion photos and invoice details (Job NBL-008-3466)

```text
Hello,

Thank you for completing the check-out works at Flat 5, 55 Lantern Quay, Cedarford, ZZ2 4ZZ. The landlord has seen your invoice for £1,190.00 and has said it is OK to pay; they will pay you directly.

To complete our records, please reply with:
1. Completion photos (bathroom walls/boxing, bathroom lino, plug socket, shelf, and the painted main room).
2. Confirmation of the VAT position on the invoice (we understand you do not charge VAT; the invoice states no tax).
3. The correct invoice date – the copy we hold is dated 09/03/2026, which looks like a typo.

Please put the details in the email body if any attachment fails to upload.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Sent through the sandboxed email service; delivery is SIMULATED.)
```


## What failed

- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'effective_date must be an ISO date'}

## Final state

- Ticket status: resolved, urgency: unset, tags: none
- Plan step [done]: Read state: property, ledger, provider, landlord, contractor records
- Plan step [done]: Validate invoice vs quote/approval and record expected expense charge
- Plan step [done]: Update ticket (status resolved, cost_actual, note) 
- Plan step [done]: Email landlord (pay-direct route, wrong-address correction) and contractor (photos, VAT confirm)
- Plan step [done]: Final report / sleep if waiting
