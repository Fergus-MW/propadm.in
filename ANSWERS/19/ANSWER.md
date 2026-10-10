# Case 19: Move-out maintenance at 18 Brindle Row

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:01:25+00:00

## Decision

**Decision**
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

## Escalation to staff

- Handover note on ticket:case

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Email to contractor@case.sandbox.invalid: 18 Brindle Row, Larkspur Vale, ZZ1 1ZZ – invoice NBL-019-INV-11: details needed | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 2 | Email to landlord@case.sandbox.invalid: 18 Brindle Row – remedial works reported complete, invoice £174 (pending verification) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 3 | record_transaction: {"fields": {"kind": "charge", "category": "repairs", "amount_minor": 17400, "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoi | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 4 | record_transaction: {"fields": {"amount_minor": 17400, "category": "contractor_expense", "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoice NBL- | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 5 | record_transaction: {"fields": {"amount_minor": 17400, "category": "maintenance", "currency": "GBP", "date": "2025-09-11", "description": "Alder & Finch Repairs invoice NBL-019-INV | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 6 | report_workflow_issue: {"category": "missing_step", "description": "contractor-invoice says to record an expected expense charge but does not name the valid transaction category. reco | OK |
| 7 | Update ticket:case: category, cost_actual, status, tags, urgency | OK |
| 8 | Note on ticket:case | OK |
| 9 | Wait: Waiting for contractor reply to email:sandbox-1 (access, date, item prices, VAT, photos). No chase until about 12 Sep. (wake on ticket:case, company:case-contractor, email:sandbox-1) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to contractor@case.sandbox.invalid: 18 Brindle Row, Larkspur Vale, ZZ1 1ZZ – invoice NBL-019-INV-11: details needed

```text
Hello Rowan,

Thank you for sending invoice NBL-019-INV-11 (£174.00, dated 11 September) for 18 Brindle Row. We have the invoice, but before we can pass it on we need a few details in the body of your reply:

1. The date you attended and how you got into the property (the former tenant had already returned his keys, so please say who gave you access or which keys you used).
2. A price per item (floorboard/carpet, blind, cupboard handle, kitchen blind, toilet seat, gate hinge) and whether VAT is included, excluded or not applicable.
3. Why the living-room blind was replaced with a new Venetian blind rather than repaired, and what it cost.
4. Photos of the completed work (ideally before and after) for all six items.

As a reminder, our email of 7 September asked for a quotation only and for no work to start until we had reviewed the price and issued written authority. Please do not carry out any further work at this property without written authority from us.

Please reply by the end of Monday 15 September. Note that this email is sent in a sandboxed environment and is reported as SIMULATED.

Kind regards,
Maintenance assistant, Northbridge Lettings
```

**send_email** to landlord@case.sandbox.invalid: 18 Brindle Row – remedial works reported complete, invoice £174 (pending verification)

```text
Dear Mr Marlow,

Re: remedial works at 18 Brindle Row, Larkspur Vale, ZZ1 1ZZ.

Following your approval on 7 September to proceed with the remedial works, here is an update.

- Alder & Finch Repairs report that they have completed all six items (floorboard and carpet beside the fireplace, living-room front blind, under-stairs cupboard handle, kitchen blind, toilet seat and front-gate hinge). This is the contractor's report; we have not yet had photos or a visit narrative to confirm it, and the property is empty so there is no tenant to confirm it.
- They have invoiced £174.00 (ref NBL-019-INV-11, dated 11 September). VAT is not stated and the invoice is not itemised. The living-room blind was replaced with a new Venetian blind rather than repaired.
- We had asked the contractor for a quotation first and for no work to start until we had authorised it. They say they misunderstood and went ahead. The total is modest and you approved the works without a price limit, so we are not asking you to decide anything now.
- We have asked the contractor for the date and access details, a price per item, VAT basis and before/after photos. We will send you those when received. Please treat this invoice as pending our verification, and tell us if you have any concern about it.

Because the invoice is for checkout works, it is for you as landlord. Whether any part is recoverable from the outgoing tenant's deposit is a decision for our staff, and we will come back to you on that.

This email is sent in a sandboxed environment and is reported as SIMULATED.

Kind regards,
Maintenance assistant, Northbridge Lettings
```


## What failed

- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}

## Final state

- Ticket status: in progress, urgency: routine, tags: move-out, completion-unverified
- Plan step [done]: Rebuild state and record in ticket
- Plan step [done]: Email contractor for clarification
- Plan step [done]: Email landlord with invoice, flagged pending verification
- Plan step [blocked]: Record invoice as expected expense (landlord charge) per contractor-invoice (Three category names rejected as unknown; no valid list available. Not recorded; invoice kept on ticket note and issue reported. Retry if a category is supplied.)
- Plan step [done]: Update ticket fields and add note
- Plan step [blocked]: Wait for contractor reply; then decide resolve/close or escalate (Waiting on contractor reply to email:sandbox-1 (requested by 15 Sep). Follow-up chase due about 12 Sep if nothing arrives (contractor chase timing 1 day), then call. On reply: verify photos/access, update landlord, resolve with resolution note; if the price/scope cannot be reconciled or the access story conflicts, hand to staff.)
