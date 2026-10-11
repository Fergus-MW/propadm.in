---
name: book-contractor
description: Find, instruct and book a contractor once there is authority, arrange access and keys, confirm visits, and handle a contractor's questions, missed appointments, cancellations or silence. Use for any dispatch, booking or access step on a ticket.
---

# Book a contractor

## Before dispatching
- Authority exists (landlord-approval) or the route allows a diagnosis visit (triage-maintenance-ticket).
- No duplicate: the landlord's own contractor or a provider already assigned owns the job.
- Who: the landlord's preferred contractor, then the warranty holder or original fitter, then a provider already used on this property, then get_skill `choose-provider` and `find_providers`. Nobody suitable: provider-research, and for routine work ask the landlord whether they have a contractor. Choosing a contractor is your job; only an urgent job with nobody available goes to staff.

## Work order (email to the contractor, `entity_ids` = ticket)
Property and the issue in the tenant's words; approved scope or limit ("fix if simple, otherwise quote first"); access (tenant role and recorded number, home or keys, pets, alarm, parking); keys needed (how many, who gets each); evidence on completion (what was done, cause, parts, photos, invoice). Offer two or three specific times from the tenant's availability.

## Access
- Occupied: agree date and time with the tenant and give at least 24 hours' notice, unless they agree otherwise or it is an emergency.
- Record exactly what the tenant agreed (home, keys, or OK to enter while out) in `access_instructions` and pass it to the contractor.
- Key location comes from the record or the agency. Not recorded: ask the agency or key holder in parallel and tell the contractor when you will confirm. Never guess, and do not hold a booking for an access question nobody has raised.
- If the tenants or parties give different answers about access or dates, do not pick one: confirm with each of them before booking, confirming or cancelling.
- When the assigned contractor asks for contact details, send the tenant's recorded name and number exactly as recorded. Never ask the tenant for details already held. Share them with nobody else.

## Bookings
- A proposed or approximate date is not a booking. Confirm date and time window with both sides; check the weekday matches the date.
- Set `scheduled_visit_at` and `status=scheduled`. Remind both the day before and the morning of the visit; if the tenant has not confirmed, call.
- No reply from a contractor within a few hours (urgent) or a day (routine): try another, within authority.
- An estimated arrival is not attendance.
- A contractor already booked, on the way or on site is left to work unless the record shows a safety or authority problem. Do not countermand their plan or send messages just to restate it.

## After the visit date
- No report within 1 to 2 working days: check inbound emails and calls first, then call the contractor.
- Fixed: job-completion. Needs a quote: landlord-approval. Parts ordered: `status=awaiting parts` with the expected date, wait until then. No fault found: confirm with the tenant. No access: find out why and rebook.
- Missed appointment: contact contractor and tenant the same day, apologise to the tenant, rebook. Second miss: offer the landlord another contractor. Third failed visit, or a second on an urgent job: escalation-and-handover. Any compensation request goes to staff.
- Contractor away or declining: record the return date; for urgent work find an alternative.

## Contractor questions
Answer from the record. If it is not there (key location, scope limit, payment), ask whoever knows and tell the contractor when you will come back. Never invent.
