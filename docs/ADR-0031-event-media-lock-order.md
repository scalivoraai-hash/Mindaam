# ADR 0031: Event-before-media transaction locking

Status: accepted for implementation; deployment acceptance pending.

Staging outdoor acceptance exposed PostgreSQL deadlocks during auditorium re-entry. Sanitized error frames show event maintenance finishing a media session while social polling holds that session and requests its event. This reverses the existing event operation lock order and can exhaust the bounded request connection pool.

All explicit media-session lock entry points now read the immutable event association without a lock, lock the parent event when present, then lock and refresh the session. Standalone conversations still lock only their session. Caller authorization, session expiry, membership checks and event mutation locks remain unchanged. No retry, timeout increase, resource increase or assertion relaxation masks the failure.

A PostgreSQL concurrency regression uses a uniquely named isolated test schema and actual event-finish/social-poll functions. It waits for the database-reported lock boundary, verifies cleanup can finish and verifies polling then denies the ended conversation. It never operates on staging or production data. Existing media, event, presentation and conversation tests and actual staging forced-TURN acceptance remain required.
