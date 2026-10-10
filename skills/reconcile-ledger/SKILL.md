---
name: reconcile-ledger
description: Assign bank lines and reconcile payments to evidence-backed charges.
---

# Reconcile ledger

Use get_unallocated, then check property references, payer tenant_of/owns,
invoice and ticket links. Allocate only with one supported property match;
chase missing evidence when ambiguous.
For needs_classification receipts, establish the payment purpose from evidence;
pass an explicit category and kind to allocate. A tenant receipt alone does not
establish rent versus a deposit or recharge. Leave unresolved claims queued.
Read get_ledger and match cleared rent
to the oldest open charge. Use settle for partial matches within both remaining
amounts. Confirm pending claims with bank evidence; retain all evidence and the
original economic entry. Record using skill=reconcile-ledger; correct mistakes
by reversing, never editing/deleting. Never send money or save bank details.
