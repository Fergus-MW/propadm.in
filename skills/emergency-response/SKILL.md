---
name: emergency-response
description: Use immediately when any message mentions gas smell, a CO alarm sounding, smoke or fire, water through a ceiling or near lights or sockets, sparking or burning, a ceiling coming down, someone hurt, or an entry door that cannot be secured. Confirms real danger, gives safety steps, arranges a make-safe, tells the landlord and alerts staff without waiting for approval.
---

# Emergency response

## Confirm before sending anyone to emergency services
Confirmed only on a clear sign: someone smells gas, sees smoke or fire, a CO alarm is sounding, water is in lights or sockets, a ceiling is coming down, someone is hurt, the property cannot be secured. If the tenant says they smell gas or see fire, give the steps straight away. Never discourage anyone from calling 999.
Not confirmed (a mention, a scheduled gas check, a letter about a leak, "smells a bit funny"): do not tell them to call emergency services. Give the always-safe steps, `place_call` the tenant with the urgency questions (anyone in danger, gas or burning smell, water near lights or sockets, getting worse, who is home, only toilet or heating), treat it as urgent and keep in touch. No answer: email the same questions with 0800 111 999 and 999, call again in about 10 minutes, then alert staff. Never assume it is fine.

## Confirmed: do all of these now
1. Safety steps to the occupant by `place_call` (objective: give safety steps, check everyone is safe) and by email:
   - Gas or CO alarm: open doors and windows, no switches, flames or electrical devices, turn gas off at the meter if safe, leave, call the National Gas Emergency Service on 0800 111 999. 999 if anyone is unwell or there is fire.
   - Fire or smoke: get out and call 999.
   - Water leak: turn off the stopcock (often under the kitchen sink). If water is near lights or sockets, switch off at the consumer unit only if it is dry to reach; otherwise keep away. Leak from the flat above: also contact that flat or the block manager.
   - Electrical danger: do not touch; switch off at the consumer unit if safe; 999 if fire.
   - Cannot secure the property or break-in: 999 if a crime is in progress, otherwise 101.
   - Structural: keep away from the area; leave if it looks unsafe.
2. Make safe only, without waiting for approval: `find_providers` with the trade and `urgency=emergency` for the property, pick an emergency-capable provider (Gas Safe for gas; choose-provider rules), and instruct the make-safe by `place_call` or `send_email`. If nobody accepts within about 15 minutes, try the next; nobody within an hour means staff take over.
3. Alert staff now (escalation-and-handover, urgency "right now") and tell the landlord by email what happened and what is being done.
4. Set the ticket `urgency=emergency` with notes of every step. The full repair afterwards follows landlord-approval as normal.

Never say it is safe, never diagnose, never blame anyone, never claim a contractor is coming until they confirm.
