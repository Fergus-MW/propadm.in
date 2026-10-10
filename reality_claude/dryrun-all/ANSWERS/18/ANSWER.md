# Case 18: Garden Maintenance Request

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:17:38+00:00

## Decision

**Decision**
- The garden work is reported as done but not verified, so I left the ticket open at status "in progress" and did not resolve or close it.
- The "Completed by supervisor" line is a platform tick. The record has no contractor report, no date, no photos and no tenant confirmation. The invoice attachment is unavailable, so I don't know the amount or scope.
- The contractor never replied to the assignment email or the three reminders.
- The only landlord approval is a platform tick with no amount or scope. Langley told the landlord on 3 Jan that the work was done and would be "invoiced off the rent", and the landlord acknowledged. I treated that as acknowledgement, not approval of a price.
- The tenant phone number given to the contractor differs between the 17 Dec email and the later reminders. I relied on neither.

**Actions**
- **State note:** I added a note to ticket:case recording issues, confirmed facts, claims, conflicts and missing information.
  - The first attempt failed because I used the wrong ticket version (24 instead of 1).
  - I had already marked plan step s1 "done" before that call returned. The retry with version 1 succeeded, so the step's evidence is now accurate, but I ticked it too early.
- **Tenant:** I emailed the tenant (email:sandbox-1) asking whether the overgrowth is cleared, with a request for a photo and a reply by 9 Jan. It contained no costs.
- **Contractor:** I emailed the contractor (email:sandbox-2) asking for the attendance date, work done, photos, and the invoice number, total, VAT basis and scope in the email body. I told them not to do further work without written approval.
- **Simulated delivery:** Both emails are SIMULATED. They were recorded, not delivered.
- **Ticket fields:** I set status "in progress", urgency "routine" and category "other". My first update with category "garden" was rejected because it isn't an allowed value. "Other" is the nearest fit, not a precise classification.
- **Plan steps:** I marked s2 to s4 done. Step s5 stays in progress while I wait.
- **Sleep:** I went to sleep for 10 minutes, waking on the ticket or either email thread.
- **Not done:** I made no ledger entries, sent nothing to the landlord, placed no calls and set no tags.

**Staff involvement**
- No handover so far and no `needs-staff` tag. I judged that nothing needs a staff decision until the invoice contents are known.
- My earlier report said the agency isn't paying a contractor under this cost route. That was wrong. "Invoiced off the rent" could mean the agency pays and deducts from the landlord's rent, and I haven't established which. Staff should decide if the amount turns out to exceed any approval, is disputed, or if anyone proposes charging the tenant.

**Open items**
- Tenant's yes/no confirmation of the outcome.
- Contractor's completion report and invoice details. If they stay silent, a phone call is the next channel, but I have not placed one.
- Once the invoice contents are known, I need to check the amount against what was approved, work out the cost route, and send the landlord the invoice and cost.
- Resolve the ticket only once the tenant has confirmed, or one check has gone unanswered and the contractor's evidence supports completion. The cost route must also be clear and the landlord informed.

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Note on ticket:case | ERROR - {'code': 'conflict', 'message': 'Stale entity version; current version is 1'} |
| 2 | Note on ticket:case | OK |
| 3 | Email to tenant@case.sandbox.invalid: Flat 17, 67 Willowmere Road – garden work: is it sorted? | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 4 | Email to contractor@case.sandbox.invalid: Flat 17, 67 Willowmere Road – garden maintenance: completion report and invoice details needed | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Update ticket:case: category, status, urgency | ERROR - {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"} |
| 6 | Update ticket:case: category, status, urgency | OK |
| 7 | Wait: Awaiting tenant completion confirmation and contractor completion report/invoice details (emails simulated). (wake on ticket:case, email:sandbox-1, email:sandbox-2) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to tenant@case.sandbox.invalid: Flat 17, 67 Willowmere Road – garden work: is it sorted?

```text
Hello Freya,

This is about the overgrown tree and weeds in the garden at Flat 17, 67 Willowmere Road, Alderwick, ZZ7 4ZZ.

Our records show the garden work has been marked as completed. We have not yet had a report from the gardener, so we would like to check with you: has the tree and weed overgrowth now been cleared and tidied? A simple yes or no is fine. If you can, please send a photo of the garden as it is now.

If anything is still outstanding, tell us what is left and we will follow it up. Please reply by Friday 9 January. If the overgrowth comes back or anything becomes unsafe, contact us straight away.

Kind regards,
Maintenance assistant, Northbridge Lettings

(Note: email in this environment is sandboxed and delivery is simulated.)
```

**send_email** to contractor@case.sandbox.invalid: Flat 17, 67 Willowmere Road – garden maintenance: completion report and invoice details needed

```text
Dear Riverside Services,

Re: Garden Maintenance Request, Flat 17, 67 Willowmere Road, Alderwick, ZZ7 4ZZ (overgrown tree and weeds).

We have not received a reply to our earlier emails, but an invoice has been added to our case file and we cannot open the attachment. Please reply in the body of the email with:
1. The date(s) you attended and what was done (tree work, weed clearance, waste removal).
2. Any before/after photos.
3. The invoice number, total amount, whether VAT is included, and the scope it covers.
4. Anything left outstanding or any recommendation for follow-up.

Please do not carry out any further work at this property without our written approval. If you did not attend, please tell us so.

Kind regards,
Maintenance assistant, Northbridge Lettings

(Email in this environment is sandboxed; delivery is simulated.)
```


## What failed

- add_note: {'code': 'conflict', 'message': 'Stale entity version; current version is 1'}
- update_entity: {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"}

## Final state

- Ticket status: in progress, urgency: routine, tags: none
- Plan step [done]: Rebuild state and record in note
- Plan step [done]: Ask tenant to confirm garden work done (yes/no)
- Plan step [done]: Ask contractor for completion report and invoice (contents unavailable)
- Plan step [done]: Update ticket fields/note; staff handover on invoice/cost if needed
- Plan step [in_progress]: Sleep for replies; resolve only if job-completion criteria met (Waiting on tenant yes/no reply (by 9 Jan) and contractor completion report/invoice details. Resolve only when criteria met.)
