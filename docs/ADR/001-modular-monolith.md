# ADR: Modular monolith

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Keep API domains within one FastAPI deployment while preserving domain routers and transactions. This reduces distributed financial failure modes. Split services only after measured operational need.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
