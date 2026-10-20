# ADR: PostgreSQL and PostGIS

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Use managed PostgreSQL/PostGIS for deployed data. SQLite is local/test only and has different concurrency semantics. Spatial type/index adoption must be demonstrated, not inferred from the database image.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
