# ADR: Presence and Redis

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Use virtual coordinates and ephemeral interest-scoped presence. Redis supports shared coordination, but replicas are restricted until cross-worker authentication/reconnect/expiry tests pass.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
