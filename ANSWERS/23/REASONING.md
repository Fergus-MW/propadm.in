# Reasoning for case 23

## What the system received

- `index.md`: read, 657 bytes
- `history.md`: read, 10036 bytes
- `attachments/invoice-NBL-CFM-250210-A.pdf`: read, 138150 bytes
- `attachments/invoice-NBL-CFM-250210-B.pdf`: read, 137742 bytes
- 23 history events; latest timestamp 2025-02-12 16:35:00 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, contractor-invoice, landlord-approval, escalation-and-handover, communications, chasing-and-follow-up, triage-maintenance-ticket

## Plan

Goal: 7 Larkspur Fold heating: resolve disputed Copper Finch invoices (A £138 within diagnostic authority; B £372 unauthorised/unevidenced), keep tenant informed, hand disputed invoice to staff, await landlord decision.

- [done] Rebuild state, triage urgency and write ticket fields
  - evidence: ticket:case updated to v2: urgent, heating, triaged, cost_estimate 372, tags needs-staff, invoice-dispute
- [skipped] Record invoice A £138 as expected expense; do not record B
  - note: record_transaction rejected 'Unknown transaction category' for repair/repairs/contractor_invoice/maintenance; valid category list not discoverable from skill or tools. Nothing recorded. Invoice A (£138) to be recorded by staff or after category known; B deliberately not recorded.
- [done] Hand over disputed invoice B to staff
  - evidence: note added to ticket (v3); email:sandbox-1 SIMULATED to maintenance-team
- [done] Email contractor: B on hold, evidence request, no further work authorised
  - evidence: email:sandbox-2 SIMULATED (not delivered)
- [done] Update tenant (no costs), safety reminder, access for possible return visit
  - evidence: email:sandbox-3 SIMULATED (not delivered)
- [in_progress] Wait for landlord decision / contractor evidence; sleep
  - note: Waiting on: landlord reply to 12 Feb 16:35 email (chase by 14 Feb), contractor evidence by 14 Feb, tenant reply, staff decision on invoices.

## Agent messages

