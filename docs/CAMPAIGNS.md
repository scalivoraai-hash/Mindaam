# Campaign funding

Campaign budgets are merchant-funded and lifecycle controlled. Publication must require verification and available funding, and reward spend must never exceed the reserved budget. Close/cancel handling must account for unused funds without altering past ledger entries.

Test concurrent claims, insufficient funding, ended campaigns, owner changes, idempotent publication/close and rollback of partial payouts. Development funding must be blocked outside local/test. Sponsored missions, zones, drops and City Battles require independent type-specific implementation and evidence.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
