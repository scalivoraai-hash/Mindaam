# PulseWorld communication upgrade — verification

This release continues the existing repository, Railway service, authentication, text message store and LiveKit integration. Gameplay, maps, wallet/reward calculations and ranking calculations are unchanged. Scoreboard changes are visual only.

## Implemented scope

- Mutually exclusive request states, revision-aware acceptance/ending reconciliation, temporary feedback, compact pending requests and content-driven chat.
- Identity-attached mini video/voice/camera-off tiles, projected/smoothed anchors, speaker outlines, mini controls and chat collapse.
- Expanded 44/56 video/world split, portrait vertical split, remote primary/local PiP and group grids; fullscreen grid and Message access.
- Server-authoritative virtual distance warning/grace/cleanup, independent group departure and final-member session ending.
- Additive approved nearby group membership, privacy/block checks, idempotent approval, six-person default capacity, shared text history and same existing media room.
- Human avatar proportions, articulated limbs, idle/walk/run/wave/collect/speaking motion and geometry LOD.
- Scoreboard gradient, medal rows, clear XP hierarchy and personal-rank highlight using existing scores.

## Executed automated tests

| Check | Result | Scope |
|---|---|---|
| Full backend regression suite | PASS — 91 tests | Existing domain tests plus seven group cases; migration applied to a fresh test database |
| Group decisions and messages | PASS | Unauthorized send, duplicate approval, history delivery and sender identity |
| Same-room media authorization | PASS | All three grants target the same existing room; this is token validation, not delivered audio/video |
| Group capacity | PASS | Four-person override and default six-person maximum, seventh rejected |
| Privacy and blocking | PASS | Closed policy, incompatible pending request BLOCKED, blocking member removed, remaining members continue |
| Request lifetime | PASS | Cancellation and expiry deny subsequent acceptance |
| Proximity | PASS | Warning, grace, hysteresis reset, independent third-person departure, pair continuation, all media kinds ended on pair separation |
| Consent | PASS | Invited group media member denied token until accepting; declined invite denied |
| Frontend regression tests | PASS — 11 tests | Three state ordering, two avatar LOD/animation, three pickup and three building-sign tests |
| Movement math | PASS — 40 checks | Existing camera-relative projection checks |
| Production frontend build / types | PASS | Next.js production build and TypeScript checks |

## Required live acceptance matrix

“FAIL — unverified” means the user's live acceptance gate has not passed; it does not assert a reproduced defect. Automated checks above do not substitute for real camera delivery, GPU rendering, device performance or multiple independent users.

| Area | Required gate | Result |
|---|---|---|
| MINIMISED LIVEFACE | Avatar attached video | FAIL — unverified live |
| MINIMISED LIVEFACE | Video follows movement/camera | FAIL — unverified live |
| MINIMISED LIVEFACE | Voice-only tile | FAIL — unverified live |
| EXPANDED | Split screen | FAIL — unverified live media |
| EXPANDED | Remote video | FAIL — unverified live |
| EXPANDED | Local PiP | FAIL — unverified live |
| EXPANDED | World remains interactive during media | FAIL — unverified live |
| FULLSCREEN | Existing fullscreen and return | FAIL — unverified live media |
| PROXIMITY | Warning | FAIL — live gate unverified; server test PASS |
| PROXIMITY | Distance disconnect | FAIL — live gate unverified; server test PASS |
| PROXIMITY | LiveKit cleanup | FAIL — provider removal unverified; local state/grant revocation tested |
| GROUP | Join request | FAIL — live gate unverified; API test PASS |
| GROUP | Approval | FAIL — live gate unverified; API test PASS |
| GROUP | Group text | FAIL — live gate unverified; API test PASS |
| GROUP | Group voice | FAIL — unverified delivered audio |
| GROUP | Group LiveFace | FAIL — unverified delivered video |
| GROUP | Independent distance leave | FAIL — live gate unverified; server test PASS |
| AVATAR | Improved human proportions | FAIL — GPU visual gate unverified |
| AVATAR | Movement animation | FAIL — live visual gate unverified; finite transforms tested |
| AVATAR | Mobile performance | FAIL — real device measurements unavailable |
| STATE/UI | Waiting message clears | FAIL — live acceptance transition unverified; stale ordering test PASS |
| STATE/UI | Blank panel removed | FAIL — live media gate unverified |
| STATE/UI | Responsive UI | FAIL — five device/orientation gates not executed |

## Browser and environment evidence

The existing live domain is https://pulseworld-production.up.railway.app/. A real existing account (rocky) is authenticated. The cloud browser exposes one shared browser profile, no viewport/device emulation and no camera/GPU testing capability; the application displays its existing GPU-unavailable map fallback. No fake users, synthetic media or injected production records were used. Earlier desktop chat and profile verification is documented in UI_VALIDATION_2026-09-21.md. A browser policy rejected the earlier local data-URL fixture; no alternate hosting/injection workaround was attempted.

Production sign-off is withheld until real multi-user media, GPU and mobile acceptance gates pass. Existing release_ready remains false.

## Deployment

Deployment verification is recorded below after publishing this code to the existing service.
