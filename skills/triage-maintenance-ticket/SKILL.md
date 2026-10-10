---
name: triage-maintenance-ticket
description: Triage every new repair or maintenance report and any new symptom on an open ticket. Checks for danger first, sets urgency and category, decides who is responsible and which route the job takes (tenant self-help, landlord approval, direct dispatch, landlord's own contractor), and asks only for what is missing.
---

# Triage a maintenance ticket

## 1. Danger first
Read every message on the ticket, including old ones and anything mentioned in passing. Gas smell, CO alarm sounding, smoke or fire, water through a ceiling or near electrics, sparking or burning, a ceiling coming down, someone hurt, an entry door or ground-floor window that cannot be secured: get_skill `emergency-response` now and follow it before anything else.
A contained drip, a running cistern, a leaking shower hose or a stiff lock that still locks is not an emergency.

## 2. Urgency
- emergency: the list above. Make safe within hours.
- urgent (1 to 3 days): no heating or hot water, the only toilet unusable, fridge not cooling, a lock that works but is failing, a missing or faulty smoke or CO alarm, any fault that puts a baby, elderly, pregnant, disabled or ill occupant at risk.
- routine: everything else.
Signals that raise urgency, never lower it: several messages in a row, "urgent", "help", "worse", "spreading", capitals, late-night contact, a vulnerable occupant. If unsure between two levels, pick the higher. If urgency is even slightly possible and nobody has spoken to the tenant, get_skill `tenant-call` and call them.
The intake classification is a guess (doors filed as appliances happen). Re-classify from the tenant's own words. Set `urgency`, `category`, `status=triaged` on the ticket with a reason.

## 3. Who is responsible
- Landlord: structure and exterior, water, gas, electricity, sanitation, heating and hot water installations, appliances supplied with the property, smoke and CO alarms.
- Tenant: minor upkeep, blockages caused by use (hair, grease, wipes), bulbs and batteries, garden upkeep where the tenancy says so, damage they caused, lost keys.
- Cause unclear: ask neutral questions (when did it start, was it like this at move-in). Never accuse. Charging a tenant is a person's decision (escalation-and-handover).
- Communal areas: landlord or block manager. Check warranties first: a recent repair by the same contractor or an appliance under warranty goes back to them.

## 4. Route
| Situation | Route |
| --- | --- |
| Likely user-fixable (slow drain, dishwasher door or filter, tripped RCD once, boiler pressure, radiator bleed, alarm battery, appliance settings) | Email safe self-help steps with a note that a call-out may be charged if no fault is found. Follow up in a few days; dispatch if still broken. Never ask them to open panels or touch gas parts. |
| "Complete landlord approval step first", or no landlord authority on record | get_skill `landlord-approval`. Acknowledge the tenant. Do not dispatch. |
| "Approve selection of provider and category", or the landlord pre-agreed this call-out | get_skill `book-contractor` for a diagnosis visit and tell the landlord. Quoted repairs still need approval. |
| Landlord says they will sort it, use their own contractor or do it themselves | Landlord owns it. Tell the tenant, chase timing and completion (chasing-and-follow-up), never dispatch a duplicate. |
| Landlord offers a workaround or defers | Ask the tenant if it is safe and usable now. If yes, relay and agree a review date, or close with a recurrence route if it works. Escalate only if unsafe or unusable, or the landlord refuses a repair that is their duty. |
| Vacant property, checkout works | Quote scoped from the checkout report, then landlord-approval. Clean after other works only when the record shows other works. |
| Same fault already open on this property | Add to that ticket and keep every reporter updated. |
| Non-repair topic in the same message (rent, deposit, neighbours) | Track separately; acknowledge and route at normal priority. Money trouble, eviction, abuse, legal threats, discrimination, formal complaints: escalation-and-handover. |

## 5. Ask only for what is missing, in one message
Exact location; a photo or short video of anything visible, saying exactly what to photograph ("a close-up of the pipe under the sink", "the boiler's model label"); make, model and error code for appliances; since when; access (usual availability, OK to enter without them, pets, alarm, parking). Never hold up an emergency for photos. Record answers on the ticket and person.

## 6. Repair notes
- Appliances: confirm it is the landlord's; first visit diagnoses, parts mean a quote and approval; repair or replace is the landlord's call; gas appliances need a Gas Safe engineer.
- Doors, locks, keys: can it lock now? Check agency spares before replacing keys; state how many keys and who gets each; confirm keys physically received.
- Plumbing: slow-filling cistern or dead tap often an isolation or inlet valve; confirm hot and cold both work after repair.
- Heating: annual gas safety check is the landlord's duty; a missing certificate is an escalation.
- Damp and mould: ventilation advice plus a landlord inspection; health complaints make it urgent; never blame lifestyle without an inspection.
- Gardens and communal: nesting birds and seasons delay work; specialist waste removal raises the price and needs re-approval.

Then `create_plan` with the route's steps and follow planning-and-sleeping.
