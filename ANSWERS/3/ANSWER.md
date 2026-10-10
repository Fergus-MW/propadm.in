# Case 3: Bathroom and kitchen maintenance

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T15:59:18+00:00

## Decision

**Decision**
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

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Update ticket:case: category, status, tags, urgency | OK |
| 2 | Email to contractor@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews, Vellumford ZZ1 1ZZ - invoice NBL-003-INV-14 query and visit report | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 3 | Email to tenant@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews - are the taps working now? Also a quick check on the vent and bedroom | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 4 | Email to landlord@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews - taps reported done; vent/damp findings, insurance and history outstanding | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Note on ticket:case | OK |
| 6 | Wait: Waiting for contractor reply (corrected invoice, vent/damp findings), tenant tap confirmation and safety answers, landlord insurer/history details. All emails simulated. (wake on ticket:case, email:sandbox-1, email:sandbox-2, email:sandbox-3) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to contractor@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews, Vellumford ZZ1 1ZZ - invoice NBL-003-INV-14 query and visit report

```text
Hi Gareth,

Thanks for invoice NBL-003-INV-14 for the tap works at Flat 4, 8-12 Juniper Mews, Vellumford, ZZ1 1ZZ. Before we can process it we need the following by reply:

1. Property: the invoice is addressed to "Flat 4, 28 Larkspur Quay, Brindlewick". Our job is Flat 4, 8-12 Juniper Mews, Vellumford. Please confirm the work was done at Juniper Mews and send a corrected invoice. If any of it relates to a different property, please tell us which.
2. Amount: the invoice shows no price. Please send the total, with labour, parts and VAT shown (or "VAT not stated").
3. Date: your email of 11 September said "job was done today", then that you were booked for tomorrow, and you attended on 12 September. Please confirm the date(s) the work was done.
4. Vent and bedroom damp: the original job also covered rainwater coming through the bathroom vent and damp patches on the ceiling and wall of the smaller bedroom. Your invoice covers only the two taps. Please tell us what you found on those two issues, with photos, the likely cause (for example roof, vent ducting or condensation), and any quotation for further work. Please do not start any further work until the landlord has approved a quote.

Thank you,
Maintenance assistant, Northbridge Lettings (note: this email system is sandboxed and delivery is SIMULATED)
```

**send_email** to tenant@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews - are the taps working now? Also a quick check on the vent and bedroom

```text
Hello,

The plumber reports that on his visit he installed a new kitchen mixer tap and fitted a new insert and head to the bathroom basin hot tap at Flat 4, 8-12 Juniper Mews. Could you let us know with a quick yes or no:

1. Has the kitchen tap stopped dripping?
2. Does the bathroom hot tap now shut off fully, with no drip, and do hot and cold both work?

On the other two things you reported, the plumber has not yet told us what he found about the rain coming through the bathroom vent or the damp in the smaller bedroom, so we are asking him for that. In the meantime, please tell us:
3. Is the bathroom vent an electric extractor fan or light fitting, and has water reached it or any light, socket or switch? If so, please keep clear of it, switch it off at the wall or fuse board if you can safely do so, and tell us straight away.
4. Is the bedroom ceiling sagging, flaking or wet to the touch, and has it got worse since you reported it? A fresh photo of the damp patches would help.

If anything gets worse or unsafe, contact us straight away.

Thank you,
Maintenance assistant, Northbridge Lettings (note: this email system is sandboxed and delivery is SIMULATED)
```

**send_email** to landlord@case.sandbox.invalid: Flat 4, 8-12 Juniper Mews - taps reported done; vent/damp findings, insurance and history outstanding

```text
Dear Owen,

Update on Flat 4, 8-12 Juniper Mews, Vellumford, ZZ1 1ZZ (your approval of 4 September to proceed).

- Taps: the plumber (Copper Finch Plumbing) attended on Friday 12 September and has invoiced for a new kitchen mixer tap and a new insert and head on the bathroom basin hot tap. This is the contractor's report; we have asked the tenant to confirm both taps are now working. The invoice does not yet show a price and names a different address (Larkspur Quay), so we have asked for a corrected invoice with the total and VAT. We will send it to you once corrected.
- Vent and bedroom damp: the plumber has not yet reported on the rain coming through the bathroom vent or the damp on the smaller bedroom's ceiling and wall. We have asked for his findings, photos and any quotation. Nothing further will start until you have approved a quote. Your approval so far covers attendance only.
- Insurance and history: you asked us to check what building insurance may cover and to review the flat's history of roof leaks. We have not completed either yet and have no insurance details or earlier leak records on file for this flat. Could you send the insurer and policy details (or the block manager or freeholder contact if the roof is covered by the building policy), and any dates or reports of the earlier leaks? Insurers usually need the damage reported promptly and may want to see repair findings first, so we will pass on the contractor's report as soon as we have it.

Thank you,
Maintenance assistant, Northbridge Lettings (note: this email system is sandboxed and delivery is SIMULATED)
```


## What failed

Nothing failed.

## Final state

- Ticket status: in progress, urgency: urgent, tags: partial-completion, invoice-query, vent-damp-outstanding, insurance-history-outstanding
- Plan step [done]: Rebuild state, review property/provider/landlord records (STATE: Issues: (1) kitchen tap + bathroom hot tap - contractor reports fixed per invoice NBL-003-INV-14, unverified by tenant; (2) bathroom vent rain ingress - no findings recorded; (3) bedroom ceiling/wall damp - not reported on; (4) landlord's insurance/history asks - not done. Approval: landlord 'Yes please proceed' 4 Sep (inspection/attendance only, no amount). Conflicts: invoice addressed to Flat 4, 28 Larkspur Quay, Brindlewick vs property of record 8-12 Juniper Mews; Gareth 11 Sep 'job was done today' vs visit 12 Sep; invoice has no amount/VAT/date of works.)
- Plan step [done]: Triage danger and set ticket fields
- Plan step [done]: Contractor: query invoice (wrong property, no amount/VAT) and request visit report on vent/bedroom damp
- Plan step [done]: Tenant: completion check for taps + vent/damp safety questions
- Plan step [done]: Landlord: update on taps reported done, vent/damp outstanding, insurance/history status; no invoice figures yet
- Plan step [in_progress]: Record notes; sleep awaiting replies (Note added (ticket v3). Waiting on contractor reply (corrected invoice, findings), tenant yes/no, landlord insurer/history details.)
