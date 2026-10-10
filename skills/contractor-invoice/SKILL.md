---
name: contractor-invoice
description: Validate repair invoices against tickets, quotes and completion evidence.
---

# Contractor invoice

Read the ticket, property, provider, quote and source invoice. Compare scope,
cost estimate, accepted quote, VAT and observed completion. Record an expected
expense charge with paid_to provider, for_ticket and source chunks. Flag overruns
and missing completion evidence; chase the provider for clarification.
Record confirmed contractor payments separately and settle against the invoice.
Invoice charge and payment must not both debit the landlord. Use
skill=contractor-invoice on financial writes/corrections. No payment initiation.