1. Now the handover note, staff email, and the other messages.
2. ## Report

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

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `get_skill` {"skill": "contractor-invoice"} -> OK
6. `get_skill` {"skill": "landlord-approval"} -> OK
7. `get_skill` {"skill": "escalation-and-handover"} -> OK
8. `get_skill` {"skill": "communications"} -> OK
9. `get_skill` {"skill": "chasing-and-follow-up"} -> OK
10. `get_skill` {"skill": "triage-maintenance-ticket"} -> OK
11. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
12. `create_plan` {"goal": "7 Larkspur Fold heating: resolve disputed Copper Finch invoices (A £138 within diagnostic authority; B £372 unauthorised/unevidenced), keep tenant informed, hand disputed invoice to staff, await landlord decision.", "steps": [{"id": "state", "title": "Rebuild state, triage urgency and writ -> OK
13. `get_entity` {"id": "company:case-contractor"} -> OK
14. `get_entity` {"id": "person:case-landlord"} -> OK
15. `get_entity` {"id": "person:agency-staff"} -> OK
16. `update_step` {"step_id": "state", "status": "in_progress"} -> OK
17. `update_entity` {"id": "ticket:case", "version": 1, "fields": {"urgency": "urgent", "category": "heating", "status": "triaged", "cost_estimate": 372, "tags": ["needs-staff", "invoice-dispute"]}, "reason": "Case history events 001, 011, 020: intermittent/no radiator heating in February with a child in the home = urg -> OK
18. `update_step` {"status": "done", "step_id": "state", "evidence": "ticket:case updated to v2: urgent, heating, triaged, cost_estimate 372, tags needs-staff, invoice-dispute"} -> OK
19. `update_step` {"status": "in_progress", "step_id": "ledger"} -> OK
20. `record_transaction` {"fields": {"kind": "charge", "category": "repair", "amount_minor": 13800, "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210-A: attendance, diagnosis, actuator inspection and operational test, 5 Feb 2025, £138.00 incl VAT (within landlord's £180  -> ERROR {'code': 'invalid', 'message': 'arguments contains undeclared fields'}
21. `record_transaction` {"fields": {"amount_minor": 13800, "category": "repair", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210-A: attendance, diagnosis, actuator inspection and operational test, 5 Feb 2025, GBP 138.00 incl VAT, within landlord's 180 diagnostic autho -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
22. `get_ledger` {"property": "property:case"} -> OK
23. `get_unallocated` {} -> OK
24. `record_transaction` {"fields": {"amount_minor": 13800, "category": "repairs", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210-A: attendance, diagnosis, actuator inspection and operational test, 5 Feb 2025, GBP 138.00 incl VAT, within landlord's 180 diagnostic auth -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
25. `record_transaction` {"fields": {"amount_minor": 13800, "category": "contractor_invoice", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210-A: attendance, diagnosis, actuator inspection and operational test, 5 Feb 2025, GBP 138.00 incl VAT, within landlord's 180 diag -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
26. `record_transaction` {"fields": {"amount_minor": 13800, "category": "maintenance", "currency": "GBP", "date": "2025-02-10", "description": "Copper Finch Mechanical invoice NBL-CFM-250210-A: diagnosis, 5 Feb 2025, GBP 138.00 incl VAT, within landlord's 180 diagnostic authority. Expected expense only; no payment made.", " -> ERROR {'code': 'invalid', 'message': 'Unknown transaction category'}
27. `update_step` {"note": "record_transaction rejected 'Unknown transaction category' for repair/repairs/contractor_invoice/maintenance; valid category list not discoverable from skill or tools. Nothing recorded. Invoice A (£138) to be recorded by staff or after category known; B deliberately not recorded.", "status -> OK
28. `report_workflow_issue` {"category": "missing_step", "description": "contractor-invoice says to record an expected expense charge but does not list valid transaction categories or field names. record_transaction rejected 'repair', 'repairs', 'contractor_invoice' and 'maintenance' with 'Unknown transaction category', so a w -> OK
29. `update_step` {"status": "in_progress", "step_id": "staff"} -> OK
30. `add_note` {"id": "ticket:case", "note": "STAFF DECISION NEEDED: Copper Finch invoice B (£372) unauthorised and unevidenced; how to treat both invoices.   Urgency: today\nTicket ticket:case, property 7 Larkspur Fold, Orvane Heath, ZZ1 1ZZ. Stage: invoice dispute; heating fault still open (urgent, child in home -> OK
31. `send_email` {"to": ["maintenance-team@agency.sandbox.invalid"], "subject": "STAFF DECISION NEEDED: 7 Larkspur Fold - Copper Finch invoice B £372 unauthorised (today)", "body": "STAFF DECISION NEEDED: Copper Finch invoice B (£372) unauthorised and unevidenced; how to treat both invoices.   Urgency: today\nTicket -> SIMULATED Sandboxed email provider: recorded, not delivered.
32. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "7 Larkspur Fold - invoices NBL-CFM-250210-A and -B: status and evidence needed", "body": "Hi Petra,\n\nThank you for your reply of 12 February about the heating job at 7 Larkspur Fold, Orvane Heath, ZZ1 1ZZ.\n\nWhere we stand on our records:\n- -> SIMULATED Sandboxed email provider: recorded, not delivered.
33. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "7 Larkspur Fold - update on your heating problem", "body": "Hello,\n\nThank you for your updates about the heating at 7 Larkspur Fold. We are sorry it is still inconsistent. We are working with the landlord and the heating contractor to agree the n -> SIMULATED Sandboxed email provider: recorded, not delivered.
34. `update_step` {"evidence": "note added to ticket (v3); email:sandbox-1 SIMULATED to maintenance-team", "status": "done", "step_id": "staff"} -> OK
35. `update_step` {"evidence": "email:sandbox-2 SIMULATED (not delivered)", "status": "done", "step_id": "contractor"} -> OK
36. `update_step` {"evidence": "email:sandbox-3 SIMULATED (not delivered)", "status": "done", "step_id": "tenant"} -> OK
37. `update_step` {"note": "Waiting on: landlord reply to 12 Feb 16:35 email (chase by 14 Feb), contractor evidence by 14 Feb, tenant reply, staff decision on invoices.", "status": "in_progress", "step_id": "wait"} -> OK
38. `sleep` {"reason": "Waiting on landlord decision, contractor evidence (due 14 Feb), tenant reply and staff decision on invoices; nothing further is due yet.", "wake_on": ["ticket:case", "person:case-landlord", "company:case-contractor", "person:case-tenant", "person:agency-staff"], "minutes": 10} -> OK
