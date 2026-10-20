# Implementation roadmap

All epics start **pending acceptance**. Code presence alone does not pass an epic. Use STATUS.md for incremental implementation evidence. Each epic also requires schema/migrations, backend authorization, usable UI, error/loading/offline states, audit/analytics where relevant, tests and documentation.

| Epic | Scope | Acceptance evidence required | Status |
|---|---|---|---|
| 00 | Repository & Documentation | Reproducible repository; docs match tested code | Pending |
| 01 | Infrastructure/Foundation | PostGIS/Redis migration and readiness exercised | Pending |
| 02 | Authentication | Register/login/logout; brute-force/reset/verification reviewed | Pending |
| 03 | Consumer Onboarding | Adult consent versions and privacy flow persisted | Pending |
| 04 | Profiles/Avatar | Avatar/profile validation and private-field filtering | Pending |
| 05 | Geo/World Foundation | Cities/zones/cells and licensed geometry verified | Pending |
| 06 | 3D World | Playable scene, camera, movement, mobile fallback measured | Pending |
| 07 | Realtime Presence | Two clients, auth, reconnect, stale expiry and interest scope tested | Pending |
| 08 | Social Graph | Request/accept/block/mute/follow authorization verified | Pending |
| 09 | Messaging | Persistence, blocks, rate limits and realtime delivery tested | Pending |
| 10 | Voice | Consent-bound tokens and actual audio including denial/reconnect | Pending |
| 11 | LiveFace | Mutual consent, floating video, metering and revoke tested | Pending |
| 12 | Wallet/Economy | Atomic idempotent entries; separate assets and reconciliation | Pending |
| 13 | XP/Daily Drop | Server-clock daily eligibility and XP progression tested | Pending |
| 14 | Referrals | Attribution, eligibility and fraud-resistant reward tested | Pending |
| 15 | Pulse Harvest/Fruit | Server collection radius/expiry/idempotency tested | Pending |
| 16 | Gems/Treasure | Rarity, expiry, claim contention and replay tested | Pending |
| 17 | Missions | Progress/event idempotency and one-time payout tested | Pending |
| 18 | Crews/Leaderboards | Role-aware crew changes and non-fabricated ranking | Pending |
| 19 | City Battles | Server scoring, boundaries, anti-fraud and rewards tested | Pending |
| 20 | Events | Creation/join/capacity/timezone and cancellation tested | Pending |
| 21 | Business Platform | Tenant isolation, onboarding, verification and permissions tested | Pending |
| 22 | Virtual Stores | Owner-managed catalogue and consumer detail workflow | Pending |
| 23 | Campaign Engine | Funded budgets, lifecycle and concurrent spend tested | Pending |
| 24 | Visit & Earn/PulsePoint | Consent, short-lived challenge, replay and geofence tested | Pending |
| 25 | Perks/Redemption | Merchant-authorized redemption; one-time usage and expiry | Pending |
| 26 | Payments/Subscriptions | Verified Stripe sandbox checkout/webhooks/refunds/subscriptions | Pending |
| 27 | Transport | Vehicle entitlement and speed boundaries tested | Pending |
| 28 | Admin | RBAC, audit, verification and financial visibility tested | Pending |
| 29 | Moderation/Fraud | Reports, blocks, triage, appeals and fraud cases tested | Pending |
| 30 | Analytics/Observability | Real persisted events, dashboards and scrubbed telemetry | Pending |
| 31 | Security Hardening | Threat model and high/critical findings resolved | Pending |
| 32 | Performance/Load | Document measured client/backend load and bottlenecks | Pending |
| 33 | Deployment | Staging deploy, health, backups and rollback exercised | Pending |
| 34 | Release Validation | Both complete critical journeys plus all gates evidenced | Pending |
