# ADR 0021 — Mindaam identity and bounded startup media

2026-10-20. Scope: scalivoraai-hash/Mindaam only. Original source and Railway remain untouched.

The verified import is commit 68744ebaa12f56a6124dd0ead5a835fb485dbf66. Its 16 successful CI jobs remain the baseline; this change requires new validation.

## Identity

The owner's approved raster is retained byte-for-byte in public/brand/approved-logo.png. Cropped/resized exports preserve its pixels, typography, colours and white background. No replacement vector glyph is drawn. shared/brand.json owns identity and colour values; app/brand.css provides semantic CSS tokens. Metadata uses https://mindaam.com. PWA cache version changes so installed clients refresh the brand assets. Emails and public interface labels use Mindaam; the approved tagline is A LIVING WORLD TOGETHER.

Database tables, migrations, Pulse Credits, cookie names, event channels, payment idempotency prefixes and legacy package names are intentionally unchanged. Historical release documents remain evidence, not current branding. scripts/audit-brand.py distinguishes these exceptions from public product names.

## Media

shared/media-policy.json supplies launch defaults to client and server. Existing Config rows persist Super Admin overrides, validated by backend/api/media_policy.py, with Audit entries. Launch ceilings cannot be raised through the client. Default events have 50 participants; normal maximum is 100; 250 requires a successful load-test reference recorded by Super Admin. Host plus three stage speakers, one primary screen and at most four received video tracks are the defaults. Policy changes apply to new media joins; event admission reads current settings.

LiveKit connects with autoSubscribe false. Subscription selection admits required microphones, event speakers and only the authenticated presenter's confirmed screen SID. Ordinary avatar videos subscribe only when in view in mini mode, and no more than four videos are received (the primary screen consumes one slot). Adaptive Stream uses pixel density one; requested video dimensions cap mini at 360p and expanded/fullscreen at 720p. Publishers provide simulcast and Dynacast. Camera capture is never started by Join. Event microphone and camera both require explicit actions. Existing consent, room lifecycle, permission revocation and screen-source authorization remain authoritative.

Event stage playback uses a Three.js canvas/video texture: DOM visibility does not observe that surface. Selected event tracks therefore explicitly remain enabled while the document is visible, with the same subscription/quality caps. Background video unsubscribes. Audio continues according to the user's speaker/mute controls.

These client bandwidth controls are not a provider-enforced billing cap against a modified client. Backend membership, event capacity and stage grants enforce authorization; VM/resource quotas and monitoring are still necessary. Ordinary presence never creates a LiveKit connection.

## Persistent snapshot work

The previous WebSocket tick rebuilt all persistent state twice per second per connection. A bounded per-connection cache now reuses unchanged state for up to five seconds. No private payload is put in Redis. A shared Redis revision invalidates the cached state after committed ORM and bulk mutations, including motion, membership, privacy, suspension, logout and session deletion. Heartbeat-only changes and non-payload audit/analytics rows do not invalidate. Rollbacks do not publish revisions; a change during a snapshot prevents caching it under the newer revision. Authentication expiry is enforced before cache reuse.

Movement validation and database row locks are unchanged. Active media and own/peer bus journeys retain 500ms full-state sampling because their lease/proximity/travel state is time-dependent. The cache is disabled when Redis is absent, except explicit single-process unit fixtures. Production/staging still require Redis. A Redis read failure closes the WebSocket instead of serving cached private state.

Measured local idle fixture: 20 snapshots, two users, 920 SQL statements before versus 92 after; 18 cache hits, 2 misses, 90% fewer statements. This is **not** a moving-crowd scalability result. Global invalidation deliberately trades some cache hit rate for privacy/correctness; moving crowds can still invalidate every tick. GCP profiling must determine whether a scoped ephemeral movement projection is needed before expanding capacity.

## Cloud preparation and limits

GCP manifests set Cloud Run min 0/max 2, a bounded connection pool, and separate migrations from instance startup. PostgreSQL startup inventory takes an advisory transaction lock to serialize simultaneous initializations. Initial 1 CPU/1 GiB/concurrency 40 values are staging candidates, not measured production sizing. Self-hosted LiveKit configuration pins the release already tested by baseline CI. Secret values are runtime-only. Production manifests must not accept LiveKit Cloud hostnames.

No GCP resources were created. The browser currently reports Site Unavailable at console.cloud.google.com, and no authenticated Cloud CLI exists in this workspace. No production URL, DNS target, cost measurement, provider test or capacity certification is asserted.
