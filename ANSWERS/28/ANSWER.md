# Case 28: Move-out maintenance request

Run: **done** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:02:04+00:00

## Decision

**Decision**
- The landlord arranged and reported the works herself, so I resolved the ticket. The property is vacant, so there is no tenant to confirm.
- The landlord's 18 Sep email says the work is complete, and nobody disputes it.
- She declined Pineglass's £564.48 quote on 13 Sep and used her own contractor, so the agency has no approval on record and no spend. She pays her contractor directly.
- Her email gave no completion date, photos or invoice. I recorded that and asked for them rather than treating it as proven.
- Any recovery from the outgoing tenant's deposit is a staff decision. Nothing has been proposed or charged.
- I did not chase her. Talia's 08:46 request for a cost breakdown and tenant-responsibility view is only about 6 hours old.

**Actions**
- I added a state note to `ticket:case`.
- I sent the landlord one email, `email:sandbox-1`. It records the job as done and says costs are hers to settle with her contractor. It asks for the work date, contractor name, photos and itemised invoice. It says deposit deductions are decided by our staff, and that we will reopen the job if the work is incomplete. The email is SIMULATED and was not delivered.
- I set `ticket:case` to status resolved, urgency routine, category other, with a resolution text.
- I did not contact the former tenant or Pineglass; Pineglass was already told on 14 Sep not to attend.

**Staff involvement**
- No handover is needed now.
- Staff will need to decide on any deposit deduction if the landlord asks for one and sends evidence.

**Open items**
- I am waiting on the landlord's reply with the date, contractor, photos and invoice.
- If she replies with a cost or a tenant-responsibility claim, I will hand that to staff.
- If she has not replied in about a week, chase her once.
- The ticket has no `cost_actual`, because the cost is unknown.
- The invoice is for the landlord to pay directly; the agency pays nothing.

## Escalation to staff

- Handover note on ticket:case

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Note on ticket:case | OK |
| 2 | Email to landlord@case.sandbox.invalid: 42 Mallowfen Crescent, Ternwick, ZZ1 1ZZ – move-out works (NBL-028) recorded as done | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 3 | Update ticket:case: category, resolution, status, urgency | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to landlord@case.sandbox.invalid: 42 Mallowfen Crescent, Ternwick, ZZ1 1ZZ – move-out works (NBL-028) recorded as done

```text
Dear Ms Quill,

Thank you for your email of 18 September confirming that the move-out works at 42 Mallowfen Crescent (meter cabinet door hinges, four nails and paint touch-up in Bedroom 1, sticker residue on the front door) have been completed. We have recorded the job as done on that basis, as arranged by you with your own contractor. As you declined Pineglass's quote, we have not instructed or paid anyone, and any invoice from your contractor is for you to settle directly.

For our file, and in case any part of the cost is to be reviewed against the former tenant's deposit, it would help if you could send, when convenient: the date of the work, your contractor's name, any photos, and the itemised invoice. This is a follow-up to Talia's email of 18 September. Please note that any decision about deposit deductions is made by our staff, and nothing has been proposed or charged.

If the work turns out not to be complete, just let us know and we will reopen the job.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Sandboxed environment: this email is SIMULATED.)
```


## What failed

Nothing failed.

## Final state

- Ticket status: resolved, urgency: routine, tags: none
- Plan step [done]: Rebuild state and record note
- Plan step [done]: Resolve ticket with resolution
- Plan step [done]: Email landlord: cost route, closure, optional evidence
- Plan step [done]: Report and sleep/finish
