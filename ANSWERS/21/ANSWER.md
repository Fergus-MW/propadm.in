# Case 21: Hot-water service report

Run: **sleeping** · Path: **live** · Model: claude-sonnet-5-5 · Generated 2026-10-10T16:01:29+00:00

## Decision

**Decision**
- I did not resolve or close the ticket. The landlord says his plumber fixed the hot water on 14 May, but that is only a text relayed by him. He gave no description of the work, report or invoice.
- The tenant's last word (13 May) was still no hot water. The tenant has not answered my 15 May voicemail and email. I recorded both accounts and relied on neither.
- The job stays with the landlord's own plumber, so I booked no agency contractor.
- I treated it as urgent, category heating rather than electrical. Hot water has been out since 6 May. The record shows no gas smell, alarm or other emergency sign.
- The letterbox fault the tenant mentioned on 13 May is a separate routine item.

**Actions**
- I updated the ticket (urgency urgent, category heating, status triaged, tags landlord-managed and completion-unverified). I added a note recording the landlord/tenant conflict, the actions below and the next steps.
- I placed a call to the tenant (call:sandbox-1). It was SIMULATED: no call was made and no transcript will arrive.
- I emailed the tenant (email:sandbox-2), SIMULATED and not delivered. It asks for a yes/no on hot water and boiler power, whether anyone visited, and what access suits (including the birds). It also asks what is wrong with the letterbox and whether the front door still locks. It gives gas-smell and emergency advice and asks for a reply by Mon 19 May.
- I emailed the landlord (email:sandbox-3), SIMULATED and not delivered. It asks by Tue 20 May for the plumber's name and visit date, what the fault was and what was done, and any electrical checks. If the boiler was worked on, it asks for Gas Safe details, and for any report or invoice. It repeats the offer of an agency contractor and says we would come back to him before booking anything.
- I did not create a separate letterbox ticket. I only have a note on this ticket and the tenant is being asked for details.
- I put the run to sleep, waking on any reply or in 10 minutes.

**Staff involvement**
- None yet. I handed nothing over and sent no staff email, because nothing so far needs a staff decision.
- Staff would be needed if the tenant says there is still no hot water and the landlord does not accept an agency contractor. They would also be needed for a safety issue, a complaint or legal threat, or any tenant charge.

**Open items**
- Neither email nor the call reached anyone, because the providers are sandboxed. The tenant's confirmation is still outstanding (reply requested by 19 May), and so is the landlord's evidence of the plumber's visit (by 20 May).
- If the tenant stays silent, I will call again. I would only resolve, with a recurrence route, after a further unanswered check and if the landlord's evidence supports completion.
- If the tenant says there is still no hot water, I will tell the landlord at once and arrange an agency diagnosis visit with his agreement.
- The letterbox needs its own ticket once the tenant's details arrive.
- The case file shows "Requires decision". I took that to be whether to close the ticket and left it open.

## Escalation to staff

None. The agent handled the case without staff.

## Actions taken

| # | Action | Result |
| --- | --- | --- |
| 1 | Update ticket:case: category, status, tags, urgency | OK |
| 2 | Call person:case-tenant: Find out whether hot water (taps and shower) and the boiler's power are working now at 17 Wrenfold Quay, after the landlord's plumber reportedly attended on 14 May, and what access would suit if not. | SIMULATED - Sandboxed voice provider: no call was placed and no transcript will arrive. |
| 3 | Email to tenant@case.sandbox.invalid: 17 Wrenfold Quay – is your hot water working now? (quick yes/no please) | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 4 | Email to landlord@case.sandbox.invalid: 17 Wrenfold Quay – hot water: details of the plumber's visit needed | SIMULATED - Sandboxed email provider: recorded, not delivered. |
| 5 | Note on ticket:case | OK |
| 6 | Wait: Waiting for tenant confirmation (reply by 19 May) and landlord's plumber details (by 20 May); nothing else to do now. (wake on ticket:case, person:case-tenant, person:case-landlord, email:sandbox-2, email:sandbox-3) | OK |

SIMULATED means the sandboxed provider recorded the message; nothing was delivered.

## Messages

**place_call** to person:case-tenant

