# Database and migrations

SQLAlchemy models define accounts/sessions/consents, ledger, presence, collectibles/claims/missions, social/messages/crews/events, moderation, media, referrals and entitlements. Commerce adds businesses, catalogue, offers, campaigns, funding ledger, PulsePoint challenges, visits, perks, store visits and payments/provider events. Inspect backend/api/models.py and commerce.py for authoritative fields.

Use Alembic from repository root. PostgreSQL is required for staging/production; SQLite is an isolated local/test fallback with different locking semantics. Run migrations against an empty PostGIS database and alembic check in CI. PostGIS provisioning alone does not mean models use geometry indexes. Financial records must not be destructively migrated. Foreign-key deletion and retention need deliberate review.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
