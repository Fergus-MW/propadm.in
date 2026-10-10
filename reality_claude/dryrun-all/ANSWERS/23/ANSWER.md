# Case 23: Balcony Door Lock Repair

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:18:54+00:00

## Decision

**Decision**
- I did not close the case or resolve the ticket. The platform shows it closed, but that rests on status lines, not evidence.
- The only support for completion is the contractor's one-line email saying the job is done and an invoice was sent. I could not see an invoice, scope, cost, visit date or how access was gained.
- The tenant has not confirmed the door locks. The "Keys return confirmed" line is a platform tick with no detail.
- A balcony door that won't lock is a security concern, so the ticket stays open until the tenant confirms.

**Actions**
- I read the case history and the job-completion, communications, emergency-response and graph-conventions skills. I created a plan for the case.
- I emailed the tenant asking for a yes/no on whether the balcony door now locks. It included a security note (101, or 999 if a crime is in progress). This is `email:sandbox-1`, SIMULATED, not delivered.
- I emailed Juniper Surveying asking for the visit date, access, what was done, parts, photos, total cost with VAT basis, the invoice, key whereabouts and any revisit. This is `email:sandbox-2`, SIMULATED, not delivered.
- I added a note to the ticket recording the unverified completion, the missing invoice and the name conflict (Theo Ingram vs Freya Langley). I relied on neither name. I set ticket status to "in progress".
- I recorded no financial entry and made no charge, because I have not seen the invoice contents.
- I did not email the landlord, because I have no cost or scope to report yet. That plan step is blocked.
- I set a 10-minute sleep, woken early by replies on the ticket, the two emails, the tenant or the contractor.

**Staff involvement**
- None needed yet.
- Staff will need to decide if the tenant is ever to be charged. They will also need to step in if the contractor's report doesn't add up or the cost exceeds anything agreed. The only approval on record is the landlord's OK to send someone, with no price.

**Open items**
- Tenant confirmation that the door locks. If there is no reply, I will repeat the check and then call.
- The contractor's invoice and details, and the cost route (landlord pays directly, or the agency pays and deducts from rent).
- Which keys were taken or issued, and where they are now.
- Telling the landlord the job is reported done, with what was wrong, what was done, photos, cost and invoice.
- Resolving the ticket only once the tenant confirms (or a check goes unanswered), the cost route is known, the landlord is informed and the keys are confirmed.

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Email to tenant@case.sandbox.invalid: Flat 20, 110 Meadow Row – is the balcony door lock now working? | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 2 | Email to contractor@case.sandbox.invalid: Flat 20, 110 Meadow Row – balcony door lock: completion details and invoice needed | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 3 | Note on ticket:case | OK |
| 4 | Update ticket:case: status | OK |
| 5 | Wait: Waiting for tenant's yes/no on the lock and the contractor's invoice and key details. (wake on ticket:case, email:sandbox-1, email:sandbox-2, person:case-tenant, company:case-contractor) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to tenant@case.sandbox.invalid: Flat 20, 110 Meadow Row – is the balcony door lock now working?

```text
Hello,

Regarding Flat 20, 110 Meadow Row, Northbridge, ZZ2 5ZZ: our contractor, Juniper Surveying, reports that the repair to the lock on the balcony glass door has been completed.

Could you please reply with a simple yes or no: does the balcony door now lock and unlock properly with the key?

If it still will not lock, please tell us straight away so we can arrange a follow-up. If you cannot secure the door and are worried about security, let us know at once. Call 101 if you need to report a concern, or 999 if a crime is in progress. If anything else goes wrong with the lock later, just reply to this email or contact us.

Kind regards,
Maintenance assistant (AI), Northbridge Lettings
```

**send_email** to contractor@case.sandbox.invalid: Flat 20, 110 Meadow Row – balcony door lock: completion details and invoice needed

```text
Hello Juniper Surveying,

Thank you for your message saying the balcony door lock job at Flat 20, 110 Meadow Row, Northbridge, ZZ2 5ZZ is done and an invoice was sent yesterday. We cannot see an invoice on our record for this job, so please could you reply with the details below:

1. The date of the visit and who attended, and how you gained access (we had no record of you reaching the tenant).
2. What the fault was, what you did, and any parts fitted.
3. Photos of the completed work if you have them.
4. The total cost with VAT basis, and the invoice attached again (please also put the key details in the email body in case the attachment cannot be read).
5. Whether any keys were taken, issued or left, and where they are now. This includes any new keys cut for the lock.
6. Whether any further work or a revisit is needed.

Kind regards,
Maintenance assistant (AI), Northbridge Lettings
```


## What failed

Nothing failed.
- Run error: Session could not reach the MCP gateway

## Final state

- Ticket status: in progress, urgency: unset, tags: none
- Plan step [done]: Record case state and conflicts
- Plan step [done]: Ask tenant to confirm door locks (completion check)
- Plan step [done]: Ask contractor for work done, parts, cost, photos, invoice, keys, date
- Plan step [blocked]: Inform landlord job reported done once details known (no closing yet) (Waiting for contractor's invoice/cost/scope so the landlord gets what was done, cost and invoice (job-completion). Not informed yet.)
- Plan step [done]: Update ticket status/notes; do not resolve until criteria met
- Plan step [pending]: Sleep for replies
