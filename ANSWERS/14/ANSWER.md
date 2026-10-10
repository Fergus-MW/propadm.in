# Case 14: Heating service request at 7 Mallowmere Walk

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:01:04+00:00

## Decision

**Decision**
- I treated the heating failure at 7 Mallowmere Walk as urgent, category heating. Leah Venn has a mobility impairment, her living room was 10°C at 16:25, and she has no safe heater. She reported no gas smell, leak or CO alarm, so I did not treat it as an emergency.
- I asked Brackenridge Heat Services to book the 15 Jan 09:00–11:00 cancellation slot for a diagnostic visit. It is a fixed £168 including VAT, which sits inside the landlord's standing £250 urgent-repair authority (his email of 12:47). The slot had to be booked by 17:30.
- I booked on Leah's own earlier words (12:14) that she can admit a contractor on 15 Jan with 30 minutes' notice and a direct call.
- The booking is not confirmed. Brackenridge has not replied, so I did not set `scheduled_visit_at` or move the ticket to scheduled.
- I did not commit to any heater delivery, transport or accommodation. The £250 authority excludes them and the duty file shows no separate limit, so that decision went to staff.

**Actions**
- **Ticket:** I set it to urgent, heating, triaged. I recorded the access instructions (30 minutes' notice, call from outside, extra time to answer the door, niece cannot give access, no key held, no medical details). I tagged it `needs-staff` and `staff-1h` and added the handover note.
- **Calls:** I placed one call to Leah (`call:sandbox-1`) and one to Brackenridge (`call:sandbox-4`). Both were SIMULATED: no call was placed and no transcript will arrive. So Leah has not confirmed the 09:00–11:00 window, and Brackenridge has not confirmed anything.
- **Emails:** All four were SIMULATED and not delivered.
  - Brackenridge (`email:sandbox-2`): booking request for diagnostic only, with no repair or parts without a written quote and approval. It gave the access terms and Leah's recorded number.
  - Leah (`email:sandbox-3`): the slot is being held, please confirm it, keep not using the hot heater, and the team will follow up on interim help. It promised nothing and mentioned no costs.
  - Staff (`email:sandbox-5`): the handover note.
  - Landlord (`email:sandbox-6`): the £168 diagnostic is being used under his urgent authority, any further work comes back to him first, and interim arrangements are to be discussed.
- **Plan:** The state, interim handover and informing steps are done. The booking and tenant-confirmation steps are blocked, waiting on Brackenridge and Leah. The follow-up step is pending.
- **Sleep:** I set a 10-minute sleep with wake triggers on the ticket, the emails and the calls.

**Staff involvement**
- Staff need to decide within the hour, as the office was about to close, whether to fund and arrange any of these for tonight:
  - delivery of a safe heater;
  - step-free transport to Leah's niece's home;
  - accommodation.
- The handover email was simulated, so someone should check the team has actually seen it. Priya Noll had offered to contact the landlord again and check approved heater suppliers.
- If Brackenridge's confirmation has not arrived by 17:30, staff should phone them directly, because my calls did not reach anyone.

**Open items**
- Brackenridge's confirmation that the 15 Jan 09:00–11:00 slot is booked.
- Leah's confirmation of the 09:00–11:00 window, and whether her niece's entrance is step-free.
- The staff decision on interim heating, transport or accommodation.
- Once both confirmations are in: set `scheduled_visit_at` and status to scheduled, and remind both sides on the morning of 15 Jan.
- After the visit: any repair or parts need a written quote and landlord approval, and the incident total must stay within £250 or go back to the landlord for consent.

## Escalation to staff

- Tagged ticket:case needs-staff, staff-1h
- Handover note on ticket:case
- Emailed agency staff: STAFF DECISION NEEDED (within 1 hour): interim heating for vulnerable tenant, 7 Mallowmere Walk

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Update ticket:case: access_instructions, category, status, urgency | OK |
| 2 | Call person:case-tenant: Confirm whether Leah can admit a heating engineer at 7 Mallowmere Walk on Wednesday 15 January between 09:00 and 11:00, with the engineer phoning her directly on arrival and giving at least 30 minutes' notice. Answer needed within about 10 minutes. | SIMULATED - Sandboxed voice provider: no call was placed and no transcript will arrive. |
| 3 | Email to contractor@case.sandbox.invalid: BOOKING: diagnostic visit, 7 Mallowmere Walk, Larkfen ZZ1 1ZZ - Wed 15 Jan 09:00-11:00 | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 4 | Email to tenant@case.sandbox.invalid: 7 Mallowmere Walk - heating engineer, Wed 15 Jan 09:00-11:00: please confirm | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Call company:case-contractor: Get Brackenridge to confirm the 15 Jan 09:00-11:00 diagnostic slot is booked/held before the 17:30 deadline. | SIMULATED - Sandboxed voice provider: no call was placed and no transcript will arrive. |
| 6 | Update ticket:case: tags | OK |
| 7 | Note on ticket:case | OK |
| 8 | Email to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED (within 1 hour): interim heating for vulnerable tenant, 7 Mallowmere Walk | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 9 | Email to landlord@case.sandbox.invalid: 7 Mallowmere Walk - heating diagnostic booked for 15 Jan (£168 within your urgent authority) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 10 | Wait: Waiting for Brackenridge booking confirmation (deadline 17:30), tenant confirmation of the 09:00-11:00 window, and staff decision on interim heating. (wake on ticket:case, email:sandbox-2, email:sandbox-3, email:sandbox-5, email:sandbox-6, call:sandbox-1, call:sandbox-4) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**place_call** to person:case-tenant

```text
Objective: Confirm whether Leah can admit a heating engineer at 7 Mallowmere Walk on Wednesday 15 January between 09:00 and 11:00, with the engineer phoning her directly on arrival and giving at least 30 minutes' notice. Answer needed within about 10 minutes.

Brief: You are the AI maintenance assistant for Northbridge Lettings (the letting agency), calling the tenant Leah Venn about the heating fault at 7 Mallowmere Walk. Confirm you are speaking to Leah (the tenant) before sharing anything. Share: a heating contractor has a cancellation appointment for Wednesday 15 January, 09:00-11:00, for a diagnostic visit only; it can only be held if confirmed within the next few minutes. Ask: (1) Can you be at home and let the engineer in during 09:00-11:00 on 15 January? (2) Is it OK for the engineer to phone you directly on this number when they are about 30 minutes away and again when outside, so you have time to come to the door? (3) Is this the best number? Also ask whether her niece's entrance is step-free and whether she plans to stay there tonight (only record the answer; do not promise transport, heaters or any arrangement - the office team is still looking at that and will follow up). Remind her not to use the plug-in heater that gets hot. Do NOT mention any costs, who pays, medical details, or promise anything about interim heating, transport or accommodation. Do not confirm the appointment as booked; say the office will confirm by message once the contractor confirms. If she is distressed, hostile, mentions a complaint or legal action, stay calm and offer a call back from staff. If she reports a gas smell, fumes, a CO alarm, smoke or someone unwell, tell her to call 0800 111 999 (gas) or 999 and end the call.
```

**send_email** to contractor@case.sandbox.invalid: BOOKING: diagnostic visit, 7 Mallowmere Walk, Larkfen ZZ1 1ZZ - Wed 15 Jan 09:00-11:00

```text
Hi Daniel,

Thank you for the cancellation slot. Please book and hold Wednesday 15 January 2025, 09:00-11:00, for a heating diagnostic at 7 Mallowmere Walk, Larkfen, ZZ1 1ZZ.

Issue (tenant's words): radiators cold, heating controller unresponsive, boiler display blank; hot water still available. No gas smell or visible leak reported. Living room 10°C at 16:25 today.

Approved scope: diagnostic call-out only, fixed £168 including VAT, as you quoted. The landlord's authority for this incident is limited, so please do not carry out any repair or order parts: send findings and a written quote (scope, price, VAT basis) and we will seek approval first.

Access: the tenant, Leah Venn (+44 2079 460101), will let you in. She needs extra time to answer the door, so please phone her at least 30 minutes before you arrive and call again from outside on arrival rather than knocking unannounced. Nobody else can give access, and we hold no key. The tenant has been asked to confirm the 09:00-11:00 window directly and we will tell you straight away if that changes. Please also call her yourself on the number above to confirm it.

Please reply to confirm the booking, and on completion send the cause found, photos, and your invoice.

Kind regards,
Maintenance assistant, Northbridge Lettings (this is an automated assistant; email is SIMULATED in this environment)
```

**send_email** to tenant@case.sandbox.invalid: 7 Mallowmere Walk - heating engineer, Wed 15 Jan 09:00-11:00: please confirm

```text
Hello Leah,

Thank you for your updates, and sorry you are so cold. We have asked Brackenridge Heat Services to hold an earlier appointment for a heating diagnosis on Wednesday 15 January between 09:00 and 11:00 (instead of 17 January).

Please reply as soon as you can to confirm you can be at home in that window. The engineer has been asked to phone you at least 30 minutes before arriving and again from outside, so you have time to come to the door. Nobody else will be asked to give access. If that window does not work, tell us straight away.

For tonight, please keep not using the plug-in heater that gets hot. A member of our team is looking at what help can be arranged with warmth or staying with your niece, and will contact you about that. We cannot promise anything yet, and we will not ask you to carry a heater. Let us know if you find out whether your niece's entrance is step-free. If you feel unwell, or anything gets worse or unsafe, contact us straight away; call 999 in an emergency.

Kind regards,
Maintenance assistant, Northbridge Lettings (automated assistant; email is SIMULATED in this environment)
```

**place_call** to company:case-contractor

```text
Objective: Get Brackenridge to confirm the 15 Jan 09:00-11:00 diagnostic slot is booked/held before the 17:30 deadline.

Brief: You are the AI maintenance assistant for Northbridge Lettings, calling Daniel Hart at Brackenridge Heat Services. Say: please book and hold the cancellation slot Wednesday 15 January 09:00-11:00 for a diagnostic-only visit at 7 Mallowmere Walk, Larkfen, ZZ1 1ZZ, at the fixed £168 including VAT he quoted. No repair or parts without a written quote and approval first. Access: tenant Leah Venn on +44 2079 460101; she needs extra time to answer the door, so phone at least 30 minutes before arriving and again from outside; nobody else can give access; no key held. We have asked her to confirm the window and will tell him straight away if it changes. A confirmation email has been sent. Ask him to confirm the booking is held. Do not share medical details, other people's details, or agree any other price or scope.
```

**send_email** to maintenance-team@agency.sandbox.invalid: STAFF DECISION NEEDED (within 1 hour): interim heating for vulnerable tenant, 7 Mallowmere Walk

```text
STAFF DECISION NEEDED: interim warmth for vulnerable tenant tonight (heater delivery / transport to niece's home / accommodation) - no spending authority on record.   Urgency: within 1 hour (office closing)

Ticket ticket:case, property 7 Mallowmere Walk, Larkfen ZZ1 1ZZ. Stage: diagnostic slot requested for Wed 15 Jan 09:00-11:00 (booking email sent to Brackenridge, SIMULATED; contractor confirmation not yet received; deadline 17:30). Waiting on: Brackenridge, tenant's confirmation of window, staff.

Decision needed: whether the agency/landlord funds and arranges (a) a safe heater delivered, (b) step-free transport to the niece's home, or (c) accommodation, for tonight. The £250 repair authority excludes these (event 007); duty file has no separate limit (event 017). The landlord (Owen Pike) is travelling. Priya offered to contact him and check approved heater suppliers (event 017) - please do that now.

Confirmed: living room 10°C at 16:25; tenant has a mobility impairment and needs extra time to reach the door; suspect plug-in heater not in use; no gas smell or leak; £168 diagnostic is within the landlord's £250 urgent authority (event 014); tenant can admit a contractor on 15 Jan with 30 min notice and a direct call; her niece cannot give access.
Reported, not confirmed: niece's spare room may be available tonight; step-free entrance unknown.
Done: ticket urgent/heating; booking email to contractor and message to tenant (SIMULATED); tenant told a team member will follow up on interim help, nothing promised. Phone calls to tenant (call:sandbox-1) and contractor (call:sandbox-4) were SIMULATED - nobody was actually reached.
Not done: any heater/transport/accommodation spend; any repair or parts beyond the diagnostic; telling the tenant any costs.
Safety steps given: keep not using the hot heater; 999 if unwell/emergency. Next check: contractor confirmation before 17:30, then tenant reply.
```

**send_email** to landlord@case.sandbox.invalid: 7 Mallowmere Walk - heating diagnostic booked for 15 Jan (£168 within your urgent authority)

```text
Dear Mr Pike,

Update on the heating failure at 7 Mallowmere Walk, Larkfen. Thank you for confirming on 14 Jan that the standing £250 urgent-repair authority applies. Under it we have asked Brackenridge Heat Services to hold a diagnostic visit on Wed 15 January, 09:00-11:00. The call-out is a fixed £168 including VAT, diagnostic only. The contractor has not yet confirmed the booking. Any repair or parts will come back to you as a written quote first, and the incident total (£250) is not to be exceeded without your consent.

The tenant reports the living room was 10°C at 16:25 and has a mobility impairment, so we are treating this as urgent. Temporary heaters, transport and accommodation fall outside the repair authority. Our office team will contact you about interim arrangements; if you have a view, please reply. If you would prefer your own contractor, let us know.

Kind regards,
Maintenance assistant, Northbridge Lettings (automated assistant; email is SIMULATED in this environment)
```


## What failed

Nothing failed.

## Final state

- Ticket status: triaged, urgency: urgent, tags: needs-staff, staff-1h
- Plan step [done]: Rebuild state, triage, set ticket urgent/heating
- Plan step [blocked]: Call tenant to confirm 15 Jan 09:00-11:00 access, 30-min notice + direct call (Call call:sandbox-1 was SIMULATED: no call placed, no transcript will arrive. Tenant's own words (event 013) already say she can admit a contractor on 15 Jan with 30 min notice + direct call. Will book on that basis subject to her confirming the 09:00-11:00 window by message.)
- Plan step [blocked]: Book slot with Brackenridge (Daniel Hart) before 17:30 with work order, access, no medical details (Booking email email:sandbox-2 sent (SIMULATED) and call:sandbox-4 (SIMULATED, no call placed). Awaiting Brackenridge confirmation; scheduled_visit_at not set until confirmed.)
- Plan step [done]: Hand over interim heating/transport/accommodation decision to staff (no authority on record)
- Plan step [done]: Tell landlord and tenant; update ticket/notes
- Plan step [pending]: Sleep/wake for confirmations; reminders for 15 Jan
