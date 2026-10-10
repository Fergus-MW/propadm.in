# Reasoning for case 3

## What the system received

- `index.md`: read, 711 bytes
- `history.md`: read, 8587 bytes
- `attachments/tap-works-invoice.pdf`: read, 135072 bytes
- 23 history events; latest timestamp 2025-09-14 09:20:00 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, triage-maintenance-ticket, communications, escalation-and-handover, landlord-approval

## Plan

Goal: Ticket:case - Flat 4, 8-12 Juniper Mews: verify tap works reported done, resolve invoice property mismatch, chase vent/damp findings, update landlord (incl. insurance/history asks), tenant completion check.

- [done] Rebuild state, review property/provider/landlord records
  - note: STATE: Issues: (1) kitchen tap + bathroom hot tap - contractor reports fixed per invoice NBL-003-INV-14, unverified by tenant; (2) bathroom vent rain ingress - no findings recorded; (3) bedroom ceiling/wall damp - not reported on; (4) landlord's insurance/history asks - not done. Approval: landlord 'Yes please proceed' 4 Sep (inspection/attendance only, no amount). Conflicts: invoice addressed to Flat 4, 28 Larkspur Quay, Brindlewick vs property of record 8-12 Juniper Mews; Gareth 11 Sep 'job was done today' vs visit 12 Sep; invoice has no amount/VAT/date of works.
  - evidence: Read ticket, property, landlord, contractor, staff entities. No quotes, no amounts, no insurance/history review on record.
- [done] Triage danger and set ticket fields
  - evidence: Ticket updated to version 2: urgency urgent, category plumbing, status in progress, tags set. No confirmed emergency indicator in the record.
- [done] Contractor: query invoice (wrong property, no amount/VAT) and request visit report on vent/bedroom damp
  - evidence: email:sandbox-1 (SIMULATED) to contractor
- [done] Tenant: completion check for taps + vent/damp safety questions
  - evidence: email:sandbox-2 (SIMULATED) to tenant
- [done] Landlord: update on taps reported done, vent/damp outstanding, insurance/history status; no invoice figures yet
  - evidence: email:sandbox-3 (SIMULATED) to landlord
- [in_progress] Record notes; sleep awaiting replies
  - note: Note added (ticket v3). Waiting on contractor reply (corrected invoice, findings), tenant yes/no, landlord insurer/history details.

## Agent messages

1. Now the three emails.
2. Mark steps and sleep.
3. **Decision**
- The case stays open and in progress. The taps are only reported done, and nothing is confirmed.
  - The contractor says he fitted a new kitchen mixer tap and a new insert and head on the bathroom hot tap. The tenant hasn't confirmed either tap works yet.
  - The invoice (NBL-003-INV-14) names Flat 4, 28 Larkspur Quay, Brindlewick, not Flat 4, 8-12 Juniper Mews. It also shows no price, VAT or work date. I recorded no expense and passed on no figures.
  - Gareth said on 11 Sep "job was done today", then that he was booked for the next day. He attended on 12 Sep, so the date of the work is unclear.
  - The vent rain leak and the bedroom damp have no findings. The landlord's approval of 4 Sep covers attendance only, so no further work is authorised.
  - The landlord's insurance and roof-leak history requests are still not done.
- I set urgency to urgent, not routine, because the vent may be an electric fan. Nothing in the record shows a confirmed emergency.

**Actions**
- Ticket: urgency urgent, category plumbing, status in progress, tags and a state note added (ticket now at version 3).
- Contractor email (email:sandbox-1):
  - It asks him to confirm the property and send a corrected invoice with total and VAT.
  - It asks him to confirm the work date(s).
  - It asks for findings, photos, the likely cause and any quote on the vent and bedroom damp.
  - It tells him not to start further work until the landlord approves a quote.
- Tenant email (email:sandbox-2): a yes/no check that both taps now work. It also asks whether the vent is an electric fan or light fitting and whether water has reached it, plus whether the bedroom ceiling is sagging or wet. It asks for a fresh photo of the damp patches. No costs are mentioned.
- Landlord email (email:sandbox-3):
  - Taps are reported done, the invoice is under query and the vent and damp findings are outstanding.
  - It is honest that the insurance and history checks are not done, and asks for insurer or block-manager details and earlier leak records.
- All three emails are SIMULATED and were not delivered.

**Staff involvement**
- No handover for now. The invoice mismatch goes to the contractor first, which is routine. Staff would be needed if the contractor can't explain the wrong address, or if the corrected invoice is materially higher than expected.

