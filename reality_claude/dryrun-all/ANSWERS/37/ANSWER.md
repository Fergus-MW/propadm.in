# Case 37: Shower Repair Request

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:21:01+00:00

## Decision

**Decision**
- The shower hose repair is reported done by the contractor (Beacon Utilities, email of 6 April) but not verified, so I have not resolved or closed the ticket. The platform's "completed by supervisor" line is only a tick, and the tenant hasn't confirmed the leak has stopped.
- The contractor's attachment (attachment-91) was unreadable. I know nothing about cost, parts or scope, so I haven't stated or recorded any cost.
- The agency's 10:45 note to the landlord (event 023) named the wrong address, Flat 8, 68 Willowmere Road, Bellmere. The property of record is Flat 14, 44 Lantern Quay, Alderwick. I treated that as an error and sent a correction.
- The only approval on record is the landlord's 27 March email, "Please get the shower hose replaced". It carries no price.

**Actions**
- Created a plan and added a state note to ticket:case. I then set the ticket status to "in progress", with a resolution line saying tenant confirmation and invoice details are pending.
- Sent the tenant a yes/no check on whether the shower is working and no longer leaking (email:sandbox-1). It mentions no costs.
- Sent the landlord a correction with the right address. It says the contractor reports the hose was replaced and that we haven't yet seen the invoice or cost (email:sandbox-2).
- Asked the contractor to put the visit date, parts, cause of the leak, photos, total cost with VAT basis and invoice addressee in the email body (email:sandbox-3).
- All three emails went through the sandboxed provider and are SIMULATED, so none were actually delivered.
- Put the run to sleep for 10 minutes, set to wake on the ticket or on replies to the tenant and contractor emails.

**Staff involvement**
- None needed so far.
- Staff would need to decide if the cost exceeds what the landlord approved, if the contractor reports further work, or if the tenant says the shower still leaks.

**Open items**
- Waiting for the tenant's yes/no on whether the shower works and no longer leaks.
- Waiting for the contractor's cost, parts and photo details.
- The cost route is not on record: the landlord may pay the contractor directly, or the agency may pay and deduct from rent. I'll confirm it once the invoice details arrive.
- Once the tenant confirms, or the check goes unanswered and the contractor's evidence supports completion, I'll set the ticket to resolved. I'll then send the landlord the cost and invoice, and tell the tenant what was done and how to report a recurrence, without any cost.
- If the tenant doesn't reply after reasonable attempts, I'll record the job as reported done and close it with a recurrence route.

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Note on ticket:case | OK |
| 2 | Email to tenant@case.sandbox.invalid: Flat 14, 44 Lantern Quay – is your shower now fixed? | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 3 | Email to landlord@case.sandbox.invalid: Correction: Flat 14, 44 Lantern Quay – shower hose replaced | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 4 | Email to contractor@case.sandbox.invalid: Flat 14, 44 Lantern Quay – shower hose: details needed in email body | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Update ticket:case: resolution, status | OK |
| 6 | Wait: Awaiting tenant yes/no on shower and contractor cost/parts details (emails SIMULATED) (wake on ticket:case, email:sandbox-1, email:sandbox-3) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**send_email** to tenant@case.sandbox.invalid: Flat 14, 44 Lantern Quay – is your shower now fixed?

```text
Hello Eliza,

Beacon Utilities reports that the snapped shower hose at Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8ZZ was replaced. Is the shower now working and no longer leaking? A simple yes or no is fine, and if anything is still wrong please tell us what you can see (photos help).

If it starts leaking again later, or anything becomes unsafe, contact us straight away.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Note: email is sandboxed in this run and reported as SIMULATED.)
```

**send_email** to landlord@case.sandbox.invalid: Correction: Flat 14, 44 Lantern Quay – shower hose replaced

```text
Hello Freya,

Please disregard the address in our earlier note today: it named another property in error. The correct property is Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8ZZ.

For that property, the contractor (Beacon Utilities) reports that the snapped shower hose was replaced, as you asked on 27 March. We have asked the tenant to confirm the leak has stopped, and will let you know. The contractor's attachment could not be read on our side, so we have not yet seen the invoice or cost; we have asked for the details and will pass them on once received.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Email is sandboxed in this run and reported as SIMULATED.)
```

**send_email** to contractor@case.sandbox.invalid: Flat 14, 44 Lantern Quay – shower hose: details needed in email body

```text
Dear Beacon Utilities,

Thank you for your report that the snapped shower hose at Flat 14, 44 Lantern Quay, Alderwick, ZZ9 8ZZ was replaced. We could not open your attachment, so please reply with the key details in the body of the email: date of the visit, what was replaced (parts), the cause of the leak, any photos, the total cost with VAT basis, and who the invoice is addressed to. Please also tell us if any further work is needed.

Kind regards,
Maintenance assistant, Northbridge Lettings
(Email is sandboxed in this run and reported as SIMULATED.)
```


## What failed

Nothing failed.

## Final state

- Ticket status: in progress, urgency: unset, tags: none
- Plan step [done]: Record case state and note conflicts on ticket
- Plan step [done]: Send tenant completion check
- Plan step [done]: Send landlord correction with correct address
- Plan step [done]: Ask contractor for cost, parts, photos in email body
- Plan step [done]: Update ticket fields/notes
- Plan step [in_progress]: Sleep awaiting tenant and contractor replies; then resolve if criteria met (Waiting on tenant yes/no and contractor cost/parts details; then resolve and send landlord cost/invoice.)
