---
name: tenant-call
description: Use before placing any phone call to a tenant, landlord or contractor with place_call, and when a call ends or an inbound call transcript arrives. Covers when to call rather than email, writing the call objective and brief, urgency callbacks, identity, and what to record afterwards.
---

# Calls

`place_call(entity_id, objective, brief)` hands the conversation to the voice agent. You write what it must achieve and what it may say; the transcript and outcome come back to this session when the call ends. Then `sleep` with the call id in `wake_on`.

## When to call
- Emergencies and anything possibly urgent where nobody has spoken to the tenant yet (urgency callback).
- After two unanswered emails, or three ignored automated reminders to a contractor.
- Same-day scheduling, missed appointments, a contractor who cannot reach the tenant.
- A distressed or confused person.
Calls between 8am and 8pm unless it is an emergency. Money approvals still need an email record.

## Objective and brief
- One objective, phrased as the outcome you need ("confirm whether the tenant can be home Thursday 10am to 1pm").
- The brief gives: who the agency is and that this is an AI assistant; the property's street and the job; facts the voice agent may share; the exact questions to ask; what it must not do (no cost, liability, compensation or unconfirmed dates; no other person's details; no promises on the landlord's behalf); what to do if the person is distressed, hostile or mentions a complaint or legal action (stay calm, offer a staff call back).
- Urgency callback questions: is anyone in danger, any smell of gas or burning, is water near lights or sockets, is it getting worse, who is at home, is this your only toilet or heating. A clear danger sign means emergency-response.
- Confirm identity before sharing case details: the person's role for this ticket, matched on the number or email on record.

## When the call ends
- Read the call's `status`, `summary`, `outcome` and transcript. The transcript is a report; it mishears names, dates and numbers. Confirm anything agreed by email (`send_email` or `reply_email`).
- `voicemail` or `no_answer`: follow up in writing; for urgent matters call again in about 10 minutes, then alert staff. Never assume it is fine.
- Record what was agreed on the ticket and person (availability, access, preferred contact) with the call as evidence.
- A caller who cannot be matched to the case after asking: share nothing and ask for name, address and phone. Still check for danger first.
