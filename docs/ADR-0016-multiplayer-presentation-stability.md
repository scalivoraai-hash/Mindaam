# Shared multiplayer and media stability

Continue the existing Presence, RentalLease, Ticket, MediaSession, LiveKit and WebSocket systems. No new infrastructure, schema migration, economy rule or world entitlement is introduced.

Remote player snapshots now include a read-only vehicle projection (asset/vehicle ID, kind, heading, speed, seat and sample time). One rendered transform owns each driver and vehicle. Bus passenger presentation shares the rendered bus transform; this exterior projection does not authorize conversations across zones or bypass visibility/privacy checks.

Boarding remains the existing atomic, idempotent ticket-and-seat transaction. It now advances the position revision, returns the seated position, and updates the client immediately before refreshing the timetable. Valid sessions retain virtual coordinates through a stale heartbeat; stale players remain hidden by the existing visibility expiry. Expired authentication still permits presence cleanup.

Media element ownership is stable across track events. Joined event audiences connect as listeners without enabling a microphone or camera. Existing room grants and publisher roles remain authoritative. Speaker video can populate the existing stage screen; media layout does not control player coordinates.

Building families use existing map tags, deterministic palettes and four shared facade textures. Unknown buildings remain neutral. The original footprints, paths, collision data and business names are unchanged.

Validation is in progress on the isolated fix branch. Three new backend regressions failed on the previous implementation and passed after correction. The full local backend suite (220 tests), frontend tests and production build passed. Real-browser acceptance runs against the production build and a disposable LiveKit server, with separate authenticated browser contexts and synthetic camera/audio inputs. This is not a claim of physical-device or production media acceptance.

Movement pace is tuned to 3.2 m/s walking and 6 m/s running (1.875x) to match the articulated avatar scale; vehicle speeds and reward/access rules are unchanged. Prediction covers one existing 500 ms snapshot interval with a 550 ms hard bound. Read-only migration inspection excludes actual extension-owned PostGIS relations and canonicalizes only demonstrably equivalent username-index expressions. Test rate-limit identities are isolated instead of weakening production limits.
