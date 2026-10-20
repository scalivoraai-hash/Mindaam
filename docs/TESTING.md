# Validation strategy

Run python -m pytest backend/tests -q and frontend typecheck/build. CI additionally starts PostGIS/Redis, applies Alembic migrations, checks model drift and audits dependencies. Consult STATUS.md for actual executed results. A test file or workflow is not a passed test.

High-value integration cases: unauthorised tenant reads/mutations; blocked media/chat; atomic replay-safe reward/payment flows; consent/expiry; account deletion/export; administrator restrictions. Both PRODUCT.md critical journeys need browser E2E with two users and merchant/admin. Provider sandbox and multi-worker PostgreSQL tests remain distinct gates.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
