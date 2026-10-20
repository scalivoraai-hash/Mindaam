# Operations

These are runbooks to validate in staging, not proof of staffed operations.

## First accounts
Consumer: open the web application, register an adult test account, accept the policy versions, then finish onboarding. Merchant: use a separately registered account and business portal; claim/create the organisation, then use administrative verification. Do not create fictitious real-world business activity.

Admin bootstrap: from a trusted API environment, run `python -m backend.api.cli create-admin --email operator@example.com`. Enter a unique password at the prompt. There is no shared default admin. Restrict execution to authorised operators; record the operator/change ticket. Confirm non-admin users cannot access admin APIs. MFA and stronger production session storage are release-review items.

## Health incident
Check `/health` for process health and `/ready` for dependencies. Inspect recent deploys, DB connections, Redis health, provider status and sanitized logs. Disable affected reward/payment feature before allowing degraded writes. Never manually edit wallet balances; use a reviewed compensating ledger workflow and reconcile.

## Payment incident
Preserve provider event IDs and ledger references. Verify webhook signature configuration. Re-deliver the exact provider event through the supported provider dashboard; confirm idempotency. Do not grant credits based on a screenshot or client success URL. Investigate missing, duplicate, refunded and disputed events separately.

## Abuse and privacy incident
Restrict the reported account or merchant with an audited admin action. Preserve only necessary evidence under the approved retention policy. Revoking/blocking a participant must terminate media authorization. Treat a precise-location disclosure as an incident; identify access, contain and follow the approved legal notification process.

## Operating controls to complete
Assign primary/on-call owners, support channels, moderation hours, alert destinations, spending budgets and escalation SLAs. Configure alarms for API error/latency, unhealthy ALB targets, DB storage/connections, Redis failures, ledger discrepancies and provider spending. Logs must not contain bearer tokens, passwords, raw payment payloads or precise device coordinates.
