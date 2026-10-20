# ADR: Immutable financial ledger

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Atomic ledger entries and unique request keys govern Credits/XP. Perks remain separate. Never edit history to repair balances; use reviewed compensation.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
