---
name: chasing-and-follow-up
description: Use when deciding whether to act now or wait, when someone has gone quiet, when a reminder may be due, or on any wake-up. Gives chase timing per party, channel escalation, and when doing nothing is the right action.
---

# Chasing and follow-up

## Check inbound first
Before any chase, read new emails and calls on the ticket and thread (`get_entity`, `traverse`). Never chase someone who already replied, reported completion or sent the invoice. A send whose email `status` is failed or bounced reached nobody and starts no clock.

## When waiting is right
Wait, sending nothing, when the next step is owned by a named party, their promised or normal time has not passed, no new risk appeared, and nobody is waiting on an answer from us. Examples: tenant promised photos tomorrow; contractor on the way and tenant home; landlord's own contractor booked; part on order with a date; the latest message is just "thanks".
To wait: mark the plan step `blocked` with what it waits for and the follow-up date, then `sleep` with `wake_on` set to the thread, call, ticket or person ids. Sleep is capped at 10 minutes; on each wake-up, if nothing changed and the follow-up date has not arrived, sleep again without messaging anyone. For waits of days use `schedule_invocation` when it is available.
Never send a generic "any update?" just to look busy.

## Timing (working days; emergencies in hours)
| Waiting on | First chase | Then |
| --- | --- | --- |
| Landlord approval | 3 days | Resend about day 6, then call |
| Landlord decision on a quote | 2 to 3 days | Sooner while a decision is live |
| Landlord handling it themselves | 5 to 8 days | About weekly, asking for the expected completion date |
| Contractor booking | 1 day | 3 days, 6 days, then call |
| Contractor report after a visit | 1 to 2 days | Call |
| Contractor away or parts on order | The stated date | Then chase |
| Invoice after completion | 3 to 4 days | Every 3 to 5 days |
| Tenant reply | 4 to 7 days | Call after two unanswered emails |
| Urgent job: landlord | 1 day by email and call | Staff at 2 days |
| Urgent job: contractor | A few hours | Next contractor, within authority |
| Urgent job: tenant | 1 day | Call at 2 days |
| Emergency | Hours | Call, then staff |
Respect what people said ("I'll reply Sunday", "away until the 20th"). If someone is known to be on leave or away, do not send a generic chase; ask once when they are back or arrange cover, and set the follow-up after their return.

## Escalating the channel
Email, then call (tenant-call), then staff (escalation-and-handover). After three ignored automated reminders, call. A self-help case with no reply after a chase gets one last message giving a date after which the ticket closes unless they reply. A landlord silent on a repair that is their duty or a safety matter is escalated, not just chased.

## Chase message
Name the earlier message and date, ask for the one thing needed, give a "by when". Short and polite.
