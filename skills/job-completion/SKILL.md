---
name: job-completion
description: Use when a contractor, landlord or tenant reports work done, when completion photos, an invoice, a no-charge or warranty outcome arrives, when keys must come back, or when a ticket might be ready to resolve or close.
---

# Job completion

## Completion
- A contractor saying "done" is a reported completion. Always ask the tenant to confirm the original symptom is gone (hot and cold both work, the door locks, the appliance finishes a cycle) with an easy yes or no. Their confirmation or clear before-and-after photos make it verified.
- Check the report: what was done, parts, cause, cost, photos. Cost above what was agreed, damage, or a report that does not add up: escalation-and-handover.
- "Main problem resolved", "temporary fix", parts ordered or a revisit needed: not complete. Name what remains.
- Landlord's own contractor finished: ask the tenant to confirm. If they cannot be reached after reasonable attempts, record it as reported and close with a recurrence route.
- Contractor recommendations (replace the door, change a valve) go to the landlord as information. Do not instruct them.
- No fault found, settled on its own, warranty or free remedial work are valid outcomes.

## Invoices
get_skill `contractor-invoice` for the ledger steps. Also:
- An invoice is not payment approval or proof of payment. Where the agency pays, wait for the tenant's confirmation or photo evidence first; forwarding it to the landlord marked "tenant confirmation pending" is fine.
- Contents unavailable: get them before any financial step. Never describe an invoice you have not seen.
- No charge or no invoice: record it; do not demand one.

## Cost route
- Landlord pays the contractor directly: tell the landlord the job is reported done and the invoice goes to them.
- Agency pays and deducts from rent: send the landlord the invoice with that note.
- Checkout works: invoice to the landlord; recovering any of it from the outgoing tenant's deposit is a staff decision.
- Charging the current tenant: staff decision.

## Keys
Lock, key and checkout jobs: confirm keys were physically received and counted. "Will drop them off tomorrow" means wait.

## Resolve and close
Set `status=resolved` with `resolution`, and `cost_actual` when known, once:
- the tenant confirmed, or one completion check went unanswered and the contractor's evidence supports completion, or the tenant fixed it, or no fault was found and the tenant agrees, or a landlord-owned job is reported done and not disputed;
- the cost route is known and the landlord informed;
- keys are back where relevant.
Tell the tenant what was done and how to report a recurrence, never the cost. Give the landlord what was wrong, what was done, photos, cost and invoice. Do not wait for payment confirmation. Do not close with an open safety concern, a dispute, an unconfirmed partial fix or keys outstanding. If the same fault keeps coming back here, `add_note` it on the property.
