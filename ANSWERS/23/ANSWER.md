# Case 23: Heating maintenance at 7 Larkspur Fold

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:02:12+00:00

## Decision

## Report

**Decision**
- Invoice B (£372, actuator replacement) is on hold and not accepted. The landlord authorised diagnosis only, up to £180. The £372 estimate was sent after the 5 Feb visit and was never approved. Nothing shows the work was done: the contractor's own 5 Feb report records no remedial work, parts and credit were unconfirmed on 7 Feb, and the tenant doesn't know whether the actuator was replaced. B also overlaps invoice A.
- Invoice A (£138, diagnosis) is within the landlord's authority and matches the diagnostic quote. I did not record it in the ledger (see Open items).
- No payment was made or initiated, and no further work was instructed.
- I set the ticket to urgent, heating, triaged. The heating is still intermittent, with a child in the home, in February. The £372 is held as an unapproved cost estimate only.

**Actions**
- Updated ticket:case to urgent, heating, triaged. Tagged it `needs-staff` and `invoice-dispute`, and added a handover note.
- Emailed staff with the handover note. Staff were not asked to decide the landlord's question.
- Emailed the contractor, Petra Quill. A is with our team for processing, B is on hold, and no further work is authorised. I asked for the following by 14 Feb:
  - whether any actuator work was actually done, and when;
  - job notes, a signed completion record and a parts record;
  - confirmation that B is withdrawn or credited, so diagnosis isn't charged twice;
  - repair options and an itemised price if no repair was done.
- Emailed the tenant. No costs were shared. I told her no return visit date is set yet, gave portable-heater and gas/carbon monoxide/smoke safety advice, and asked for current symptoms, any boiler code, and whether access after 14:00 on weekdays still holds.
- I did not email the landlord again. The property manager's 12 Feb 16:35 email already asks him how to proceed and whether any work is authorised.
- All three emails went through the sandboxed provider and are SIMULATED, not delivered.
- Reported a workflow issue on the contractor-invoice skill. `record_transaction` returned "Unknown transaction category" for "repair", "repairs", "contractor_invoice" and "maintenance", and no list of valid categories is available.

**Staff involvement**
- Staff need to decide how to treat the disputed invoice B, whether invoice A is paid separately, and whether a return visit is approved once the landlord answers. The 14-day payment terms run to about 24 Feb.
- Staff also need to record invoice A (£138) in the ledger, or tell me the valid category.

**Open items**
- Landlord decision on how to proceed, and on any repair or return visit. I'll chase by 14 Feb if there's no reply.
- Contractor evidence, due 14 Feb.
- Tenant reply on symptoms and access.
- Invoice A is not yet in the ledger because of the category failure.
- Plan step "wait" is in progress. I'm sleeping now with the ticket as the wake trigger.

## Escalation to staff

