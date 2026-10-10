---
name: rent-arrears
description: Reconcile overdue rent and follow up with tenants using source evidence.
---

# Rent arrears

Read get_property and get_ledger before acting. Use actual unpaid rent_due
charges, not a predicted balance. Check pending claims and evidence first.
Default grace is three days: email the lead tenant, record their reply and any
promise to pay; at day seven call if unpaid. Schedule follow-ups with
schedule_invocation and escalate to the managing agent under the recorded policy.
Treat a pending claim as unconfirmed until bank evidence clears it. Never
initiate payments. Record financial changes using record_transaction with
skill=rent-arrears. A workflow-caused correction requires reverse_transaction
with skill=rent-arrears, evidence and a workflow issue.