**Open items**
- Waiting on the contractor for the corrected invoice, work date and vent/damp findings. If there is no reply by about the next working day, I'll phone him.
- Waiting on the tenant's yes/no on the taps and the answers on the vent and bedroom. If the tenant reports water reaching electrics or a sagging ceiling, treat it as an emergency.
- Waiting on the landlord for insurer and leak-history details. The roof may sit under a building policy, so the freeholder or block manager may also need contacting.
- Any further vent or damp work needs a written quote and fresh landlord approval.
- After the tenant confirms the taps and a corrected invoice arrives, forward the invoice to the landlord.
- Don't resolve or close the ticket while the vent and damp are unresolved.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
6. `get_skill` {"skill": "job-completion"} -> OK
7. `get_skill` {"skill": "contractor-invoice"} -> OK
8. `get_skill` {"skill": "triage-maintenance-ticket"} -> OK
9. `get_skill` {"skill": "communications"} -> OK
10. `get_skill` {"skill": "escalation-and-handover"} -> OK
11. `get_skill` {"skill": "landlord-approval"} -> OK
12. `create_plan` {"goal": "Ticket:case - Flat 4, 8-12 Juniper Mews: verify tap works reported done, resolve invoice property mismatch, chase vent/damp findings, update landlord (incl. insurance/history asks), tenant completion check.", "steps": [{"id": "s1", "title": "Rebuild state, review property/provider/landlord -> OK
13. `get_property` {"property": "property:case"} -> OK
14. `get_entity` {"id": "company:case-contractor"} -> OK
15. `get_entity` {"id": "person:case-landlord"} -> OK
16. `get_entity` {"id": "person:agency-staff"} -> OK
17. `update_step` {"step_id": "s1", "status": "done", "evidence": "Read ticket, property, landlord, contractor, staff entities. No quotes, no amounts, no insurance/history review on record.", "note": "STATE: Issues: (1) kitchen tap + bathroom hot tap - contractor reports fixed per invoice NBL-003-INV-14, unverified b -> OK
18. `update_step` {"step_id": "s2", "status": "in_progress"} -> OK
19. `update_entity` {"id": "ticket:case", "version": 1, "fields": {"status": "in progress", "urgency": "urgent", "category": "plumbing", "tags": ["partial-completion", "invoice-query", "vent-damp-outstanding", "insurance-history-outstanding"]}, "reason": "Taps reported fixed by contractor invoice (event 022) but unveri -> OK
20. `update_step` {"status": "done", "step_id": "s2", "evidence": "Ticket updated to version 2: urgency urgent, category plumbing, status in progress, tags set. No confirmed emergency indicator in the record."} -> OK
21. `update_step` {"status": "in_progress", "step_id": "s3"} -> OK
22. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "Flat 4, 8-12 Juniper Mews, Vellumford ZZ1 1ZZ - invoice NBL-003-INV-14 query and visit report", "body": "Hi Gareth,\n\nThanks for invoice NBL-003-INV-14 for the tap works at Flat 4, 8-12 Juniper Mews, Vellumford, ZZ1 1ZZ. Before we can process  -> SIMULATED Sandboxed email provider: recorded, not delivered.
23. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "Flat 4, 8-12 Juniper Mews - are the taps working now? Also a quick check on the vent and bedroom", "body": "Hello,\n\nThe plumber reports that on his visit he installed a new kitchen mixer tap and fitted a new insert and head to the bathroom basin  -> SIMULATED Sandboxed email provider: recorded, not delivered.
24. `send_email` {"body": "Dear Owen,\n\nUpdate on Flat 4, 8-12 Juniper Mews, Vellumford, ZZ1 1ZZ (your approval of 4 September to proceed).\n\n- Taps: the plumber (Copper Finch Plumbing) attended on Friday 12 September and has invoiced for a new kitchen mixer tap and a new insert and head on the bathroom basin hot  -> SIMULATED Sandboxed email provider: recorded, not delivered.
25. `add_note` {"id": "ticket:case", "note": "Agent 2025-09-14: State. Taps: contractor reports done via invoice NBL-003-INV-14 (event 022); tenant confirmation requested (email:sandbox-2), so NOT verified/closed. Invoice conflicts: addressed to Flat 4, 28 Larkspur Quay, Brindlewick vs property of record 8-12 Juni -> OK
26. `update_step` {"evidence": "email:sandbox-1 (SIMULATED) to contractor", "status": "done", "step_id": "s3"} -> OK
27. `update_step` {"evidence": "email:sandbox-2 (SIMULATED) to tenant", "status": "done", "step_id": "s4"} -> OK
28. `update_step` {"evidence": "email:sandbox-3 (SIMULATED) to landlord", "status": "done", "step_id": "s5"} -> OK
29. `update_step` {"note": "Note added (ticket v3). Waiting on contractor reply (corrected invoice, findings), tenant yes/no, landlord insurer/history details.", "status": "in_progress", "step_id": "s6"} -> OK
30. `sleep` {"reason": "Waiting for contractor reply (corrected invoice, vent/damp findings), tenant tap confirmation and safety answers, landlord insurer/history details. All emails simulated.", "wake_on": ["ticket:case", "email:sandbox-1", "email:sandbox-2", "email:sandbox-3"], "minutes": 10} -> OK