- Tagged ticket:case needs-staff, invoice-dispute
- Handover note on ticket:case
- Emailed agency staff: STAFF DECISION NEEDED: 7 Larkspur Fold - Copper Finch invoice B £372 unauthorised (today)

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Update ticket:case: category, cost_estimate, status, tags, urgency | OK |
| 2 | record_transaction: {"fields": {"kind": "charge", "category": "repair", "amount_minor": 13800, "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invo | ERROR - {'code': 'invalid', 'message': 'arguments contains undeclared fields'} |
| 3 | record_transaction: {"fields": {"amount_minor": 13800, "category": "repair", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210 | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 4 | record_transaction: {"fields": {"amount_minor": 13800, "category": "repairs", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-25021 | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 5 | record_transaction: {"fields": {"amount_minor": 13800, "category": "contractor_invoice", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NB | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 6 | record_transaction: {"fields": {"amount_minor": 13800, "category": "maintenance", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-2 | ERROR - {'code': 'invalid', 'message': 'Unknown transaction category'} |
| 7 | report_workflow_issue: {"category": "missing_step", "description": "contractor-invoice says to record an expected expense charge but does not list valid transaction categories or fiel | OK |
| 8 | Note on ticket:case | OK |
| 9 | Email to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED: 7 Larkspur Fold - Copper Finch invoice B £372 unauthorised (today) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 10 | Email to contractor@case.sandbox.invalid: 7 Larkspur Fold - invoices NBL-CFM-250210-A and -B: status and evidence needed | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 11 | Email to tenant@case.sandbox.invalid: 7 Larkspur Fold - update on your heating problem | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 12 | Wait: Waiting on landlord decision, contractor evidence (due 14 Feb), tenant reply and staff decision on invoices; nothing further is due yet. (wake on ticket:case, person:case-landlord, company:case-contractor, person:case-tenant, person:agency-staff) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED: 7 Larkspur Fold - Copper Finch invoice B £372 unauthorised (today)

```text
STAFF DECISION NEEDED: Copper Finch invoice B (£372) unauthorised and unevidenced; how to treat both invoices.   Urgency: today
Ticket ticket:case, property 7 Larkspur Fold, Orvane Heath, ZZ1 1ZZ. Stage: invoice dispute; heating fault still open (urgent, child in home). Waiting on: landlord Soren Dallow (asked 12 Feb 16:35) and contractor Petra Quill (said 12 Feb she is checking records).
Decision needed: (1) Invoice B £372 (NBL-CFM-250210-B): reject/hold until contractor shows landlord authority and signed completion, or seek landlord approval; (2) whether invoice A £138 (NBL-CFM-250210-A) is paid separately; (3) whether a return visit/repair is approved once the landlord answers. By: before the 14-day payment terms end (about 24 Feb).
Confirmed: landlord authorised diagnosis up to £180 incl VAT only and asked to be consulted before remedial work (events 005, 012); diagnostic quote £138 incl VAT (event 007); visit attended 5 Feb, actuator fault found, no remedial work reported (event 008); £372 estimate sent 5 Feb 14:54, after the visit, requesting written authorisation (event 009); landlord has not approved it (event 012); parts/breakdown/credit unconfirmed 7 Feb (event 016); no payment recorded.
Reported, not confirmed: invoice B says actuator replaced 5 Feb (contractor, events 017/018); tenant does not know whether it was replaced, has seen no contractor since 5 Feb, heating still intermittent (event 020).
Conflicts: invoice B "completed 5 Feb" vs the contractor's own 5 Feb report (no remedial work), the later estimate asking for authorisation and the 7 Feb parts check; B also overlaps A (diagnosis, attendance, testing). Blocks payment of B.
Done so far: ticket set urgent/heating, tagged needs-staff; £372 held as unapproved estimate only. Deliberately not done: no payment, no acceptance of B, no further work instructed. Invoice A £138 NOT recorded in the ledger because record_transaction rejected every category I tried ("Unknown transaction category"); please record it or tell me the valid category (workflow issue reported).
Safety steps given: yes, tenant reminded about safe heater use and to report gas smell/CO alarm/smoke at once. Next check: landlord/contractor reply; I will chase the landlord by 14 Feb.
(Email provider in this run is sandboxed/SIMULATED.)

Maintenance assistant
```

**send_email** to contractor@case.sandbox.invalid: 7 Larkspur Fold - invoices NBL-CFM-250210-A and -B: status and evidence needed

```text
Hi Petra,

Thank you for your reply of 12 February about the heating job at 7 Larkspur Fold, Orvane Heath, ZZ1 1ZZ.

Where we stand on our records:
- Invoice NBL-CFM-250210-A (£138 incl VAT, diagnosis on 5 February) matches the diagnostic visit you quoted and that was authorised. It is with our team for processing.
- Invoice NBL-CFM-250210-B (£372 incl VAT, actuator supply and replacement) is on hold and is not accepted for payment. Our file holds no written landlord authorisation for actuator replacement; your £372 estimate was sent after the 5 February visit and the landlord has not approved it. Its description also overlaps invoice A.
- No further work is authorised at the property until the landlord has decided.

To move this forward, please send in the email body by 14 February:
1. Whether work was actually done on the actuator, and on what date (your 5 February visit update reported none).
2. Job notes, any signed completion record, and the parts record (supplier or part number) if a part was fitted.
3. Confirmation of whether invoice B is withdrawn or re-issued as a credit, so that diagnosis is not charged twice.
4. If no repair was done, the repair options, parts availability and itemised price that the landlord asked about.

The tenant still reports intermittent heating, so we want to resolve this promptly. A member of our team will follow up on the invoice point.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Email provider in this run is sandboxed/SIMULATED.)
```

**send_email** to tenant@case.sandbox.invalid: 7 Larkspur Fold - update on your heating problem

```text
Hello,

Thank you for your updates about the heating at 7 Larkspur Fold. We are sorry it is still inconsistent. We are working with the landlord and the heating contractor to agree the next step, and we will tell you as soon as a return visit is confirmed. We cannot give a date yet.

In the meantime:
- Please let us know if anything has changed: are the radiators and hot water working today, and does the boiler show any symbol or code? If you can, a photo of the display would help.
- If you use a portable heater, please keep it clear of curtains and bedding, never leave it on while you are out or asleep, and do not use extension leads or dryers with it.
- If you ever smell gas, a carbon monoxide alarm sounds, or you see smoke, sparks or a leak near electrics, leave the property and call 999 or the gas emergency line 0800 111 999, then tell us.
- If a visit is arranged, we have your access as after 14:00 on weekdays. Please tell us if that has changed.

If anything gets worse or unsafe, contact us straight away.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Email provider in this run is sandboxed/SIMULATED.)
```


## What failed

- record_transaction: {'code': 'invalid', 'message': 'arguments contains undeclared fields'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}
- record_transaction: {'code': 'invalid', 'message': 'Unknown transaction category'}

## Final state

- Ticket status: triaged, urgency: urgent, tags: needs-staff, invoice-dispute
- Plan step [done]: Rebuild state, triage urgency and write ticket fields
- Plan step [skipped]: Record invoice A £138 as expected expense; do not record B (record_transaction rejected 'Unknown transaction category' for repair/repairs/contractor_invoice/maintenance; valid category list not discoverable from skill or tools. Nothing recorded. Invoice A (£138) to be recorded by staff or after category known; B deliberately not recorded.)
- Plan step [done]: Hand over disputed invoice B to staff
- Plan step [done]: Email contractor: B on hold, evidence request, no further work authorised
- Plan step [done]: Update tenant (no costs), safety reminder, access for possible return visit
- Plan step [in_progress]: Wait for landlord decision / contractor evidence; sleep (Waiting on: landlord reply to 12 Feb 16:35 email (chase by 14 Feb), contractor evidence by 14 Feb, tenant reply, staff decision on invoices.)
