---
name: landlord-approval
description: Use whenever landlord permission, a quote, an estimate, a price, a second quote, a refusal or any cost decision is involved in a repair. Covers asking the landlord, reading exactly what was approved, comparing quotes, re-approval when price or scope changes, and recording and accepting quotes.
---

# Landlord approval

## Authority
You have no spending authority of your own. Authority comes only from the record: a landlord approval, a recorded pre-agreement, or a spending limit stated in the record. Within it, act and tell the landlord; do not ask again. Outside it, ask. Never assume a limit or approve on the landlord's behalf. A confirmed emergency allows a make-safe only (emergency-response).

## Asking
One email to the landlord: the problem in the tenant's words and the property; what you propose (inspect, repair if simple, or quote first); the price if known or "price not yet known"; the option to use their own contractor; the decision you need as a clear yes or no. Optional extras are separate yes/no questions. Only the agency asks the landlord; never ask the tenant to.

## Reading an approval
| Landlord says | It approves |
| --- | --- |
| "Yes send someone", "have a look" | An inspection only. Do not tell the contractor small repairs are fine; ask for findings and a quote. |
| "Go ahead" in reply to a quote | That quote's scope and amount. |
| "Do X too", "include the carpets" | That added item. Do not ask again; ask the contractor to include it and show its cost on the invoice. |
| A thumbs-up, "ok" | Only the question it answers. |
| "Get a second quote" | Nothing yet. Instruct nobody. |
| "I'll sort it", "my contractor will" | The landlord owns the job. Do not dispatch. |
| "Fix if simple, quote if expensive" | A simple repair on the visit; anything bigger comes back as a quote. |
Evidence of approval, strongest first: the landlord's message, a staff note that the landlord agreed, a staff "approval confirmed" entry. Each covers the job as then described unless contradicted. None covers a later quote, a higher price or a wider scope. Tenant requests outside the approved scope stay unapproved.

## Quotes
- Check the quote is for this property and job; quotes for the wrong flat happen.
- Contents unavailable: ask the contractor to put scope, price and VAT in the email body. Never quote figures you have not seen.
- A verbal or approximate price is not a quote. If a written quote is coming, wait for it before asking the landlord, unless urgent.
- State the VAT basis, or "VAT not stated". Compare quotes like for like on scope and VAT.
- `record_quote` each one (scope, exclusions, VAT, dates, evidence). Send it to the landlord the same day.
- After approval, `accept_quote` assigns the provider and records an expected expense. It never pays anyone.
- choose-provider covers how many quotes and who to ask.

## Instructing after approval
Get_skill `book-contractor`. The instruction restates property, exact approved scope and amount with VAT basis, exclusions, access, and asks for start and completion dates and photos and invoice on completion. Add a "do not start until" condition only when the record already shows a dependency. Then tell the tenant the work is approved and the contractor will be in touch, with no date unless confirmed and never the cost.

## Changes after approval
- Contractor did the repair on an inspect-only visit: send the invoice to the landlord saying the work was done on the visit; escalate only if it exceeds what was agreed or the landlord objects.
- Higher price, revised quote or wider scope: fresh approval.
- Never promise a tenant they will not be charged; who pays depends on the cause found.

## Refusal or deferral
Follow the triage-maintenance-ticket workaround row. Escalate (escalation-and-handover) only on an outright refusal of a repair that is the landlord's duty, or if the tenant says it is unsafe or unusable.
