# Case 14: Front Door Repair Request

Run: **done** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T13:16:19+00:00

## Decision

## Decision
The ticket is closed as resolved with a recurrence route. No email, call or contractor booking was needed.

- **Landlord's message:** The latest message ("Thank you Ava", 21:45 on 7 June) is only a thank-you. Nobody is waiting on us, so I sent no reply.
- **Workaround:** The tenant told Ava on 7 June that the landlord's workaround worked. She uses the key to retract the latch, then closes the door. She will report if it comes back.
- **Danger check:** The door closes with the workaround, so there is no emergency and no unsecured entry door.
- **Landlord's plan:** The landlord intends to get a contractor to look at the door next month. That is the landlord's own job, with no quote, approval or spend on record, so I did not dispatch anyone.

## Actions
- I updated `ticket:case`. Status is now resolved, urgency routine, and category is access/security. The intake had wrongly filed it under appliances. The resolution text records the workaround, that no contractor attended, the recurrence route and that there was no cost.
- I added a note to `property:case` recording the recurring door fault, the workaround, the contractor's remark that the frame wobbles and slamming could break the glass, and the landlord's plan for next month.
- I sent no outbound messages, so there is no simulated delivery to report.

## Staff involvement
None needed. There is no money, complaint, legal or safety decision to hand over.

## Open items
- If the tenant reports the door sticking again, or says it no longer locks or latches, reopen the ticket and triage it afresh. A door that cannot be secured is an emergency.
- The landlord's "next month" contractor visit is theirs to arrange. If the landlord later asks the agency to arrange it, that needs landlord approval first. A follow-up of about a week after the landlord's visit date would be reasonable.
- The tenant's confirmation came from the agent's note of a phone call, not from a message of her own.

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Update ticket:case: category, resolution, status, urgency | ERROR - {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"} |
| 2 | Update ticket:case: category, resolution, status, urgency | OK |
| 3 | Note on property:case | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## What failed

- update_entity: {'code': 'invalid', 'message': "category must be one of ['plumbing', 'heating', 'electrical', 'damp/mould', 'structural', 'appliances', 'pests', 'access/security', 'other']"}

## Final state

- Ticket status: resolved, urgency: routine, tags: none
- Plan step [done]: Record state and resolution on ticket
- Plan step [done]: Add note on property re recurrent fault
- Plan step [done]: Final report
