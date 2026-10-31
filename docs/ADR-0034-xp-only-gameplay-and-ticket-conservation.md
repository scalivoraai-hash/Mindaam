# ADR 0034: XP-only gameplay and conserved event tickets

Owner request: gameplay must not create Pulse Credits. New positive PC ledger entries are limited to payment/subscription settlement and existing conserved ticket/refund paths. Welcome, daily, mission, referral and physical-visit gameplay no longer grant PC; XP rewards remain authoritative. Historical rows are not rewritten.

Ticket purchase locks the event and affected accounts, debits the attendee and credits the original organiser in one transaction, with paired ledger sources and idempotency keys. Cancellation reverses the original organiser credit before refunding the attendee. Insufficient organiser funds roll back cancellation rather than minting a refund. Legacy tickets without an organiser credit refund their original debit under the existing rule.

Grand Arena is default-closed behind MINDAAM_GRAND_ARENA_ENABLED. Production payment gates remain separate and unchanged. Free standard events and virtual auditoriums remain available. Enabling a flag is not payment-provider acceptance.

Historical reconciliation is dry-run only. It conservatively protects all purchased/transferred/refunded and ambiguous lifetime credits, attributes spending to gameplay first, and proposes only the remainder for owner review. No adjustment operation is provided. Actual production audit, backup and explicit adjustment approval remain required.

Feedback uses existing authentication, a new additive table, server-side Super Admin authorization, per-user submission limits and private audited review notes. Account export omits internal notes.

Billboards reuse existing placements, creatives and campaigns. Initial placements have map-bound geometry evidence and are seeded once; removal disables the placement without deleting campaign history. Rotation opportunities use bounded precomputed public-ground points, retain authored IDs and claims, and keep the hourly refresh and per-user daily limit. New rotation generations do not reset the global daily allowance.
