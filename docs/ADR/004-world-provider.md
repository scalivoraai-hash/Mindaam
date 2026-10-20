# ADR: Independent world provider

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Use local procedural scene for development; licensed map imagery is a separate provider concern. Navigation/gameplay datasets must remain independent of restricted imagery.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
