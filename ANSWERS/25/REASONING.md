# Reasoning for case 25

## What the system received

- `index.md`: read, 639 bytes
- `history.md`: read, 7770 bytes
- `attachments/corrected-plumbing-invoice.pdf`: read, 133867 bytes
- 22 history events; latest timestamp 2025-09-15 11:11:18 UTC

## Skills consulted

graph-conventions, planning-and-sleeping, job-completion, contractor-invoice, escalation-and-handover, landlord-approval, communications

## Plan

Goal: Handle kitchen tap case: review corrected invoice NBL-025-INV-15 for 18 Thistlewick Row, verify completion with tenant, inform landlord, chase missing invoice details, handle drawer request.

- [done] Rebuild state, load skills, read parties
  - evidence: Read ticket:case, tenant/landlord/contractor entities, property:case, skills graph-conventions, job-completion, contractor-invoice, landlord-approval, escalation, communications.
- [done] Record state note on ticket and update ticket fields
  - note: STATE. Issues: (1) drip/tap - contractor invoice says new mono kitchen sink tap supplied+installed; reported completion, tenant NOT confirmed; (2) cloudy water - no finding/test, unresolved; (3) top kitchen drawer brackets snapped - tenant request 5 Sep, no landlord approval, not addressed; (4) invoice NBL-025-INV-15 - postcode now matches ZZ1 1ZZ, but no amount/VAT/date of visit/photos shown; (5) boiler remark on call 15 Sep - not part of this job, Tessa checking with engineer. Stage: completion check + invoice validation. Blocking: contractor (amount, visit date, findings), tenant (confirmat
  - evidence: ticket updated to v3: status in progress, category plumbing, urgency routine; note added.
- [done] Ask contractor for invoice amount/VAT, visit date, findings, cause of cloudiness, key return
  - evidence: email:sandbox-1 simulated
- [done] Ask tenant to confirm drip stopped/cloudy water, and about drawer (no costs)
  - evidence: email:sandbox-2 simulated
- [done] Email landlord: work reported done, invoice status, drawer request yes/no
  - evidence: email:sandbox-3 simulated
- [in_progress] Sleep awaiting replies
  - note: Waiting on contractor (price/VAT/visit date/key), tenant confirmation, landlord drawer answer.

## Agent messages

1. Now update the ticket fields and try adding a note.
2. **Decision**
The corrected invoice fixes the postcode but is not enough to act on. It matches ZZ1 1ZZ and describes "supply and install one new mono kitchen sink tap". It shows no amount, VAT, visit date or photos.
- I did not record an expense or settle anything, because there is no price.
- The ticket is not resolved. The tenant hasn't confirmed the drip has stopped, and the cloudy water has no finding. The ticket is set to "in progress".
- The landlord's 5 Aug approval covers "proceeding with the maintenance works" with no price or limit. It does not cover the drawer repair.
- This is routine work, so I did not hand it to staff.

**Actions**
- I updated the ticket to category plumbing, urgency routine and status in progress, and added a note with the review state.
- I emailed the contractor (email:sandbox-1) asking for:
  - the total with VAT shown separately;
  - the visit date and findings;
  - photos;
  - confirmation the spare key was returned;
  - any extra work listed separately.
- I told the contractor not to do any other work without written go-ahead.
- I emailed the tenant (email:sandbox-2) asking a yes/no on whether the drip has stopped and whether the water is still cloudy. I did not mention any costs. I also said the drawer is being checked with the landlord.
- I emailed the landlord (email:sandbox-3) with the invoice status, saying the figures will follow. I asked a separate yes/no on getting a quote for the drawer repair.
- All three emails are SIMULATED; nothing was actually delivered.

**Staff involvement**
None needed now. Tessa is separately checking the boiler remark from the 15 Sep call. It is not documented as part of this job, and I did not act on it.

**Open items**
- Waiting on the contractor for the price, VAT, visit date, findings, photos and key return. Once the price arrives I will compare it with the approval, record the expense and pass the invoice to the landlord.
- Waiting on the tenant to confirm the drip is gone and say whether the cloudy water persists. The ticket can be resolved only after that, plus the cost route being known and the landlord informed.
- Waiting on the landlord's yes or no on the drawer. Nothing is instructed until then, and any quote would need their approval.
- The 10 Sep visit and the spare-key return are unconfirmed.
- I have not yet called the sleep tool. It is the next step, with the ticket in wake_on.

## Tool trace

1. `get_plan` {} -> OK
2. `get_skill` {"skill": "graph-conventions"} -> OK
3. `get_skill` {"skill": "planning-and-sleeping"} -> OK
4. `get_entity` {"id": "ticket:case"} -> OK
5. `traverse` {"entity_id": "ticket:case", "depth": 2} -> OK
6. `get_skill` {"skill": "job-completion"} -> OK
7. `get_skill` {"skill": "contractor-invoice"} -> OK
8. `get_skill` {"skill": "escalation-and-handover"} -> OK
9. `get_skill` {"skill": "landlord-approval"} -> OK
10. `create_plan` {"goal": "Handle kitchen tap case: review corrected invoice NBL-025-INV-15 for 18 Thistlewick Row, verify completion with tenant, inform landlord, chase missing invoice details, handle drawer request.", "steps": [{"id": "s1", "title": "Rebuild state, load skills, read parties", "detail": "Read ticke -> OK
11. `get_skill` {"skill": "communications"} -> OK
12. `get_entity` {"id": "person:case-landlord"} -> OK
13. `get_entity` {"id": "company:case-contractor"} -> OK
14. `get_property` {"property": "property:case"} -> OK
15. `update_step` {"step_id": "s1", "status": "done", "evidence": "Read ticket:case, tenant/landlord/contractor entities, property:case, skills graph-conventions, job-completion, contractor-invoice, landlord-approval, escalation, communications."} -> OK
16. `update_step` {"step_id": "s2", "status": "in_progress", "note": "STATE. Issues: (1) drip/tap - contractor invoice says new mono kitchen sink tap supplied+installed; reported completion, tenant NOT confirmed; (2) cloudy water - no finding/test, unresolved; (3) top kitchen drawer brackets snapped - tenant request  -> OK
17. `update_entity` {"id": "ticket:case", "version": 1, "fields": {"status": "in progress", "category": "plumbing", "urgency": "routine"}, "reason": "Corrected invoice NBL-025-INV-15 (event 022) reports new mono kitchen tap supplied and installed; completion unverified by tenant, so not resolved. Routine plumbing per o -> OK
18. `add_note` {"id": "ticket:case", "note": "Agent review 15 Sep 2025: Corrected invoice NBL-025-INV-15 (event 022) shows postcode ZZ1 1ZZ matching the property; scope 'supply and install one new mono kitchen sink tap'. It shows NO amount, VAT, visit date or photos, so no expense recorded and no cost can be passe -> OK
19. `update_step` {"evidence": "ticket updated to v3: status in progress, category plumbing, urgency routine; note added.", "status": "done", "step_id": "s2"} -> OK
20. `send_email` {"to": ["contractor@case.sandbox.invalid"], "subject": "18 Thistlewick Row, ZZ1 1ZZ – corrected invoice NBL-025-INV-15: details needed", "body": "Hello,\n\nThank you for the corrected invoice NBL-025-INV-15 for 18 Thistlewick Row, Fenmere, ZZ1 1ZZ. The postcode now matches our record.\n\nThe copy we -> SIMULATED Sandboxed email provider: recorded, not delivered.
21. `send_email` {"to": ["tenant@case.sandbox.invalid"], "subject": "18 Thistlewick Row – is your kitchen tap now fixed?", "body": "Hello Nia,\n\nOur plumbing contractor reports that a new kitchen sink tap has been fitted at 18 Thistlewick Row. Could you let us know with a quick yes or no:\n1. Has the dripping stopp -> SIMULATED Sandboxed email provider: recorded, not delivered.
22. `send_email` {"to": ["landlord@case.sandbox.invalid"], "subject": "18 Thistlewick Row – kitchen tap reported replaced; drawer repair question", "body": "Dear Mr Bell,\n\nUpdate on the kitchen tap at 18 Thistlewick Row, Fenmere, ZZ1 1ZZ (the works you approved by email on 5 August):\n\n- Bracken & Vale Plumbing h -> SIMULATED Sandboxed email provider: recorded, not delivered.
23. `update_step` {"evidence": "email:sandbox-1 simulated", "status": "done", "step_id": "s3"} -> OK
24. `update_step` {"evidence": "email:sandbox-2 simulated", "status": "done", "step_id": "s4"} -> OK
25. `update_step` {"evidence": "email:sandbox-3 simulated", "status": "done", "step_id": "s5"} -> OK
26. `update_step` {"note": "Waiting on contractor (price/VAT/visit date/key), tenant confirmation, landlord drawer answer.", "status": "in_progress", "step_id": "s6"} -> OK
