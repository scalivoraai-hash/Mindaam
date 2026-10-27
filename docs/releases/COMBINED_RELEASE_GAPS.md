# Release limitations and acceptance gates

The latest owner instruction replaces the external rigged-avatar requirement with improvements to the existing procedural avatar. See COMBINED_RELEASE_REPORT.md for implemented scope and measured checks.

- Live GCP staging readiness requires the exact published SHA to pass application CI, deployment/migrations, HTTPS, multiplayer, paid venue and direct/forced-TURN media acceptance. Do not report readiness from unit-test mocks or local screenshots.
- The paid staging journey needs a legitimately funded dedicated QA host and explicit per-booking limit in GitHub settings, described in the report. No artificial remote credits or payment success are allowed.
- Physical mobile/desktop performance, full-map visual coverage and real Stripe purchases are not certified by the small local renderer/browser fixtures.
- Optional future scope: externally rigged characters/facial morphs, expanded wardrobe studio, anonymous profiles, full Creations/Friends tabs, every crew/search/notification entry point, photo moderation operations, rich NPC crossing behaviour and verified landmark/facade datasets. These are not represented as implemented in this revised release.
- Production promotion, DNS and original MyLilWorlds/Railway remain separate from this staging release.
