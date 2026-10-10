---
name: landlord-statement
description: Generate monthly landlord statements with ownership-weighted figures.
---

# Landlord statement

Read get_balances for the landlord and ledgers for every owns property, including
share_pct. Reconcile pending/unallocated entries before reporting. Generate a
YYYY-MM statement with opening/closing balances, rent, deposits, fees, expenses
and payouts, citing source files. generate_statement stores the PDF as a source
file; send_email may share that statement using the existing email service.
State unresolved entries plainly. Remittance figures are reporting only; do
not initiate payments or treat a statement as a payment instruction.
