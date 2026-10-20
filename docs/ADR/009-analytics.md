# ADR: Persisted event analytics

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Use real application events and distinguish interaction types. External analytics sinks require privacy scrubbing, consent and budgets before activation.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
