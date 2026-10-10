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

Read PDF/image attachments through their ingested source documents and cite the original
file and extracted text/description. Check document identity: an inspection report is not
a quote, and a duplicate attachment is not a second estimate. Preserve uncertainty in
OCR/image descriptions; unreadable amounts or scope need clarification.
Where the final invoice is lower because an item was unnecessary, record that explanation
and compare the remaining scope to completion evidence. Landlord approval to pay is not
proof of payment. When the landlord pays the contractor directly, record that arrangement
and only settle after payment evidence arrives; do not invent an agency disbursement.
Missing completion photos, keys return or required confirmations remain outstanding even
if an invoice is received or the request is moved to Result.
