# ADR: Staging-first container deployment

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Provide local Compose and private ECS/RDS/Redis with TLS ALB. Apply only after plan review, one-off migrations and health checks. Terraform is unvalidated until executed.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