```text
Objective: Find out whether hot water (taps and shower) and the boiler's power are working now at 17 Wrenfold Quay, after the landlord's plumber reportedly attended on 14 May, and what access would suit if not.

Brief: You are an AI assistant calling for Northbridge Lettings' maintenance team. Confirm you are speaking to the tenant of 17 Wrenfold Quay (the resident who reported the hot-water fault) before sharing details. Background you may share: the tenant reported no hot water since 6 May; the landlord says his own plumber attended on 14 May and fixed it, but we have not had confirmation and want to check with them. Ask: (1) Is hot water now working at both the kitchen/bathroom taps and the shower? (2) Does the boiler have power / is it running? Did anyone actually visit the property, and if so when? (3) If still not working: when is someone usually home, is it OK for an engineer to come when they are not in, and the household member who does not speak English - any best arrangement for access; any pets/birds to be aware of. (4) Any smell of gas or burning, any alarm sounding, or anything unsafe near the boiler? If so tell them to leave the property, call the gas emergency line 0800 111 999 and 999 if in danger, and say staff will follow up. (5) Separately, they mentioned the letterbox not working on 13 May: ask briefly what is wrong (broken flap, stuck, can't close, door still locks securely?). Do not discuss costs, liability, charges, compensation, or promise dates or contractors. Do not share anyone else's details. If the tenant is distressed, hostile, or mentions a complaint or legal action, stay calm and offer a call back from a member of staff. Do not say the fix is confirmed; the landlord's report is only a report.
```

**send_email** to tenant@case.sandbox.invalid: 17 Wrenfold Quay – is your hot water working now? (quick yes/no please)

```text
Hello,

Following my email and voicemail of 15 May about the hot water at 17 Wrenfold Quay: the landlord has told us his plumber attended on 14 May and fixed it. We have not yet had that confirmed, and your last message to us said it was still not working, so we would like to hear it from you.

Could you please reply with a quick answer to each of these?
1. Is hot water now working at the taps and the shower? (yes / no)
2. Does the boiler have power again? Did anyone actually visit, and if so when?
3. If it is still not working: when is someone usually home, and is it OK for an engineer to come in if you are out? Please also tell us about the birds so the engineer can take care.
4. Separately, you mentioned on 13 May that the letterbox is not working. What is wrong with it (for example broken flap, stuck, will not close), and does your front door still lock securely? We will log this as its own job.

If you ever smell gas or burning, or an alarm sounds, leave the property and call the gas emergency line on 0800 111 999 (or 999 if anyone is in danger), then let us know straight away.

We would like to hear from you by end of day Monday 19 May. A phone call attempt was also queued, but our phone system is a test setup, so please do not rely on it having reached you.

Kind regards,
Maintenance assistant, Northbridge Lettings
```

**send_email** to landlord@case.sandbox.invalid: 17 Wrenfold Quay – hot water: details of the plumber's visit needed

```text
Dear Ravi,

Thank you for your update on 15 May that your plumber attended on 14 May and fixed the hot water at 17 Wrenfold Quay. We have not yet had the tenant's confirmation: their last message to us (13 May) said there was still no hot water, and we are asking them again today.

So we can close this properly, could you send us by Tuesday 20 May:
- the plumber's name/company and the date of the visit;
- what the fault was and what was done (the tenant reported the boiler had no power), including any electrical checks;
- if any work was done on the boiler itself, the engineer's Gas Safe registration number, and a copy of any report or invoice.

The tenant also reported a faulty letterbox on 13 May. We are getting details and will pass them on separately.

If the tenant tells us the hot water is still not working, we will let you know immediately. As you offered on 12 May, we can arrange an agency contractor to attend; we would come back to you before anything is booked.

Kind regards,
Maintenance assistant, Northbridge Lettings
```


## What failed

Nothing failed.

## Final state

- Ticket status: triaged, urgency: urgent, tags: landlord-managed, completion-unverified
- Plan step [done]: Record state and triage on ticket
- Plan step [blocked]: Call tenant to verify hot water and ask about letterbox and safety (Call was simulated; tenant answer outstanding. Chased by email with reply-by Mon 19 May.)
- Plan step [done]: Email landlord for plumber's work details
- Plan step [blocked]: Act on tenant outcome (resolve, or dispatch/escalate) (Waiting on tenant reply (due 19 May) and landlord visit details (due 20 May). Do not resolve until tenant confirms or a second unanswered check plus landlord evidence supports completion.)
- Plan step [done]: Letterbox: record as separate item and ask for details
