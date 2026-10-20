# Payments

POST /api/payments/checkout creates a provider checkout when configured. POST /api/payments/webhook receives Stripe events and must verify their signature before fulfilling. Payment success displayed by a browser is never authoritative.

Use Stripe test mode to exercise checkout success, cancellation, failed payment, webhook duplicate/out-of-order delivery and currency/amount/customer binding. Verify refunds, disputes and subscription lifecycle separately; these are not complete merely because checkout exists. Live keys, tax decisions and real charges require owner-controlled activation.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
