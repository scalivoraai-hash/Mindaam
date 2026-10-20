# Economy

XP, Pulse Credits and merchant Perks are separate assets. Credits have no standard cash-out or arbitrary user-to-user money transfer. Every credit change requires an immutable ledger entry and server transaction; unique idempotency keys prevent replay.

Reconcile account balances to ledger totals; investigate differences before further payouts. Reward eligibility, campaign reservation and account credit must commit atomically. Test concurrent claims on PostgreSQL, repeated requests, failed commits, provider duplicates and malicious negative amounts. Local serialized SQLite tests do not prove PostgreSQL concurrency.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
