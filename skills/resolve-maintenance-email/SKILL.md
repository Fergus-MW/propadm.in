---
name: resolve-maintenance-email
description: Resolve tenant maintenance reports with prompt updates and competing supplier outreach.
---

# Resolve maintenance email

Your objective is the earliest viable resolution, using qualified suppliers and sourced
spending limits. Coordinate the tenant and all suppliers within this same run.

1. Call get_plan first and create or revise the plan. Include acknowledgement, triage,
   supplier outreach, selection/booking, tenant timeline updates, completion verification,
   and the final tenant reply. Preserve the original tenant email id in the plan detail.
2. Before supplier outreach, use reply_email on the tenant's original email to acknowledge
   the issue, explain the next action and give a concrete next update deadline appropriate
   to urgency. Do not promise a repair time before a supplier confirms one. Set a wake-up
   that lets you honour the update deadline even if no supplier responds.
3. Read the email, property and existing tickets; create or update the maintenance ticket
   and link it to the property and reporter. Triage urgency and access constraints. Ask
   only for missing information that affects safe dispatch; continue useful outreach
   while awaiting answers. Follow applicable emergency procedures immediately.
4. Load choose-provider and use find_providers for the trade, location and urgency. Check
   qualifications and coverage; use provider-research if the directory is insufficient.
   Contact 2-3 suitable suppliers in separate send_email calls during this turn, before
   waiting on replies. Include the ticket reference, fault/scope, location, urgency and
   access constraints; request price including VAT/callout, exclusions, earliest confirmed
   attendance and expected completion. Link every email to the ticket and provider with
   entity_ids. Share only information needed for the job; keep competing suppliers in
   separate threads. If fewer suppliers qualify, contact those available and record why.
5. Record each successful outreach and its thread/email ids in the plan. The email tools
   automatically add these conversations to this run. Before sleeping, leave the waiting
   step blocked/in_progress and include the tenant, supplier threads and ticket in wake_on.
   Sleep at most 10 minutes, or less for an urgent response/update deadline. End the turn.
6. On each wake, read the new message and current plan. Record genuine supplier quotes
   with record_quote, including evidence, scope, price and timing. Compare earliest viable
   attendance/completion as well as price and qualifications. A fast email response alone
   does not prove fast attendance. For urgent work, proceed with the first suitable,
   qualified offer within sourced spending limits; do not wait for every quote. For routine
   work, use a short, explicit comparison deadline and choose the earliest viable offer
   with reasonable sourced cost. If no response arrives by the chase deadline, follow up,
   call suppliers or expand the search. Track whom you contacted to avoid duplicate requests.
7. Accept the selected quote with accept_quote where applicable and obtain an explicit
   booking/arrival window and tenant access confirmation. Tell other suppliers the request
   is closed; do not book duplicate visits. Reply to the original tenant thread with the
   confirmed supplier, attendance window, expected completion if known and next update time.
   If timing is unknown, say so and state when you will next update them. Send updates on
   delays, changed arrangements and promised deadlines even if there is no new information;
   avoid repetitive emails on every timer wake. Keep chasing toward resolution.
8. Keep completion verification and final notification steps open while the work is pending.
   Booking, dispatch, quote acceptance or an invoice alone is not evidence of resolution.
   Obtain a completion report or tenant confirmation that addresses the reported fault;
   if disputed or incomplete, continue the repair. Record the evidence, actual outcome and
   resolved_at on the ticket. When setting status to resolved or closed, also write both
   final_answer and reasoning as Markdown in fields. The final answer states the actual
   result and whether the requested work was executed; explain any unexecuted instruction.
   The reasoning is a thorough evidence-based audit explanation covering all observable
   steps, source/tool-result references, supplier comparisons, attempted actions, outcomes,
   verification, failures, skipped actions with reasons, and remaining limitations. Explain
   how the evidence supports the result. Do not invent missing steps or expose hidden model
   thoughts or private chain-of-thought. Then reply to the tenant's original thread explaining what
   was fixed and when, and how to report any continuing problem. Mark the final notification
   done only after reply_email succeeds. Finish only after resolution and notification are
   evidenced; service failures stay blocked with a next action and wake-up.
