# ADR: Merchant ownership checks

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Backend owner/admin checks protect merchant mutations and analytics. A separate malicious tenant is required in integration tests.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
