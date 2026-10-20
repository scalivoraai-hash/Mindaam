# ADR 010 — Extend existing world and authority boundaries

Status: implemented, pending live multi-user and device acceptance.

Use the existing database, authentication, ledger, media sessions and world renderer for transit, Friends, supported public interiors, auditorium events and advertising operations. Do not provision a parallel service or duplicate communication model.

Virtual zones isolate occupants while preserving the identity used by chat and LiveKit. Ticket purchases lock the user and route/vehicle; seat selection locks the vehicle. Database uniqueness and immutable ledger idempotency prevent duplicate fares/seats. World movement and snapshots lock the user before Presence to maintain the same lock order as boarding. The route network uses licensed mapped approaches and an explicitly compressed intercity interval. No real GPS or invented passenger population is used.

Platform operators receive a separate route with server-enforced permissions. Owner credentials are deployment secrets, with first-login password change and session revocation. No arbitrary SQL, shell, secret viewer or infrastructure panel is exposed in the product. Public templates only apply to eligible mapped non-residential places. Event audiences cannot publish until promoted, and use the same existing media room and controls.

Trade-offs: road coverage remains bounded districts rather than full-country geometry. Interior layouts are templates. Browser/GPU, mobile gestures and multi-device media must be accepted on supported real devices before release readiness can be claimed. New activity history starts with deployment. SQLite integration tests do not substitute for a concurrent production PostgreSQL load test.

Migration is additive, but an old image whose Alembic graph lacks fi25 cannot simply run its migration launcher against the newer database. Prefer a forward fix or a compatible rollback build retaining the new migration. Restoring a database snapshot is an operator recovery action requiring a write-loss assessment.
