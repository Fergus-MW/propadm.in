# Case 15: Vacant Property Preparation

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:00:35+00:00

## Decision

**Decision**
- I am not instructing or booking the contractor, and I have not called `accept_quote`. The work stays on hold.
- The £665 Brindlewick quote (NBL-015-Q1, VAT not stated) is not clearly approved. On 8 and 8 Sep (events 008 and 010) the landlord said she would approve only if the cost is recovered from the former tenants' bond.
- The contractor was told "approved" without that condition (event 009).
- Her 17 Sep message "approved quote" does not say which quote it meant (event 016).
- Her approval request never listed the carpet and garden tasks (event 007).
- The quote does not cover the disturbed soil noted in the inspection.
- Separately, the work is held until the other major maintenance is completed. No completion date is recorded, and Mira's 25 Sep instruction is to wait three more working days.

**Actions**
- Emailed the landlord (email:sandbox-1). I asked which quote she approved, whether the bond condition still applies, and whether she accepts the scope. I offered a separate price for the soil and said a team member will follow up on the bond. I did not promise recovery.
- Updated the ticket: status triaged, urgency routine, cost_estimate 665, tags needs-staff, on-hold and vacant-property. I added a handover note.
- Emailed the staff team with the same handover (email:sandbox-2).
- Both emails are SIMULATED and were not delivered.
- I did not chase the contractor. The hold is agreed and they are not waiting on anything from us.
- I did not contact the tenant, as the property is vacant.

**Staff involvement**
Staff need to decide whether the work can be instructed before the deposit claim outcome, and who bears the £665 if the bond does not cover it. Deposit deductions are a staff matter. They should also check the deposit figure and handle the 28 Sep move-in risk.

**Open items**
- Waiting on the landlord's reply and the staff decision.
- Waiting on completion of the separate maintenance.
- Follow-up around 30 Sep, three working days after 25 Sep.
- The graph shows a deposit held of 0, but the case file says £650. Staff should check this.
- The plan step "wait" is blocked.

## Escalation to staff

- Tagged ticket:case needs-staff, on-hold, vacant-property
- Handover note on ticket:case
- Emailed agency staff: STAFF DECISION NEEDED: 18 Thistlevaunt Lane – bond condition on £665 clean quote (work on hold)

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Email to landlord@case.sandbox.invalid: 18 Thistlevaunt Lane, Orvelune, ZZ1 1ZZ – which quote did you approve? | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 2 | Update ticket:case: category, cost_estimate, status, tags, urgency | OK |
| 3 | Note on ticket:case | OK |
| 4 | Email to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED: 18 Thistlevaunt Lane – bond condition on £665 clean quote (work on hold) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Wait: Waiting on landlord reply, staff decision on bond condition, and completion of separate maintenance; follow-up due ~30 Sep. (wake on ticket:case, email:sandbox-1, email:sandbox-2) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to landlord@case.sandbox.invalid: 18 Thistlevaunt Lane, Orvelune, ZZ1 1ZZ – which quote did you approve?

```text
Dear Ms Quill,

Re: post-tenancy cleaning and garden work at 18 Thistlevaunt Lane, Orvelune, ZZ1 1ZZ (property vacant).

Your update of 17 September said "approved quote", but it did not say which quote. We hold two matters for this property, so we need to be sure before anyone is booked:

1. Brindlewick Turnover Services quote NBL-015-Q1 dated 8 September: £665 (VAT not stated). It covers degreasing the oven, hob and extractor; shampooing the carpets in Bedroom 1, stairs and landings; rubbish removal; treating kitchen grease and bathroom limescale; general sanitation of remaining areas; and weeding, cutting the grass and tidying the rear garden. It does not mention making good the soil disturbed by digging.
2. The separate major maintenance quote.

Could you please confirm:
(a) Did "approved quote" refer to the £665 cleaning and garden quote, the maintenance quote, or both?
(b) Your earlier replies on 8 September said approval of the £665 quote depended on the cost being recovered from the former tenants' bond. Does that condition still apply? Any deposit claim is being handled through the deposit process and its outcome cannot be guaranteed; a member of our team will follow up with you on that point.
(c) Are you happy with the scope listed above, including the carpet shampooing and garden work? The soil disturbance is not covered, so we can ask for a separate price if you wish.

If you would prefer to use your own contractor, please let us know. We are not booking the work yet. It remains on hold until the separate maintenance work is completed. We will confirm any date with you first.

Kind regards,
Maintenance assistant, Northbridge Lettings
```

**send_email** to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED: 18 Thistlevaunt Lane – bond condition on £665 clean quote (work on hold)

```text
STAFF DECISION NEEDED: Is the £665 Brindlewick quote (NBL-015-Q1) approved given the landlord's bond-recovery condition, and how will the deposit claim be handled?   Urgency: today
Ticket ticket:case, property 18 Thistlevaunt Lane, Orvelune, ZZ1 1ZZ. Stage: quote on file, work ON HOLD, no visit booked. Waiting on: separate major maintenance completion (no date recorded); landlord clarification (email sent, SIMULATED).
Decision needed: (1) Landlord said 8 Sep she would approve only if the cost is recovered from the former tenants' bond (ev 008, 010). The contractor was told "approved" without that condition (ev 009). Please decide whether work may be instructed before the deposit claim outcome, and who bears the £665 if the bond does not cover it. Deposit deductions/tenant charges are staff matters. (2) Prospective tenant wants to move in 28 Sep; the maintenance dependency puts that date at risk. Mira's 25 Sep instruction: wait three more working days (to about 30 Sep).
Confirmed: quote £665, VAT not stated, scope = oven/hob/extractor degrease, carpets Bed 1/stairs/landings, rubbish removal, kitchen grease and bathroom limescale, general sanitation, garden weed/cut/tidy (ev 006, quote PDF). £650 deposit held per ev 011 (the property record shows deposit_held 0, please check). Hold instruction given to contractor 10 and 16 Sep; contractor agreed to wait (ev 013).
Reported, not confirmed: landlord's 17 Sep "approved quote" (ev 016) does not say which quote (cleaning or separate maintenance). Tenant-attributed damage and costs exceeding the deposit (Mira, ev 011).
Conflicts: the landlord's approval request (ev 007) did not list the carpet and garden tasks, so the scope she agreed to is unclear. The quote does not cover the disturbed soil noted in the inspection. This blocks instructing the contractor.
Done so far: emailed the landlord (SIMULATED) asking which quote she approved, whether the bond condition stands, and whether she accepts the scope; told her a team member will follow up on the bond. Ticket tagged needs-staff, status triaged, cost_estimate 665. Deliberately not done: no instruction or booking to the contractor, no accept_quote (approval conditional/ambiguous), no tenant contact (property vacant), no deposit or tenant-charge statement.
Safety steps given: none needed. Next check: 30 Sep or on landlord reply.
```


## What failed

Nothing failed.

## Final state

- Ticket status: triaged, urgency: routine, tags: needs-staff, on-hold, vacant-property
- Plan step [done]: Record state/analysis on ticket
- Plan step [done]: Email landlord to clarify which quote 'approved quote' meant and whether approval still conditional on bond
- Plan step [done]: Hand over to staff: bond/deposit condition, approval ambiguity, 28 Sep timeline, scope gap
- Plan step [done]: Update ticket fields/notes
- Plan step [blocked]: Wait: follow-up after 3 working days (30 Sep) or on replies (Waiting on staff decision on bond condition, landlord reply to email:sandbox-1, and maintenance completion; follow-up ~30 Sep (3 working days from 25 Sep). No chase to contractor: hold agreed, nobody waiting on us from them.)
