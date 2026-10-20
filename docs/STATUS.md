# Release status — 2026-09-13

**Public testable alpha at https://pulseworld-production.up.railway.app/. Not certified production-ready.**

## Implemented

- Next.js consumer app, merchant and admin portals; public `/explore` simulated city preview, Three.js scene and 2D fallback.
- Account registration, login, onboarding, password reset/email verification plumbing, session revocation and consent.
- Server-authoritative movement, collectible claims, missions, daily rewards and immutable Credits/XP accounting.
- Friends, blocking, direct messages, Crews, invitations, events, notifications and CityBattles.
- Merchant onboarding/verification, catalogues, campaign funding, signed single-use PulsePoints, redemption and analytics.
- Stripe checkout and recurring billing integration with signed/idempotent webhook handling; LiveKit consent/session integration. Live providers remain unvalidated.
- Privacy export/anonymization, moderation, audit and configuration endpoints.
- Versioned migrations, PostgreSQL/PostGIS and Redis deployment configuration, unified Railway Docker image and CI definitions.

## Validation evidence

`npm run build` passed on 2026-09-13, including TypeScript checks and generation of all 11 static pages. The backend suite passed before the final public-preview privacy regression was added; the consolidated JUnit report bundled under `validation-artifacts/pytest.xml` records the final suite. Tests cover transactional/idempotent rewards, authorization, signed payment events, privacy and clean SQLite migration application with database-level immutable ledger checks. Passing local tests is not proof of production correctness.

## Remaining release work

- Publish source to a user-confirmed GitHub repository connected to Railway; no Railway projects or source remote existed at the last check.
- Build the Docker image on the target platform and validate durable PostGIS/Redis, HTTPS, migrations, restarts, backups and recovery.
- Complete real two-user browser and mobile journeys, provider sandbox payments/subscriptions, SMTP delivery and consent-based audio/video tests.
- Complete security/privacy review, operational ownership, legal-policy approval, accessibility and measured performance/load gates.
- Licensed real-map integration, broad world fidelity, production campaign content, advanced commerce/refunds, fully metered media entitlements and other unfinished specification requirements remain roadmap work.

Procedural scenes are explicitly simulated. No seeded fake users, merchant activity or payment success. Optional integrations fail closed without configuration. The full 120-section specification is retained in PRODUCT.md; this implementation does not claim full specification completion. See RELEASE_CHECKLIST.md for outstanding acceptance gates.

## Geographic world upgrade
Mapped districts, modular animated human avatars, skin/hair/outfit onboarding controls, follow/orbit camera, mapped minimap, mobile movement controls, labelled ambient NPCs, shaped collectibles and persistent authored trails implemented. Full city streaming, daily respawn, advanced NPC interactions, verified reward merchants and cross-device GPU/performance certification remain unfinished. Cloud browser has no WebGL: it can verify the interactive 2D fallback, not certify 3D rendering.

## 2026-09-14 repair
Realtime and maintenance database work now execute off the asyncio event loop. Postgres connection/statement/lock waits are bounded, with an ongoing readiness watchdog. Inventory derives from committed claims; rankings derive from collections/missions, not fake scores. Added pickup feedback, basket, map navigation, explicit cooldown-limited virtual fast travel, UK road nameplates, City Centre and Willen Lake mapped districts and trails. Local backend suite: 60 passing before final deployment. Full authenticated production browser, device audio/video and GPU visual acceptance remain unverified; provider credentials are absent. This is still a partial release, not full PRD completion.

## Pickup and communication repair
Automatic two-metre fruit/gem pickup now serializes requests and retries failures after eight seconds. Reward feedback uses authoritative award deltas. OAuth database/JWKS work runs off the event loop; Google requires verified email and preserves explicit account linking. Media grants reject text-only consent, invitations share duplicate protection, and end-call database work runs off the event loop. Build gates run backend regression tests and pickup state tests. Production device/OAuth acceptance is still required; test fixtures run only in APP_ENV=test. Google credentials were not found in existing production scopes; the three existing staged LiveKit variables were submitted for deployment.

## 2026-09-20 communication repair
Restored the published pickup/OAuth fixes before changes. Chat state now continues polling if the world WebSocket drops; messages can still be sent over authenticated HTTP. Media UI offers explicit autoplay recovery and voice/video switching, ending the previous room before joining another. Reconnected rooms reattach tracks; cleanup retries recent ended rooms after provider timeouts. The text endpoint cannot end a media session without provider cleanup. LiveKit environment variable names are present; Google names are absent from the active app service and the public Google button is disabled. Real two-account/device acceptance and broader release gates remain required; this is not certified production-ready.

## Release closure changes — 2026-09-20
Implemented username/email login, browser cookie sessions/CSRF checks, separate registration controls, change-password/session UI, provider-status endpoint and unavailable-provider hiding. Added returning-user home, onboarding talk preferences, configurable 10m/5m proximity and 30s requests, cancellation, privacy/mute enforcement, post-commit block cleanup, avatar-anchored mini media, merchant signage editor, map storefronts and category interior views. Existing ledger and consent-gated media remain authoritative.

Validation: 75 backend tests pass including real local two-client WebSocket exchanges, migration application, cookie/CSRF/password checks and storefront tenant controls. Production frontend build and final TypeScript checks passed. Three auto-pickup tests and 40 camera movement checks passed. A mail-worker threading regression test also passes. Deployment and live acceptance evidence are recorded separately. No two-device live voice/video or Google/mail-delivery success is asserted. Production configuration preflight found Google and mail credentials absent previously; native infrastructure recheck requested. Release-ready stays false until complete live acceptance evidence exists.

Live deployment and acceptance gates: see RELEASE_VALIDATION_2026-09-20.md. Production sign-off is not granted.

## Release recovery — movement and signage
Reproduced a deterministic collision defect in geography tests: Birmingham's configured origin was inside a building. Added validated entry spawn, swept movement with axis sliding, cached collision buckets, bounded automatic invalid-position recovery, an authenticated/cooldown Unstuck action, and stale-snapshot protection. Added street-facing nameplates for licensed named buildings/shops, with nearby culling and texture disposal. Added End/Report to the active chat toolbar and distance-aware LiveFace tiles.

Fresh live sign-in attempt returned "Invalid email, username or password"; no authenticated browser session was established. The supported browser provides no advertised isolated-context or GPU/device execution capability. Live two-device communication has not passed. Fresh infrastructure inspection again found Google/SMTP absent across inspected scopes; LiveKit variables/SDK are present, but the connector cannot execute a provider room query. No simulated media delivery is reported as live evidence.

## Targeted UI repair — 2026-09-21
Implemented explicit LiveFace mini/expanded/fullscreen layouts, persistent wrapping controls, compact join/disconnect states, camera-off avatars, and a cancellable connecting state. Chat is a constrained flex column with scrolling history and wrapped footer. Pending requests render solely from session state; acceptance clears stale waiting text and briefly announces connection. Nearby wording now Say Hi / Can We Talk?.
Added optional private identity fields, unrestricted avatar suggestions, owner-editable display location with explicit public toggles, and migration/privacy regression tests. Whitehouse is a display-name change only. Added reusable Top 10 physical scoreboards from existing rankings with per-location positions and distance-based detail. Mobile navigation exposes Missions, Harvest, Events and Rankings through existing drawers; viewport keyboard sizing and safe areas are respected.
Local validation: 84 backend tests, 3 pickup tests, 3 building-sign tests, 40 camera projection checks, production Next.js build. Browser blocked the data-URL local layout fixture; no workaround attempted. Live browser subsequently signed in as rocky; desktop chat bounds and profile controls were inspected at 1363×936. Actual multi-viewport responsive checks, GPU board rendering and the required two-user camera journey are not certified. See UI_VALIDATION_2026-09-21.md for precise gates.


## Communication group/split upgrade — 2026-09-21
Implemented additive group memberships/approval/privacy/capacity, common-room media membership, virtual proximity warning/grace/individual removal, stale-state reconciliation, avatar-attached mini tiles, voice-only states, interactive split-screen, group grids and content-driven chat height. Updated avatar proportions/joints/LOD and scoreboard presentation. All 91 backend regressions passed, including new group/capacity/block/expiry/proximity scenarios; 11 frontend unit tests and 40 movement checks passed. Production build and TypeScript passed. Live deployment and current acceptance limits are recorded in COMMUNICATION_VALIDATION_2026-09-21.md. Multi-device media and GPU/mobile performance remain unverified, so production acceptance is not claimed.


## 2026-09-22 release candidate
Implemented MyLilWorlds public branding, original-pair group moderation, hosted events/stage, audio playback deduplication and device controls, 12 licensed OSM districts, truthful recent-presence counts, Whitehouse import audit, mobile input isolation and faster running.
Validation: 114 backend tests, 13 frontend tests, 40 camera-relative projection checks passed; Next production build and type checking passed. Includes migration chain and group/event authorization regressions. See MYLILWORLDS_RELEASE_VALIDATION.md for required live evidence and remaining release gates. Do not mark production-ready merely because automated gates pass.


## 2026-09-24 targeted growth release
Implemented dynamic flat discovery, prominent real counts, four explicit Starter World choices, atomic permanent access, five-share unlocks, per-destination progress, channel composers/native/clipboard flows, opaque invite landing, social card and consent-aware growth metrics. Existing users preserve all 17 pre-gate worlds. No chat/media/event/movement/geometry/economic behavior changes in this release beyond world-entry access checks.
121 backend tests PASS, including migrated existing users, competing fourth selections, duplicate fifth shares, separate progress, cooldown and logout/login persistence. Frontend type/build and share-copy tests run. See GROWTH_RELEASE_VALIDATION.md for live acceptance status.

## 2026-09-25 connected city platform
Implemented Friends requests/lists/direct messages and consent-based cross-world friend calls; configurable room capacity; pitch/yaw/pinch camera; scheduled social transit, immutable-credit tickets and seats; mapped public-entry templates; auditorium stage roles/reactions/gifts/chat switch; ad enquiries/campaigns; and a separate server-restricted Super Admin portal. Existing growth/auth/communication/economy modules are extended in place. Full details and acceptance limits are in CITY_PLATFORM_RELEASE_VALIDATION.md.

Local evidence: 132 backend tests passed; 18 frontend unit tests and 40 camera-relative projection checks passed; Next.js production build and TypeScript passed. Subsequent lock-order/owner-configuration review passed all 11 targeted city-platform tests. Fresh migration/inventory bootstrap produced 32 routes, 34 stops, 2,129 supported public entries and 17 boards in 7.25 seconds locally. Counts describe content inventory, not user activity.

Owner bootstrap variables are absent from the current Railway service. No owner credential/account was fabricated. Real multi-user media, mobile/tablet/GPU and authenticated live acceptance remain unverified; release_ready remains false until those gates pass.

Deployment evidence: application commit 45c8f7b4f259ff0f33ae5e353e5682cd0135444e is live in Railway deployment 1749f97d-4016-4031-bd03-38626fb8fdf3 (SUCCESS). The container independently passed all 133 backend tests in 130.66 seconds. Final review passed 16 affected API tests and a clean Next.js build, including stale ticket/gift quote protection. Front/Back avatar-relative and onboard camera fixes are implemented; real-device camera testing remains pending. API startup/readiness passed. Live public landing, 17-destination preview and unauthenticated Super Admin gate loaded. No owner account or live media/device acceptance is claimed. Backup creation was unavailable through the connector; its temporary staged volume change was discarded and no infrastructure changes were deployed.

Final public live retest: 17 flat destinations including all three Milton Keynes destinations; current-world checkmark and Explore Now labels; London map switch; no horizontal overflow or unavailable 3D controls in the fallback. These public checks do not certify signed-in, multi-user, WebGL or physical-device behavior.

## 2026-09-25 global social expansion
Implemented a flat 64-destination catalogue: 17 existing active UK worlds, 28 international destinations and 19 future request places. Future worlds stay requestable until approved maps are installed and an owner activates them. Explicit unique interest, independent demand sharing and configurable audited thresholds extend existing discovery; four-world/share-unlock entitlements remain unchanged.

Added safe/recoverable building exits, mall hierarchy/directory and sourced business cards, category interiors, bounded virtual swimming/boats, exclusive server-driven rentals, immutable gift debits, rate-limited reactions, merchant manager permissions, premium ad boards and owner catalogue controls. The assistant remains disabled. Existing media/auth/reward systems are integrated in place.

Local evidence: 145-test full backend run passed before the final transport test was added; all 22 affected transport/integration tests then passed. 18 frontend tests, 40 camera projection checks and Next production build passed. Fresh migration/bootstrap and idempotent second bootstrap passed; first import takes approximately 57 seconds locally and startup readiness now permits 150 seconds. Final mall-layout regression/build and independent deployment test gates remain part of release verification. See GLOBAL_EXPANSION_RELEASE_VALIDATION.md for live evidence and acceptance limits.

Global release deployment completed: ac64c0c42f2f0c498b5af9e264dca354091fd0d9, Railway c1b543c0-dab0-4c5e-be11-d778cde631b4 SUCCESS. Latest backend container passed 147 tests. Fixed two defects found in authenticated live acceptance: stale cross-city interior recovery and world-action controls hidden under the harvest card. London entry/realtime presence, catalogue/demand/share handoffs, preserved Starter Worlds and permission rejection were observed live. Full details and 109 acceptance rows are in GLOBAL_EXPANSION_RELEASE_VALIDATION.md. Physical/GPU/multi-user and privileged owner/merchant positive flows remain unverified; release_ready remains false.

## 2026-09-26 movement and exploration correction

The input path now carries bounded intents over the existing authenticated WebSocket, keeps a latest-intent HTTP fallback, guards city/interior transitions, clears held input on focus/touch loss and reconciles snapshots without rewinding newer movement. Vehicle steering direction is corrected. Existing parked car placements have stable rental/scenery classifications and eligible street bikes/cars use the existing rental ledger. The mobile/tablet HUD groups secondary controls into Quick Actions and Camera, keeps a compact location control, and preserves contextual exits.

Shared provisioning adds 48 existing-type fruits/gems to each of the 28 active international destinations and any installed ACTIVE world with no authored collectible rows. Existing UK items/claims and economic/access rules are preserved. Four Starter Worlds and four-share unlock remain unchanged. No new respawn/repeat reward policy is introduced. See ADR-0014 and WORLD_MOTION_VALIDATION_2026-09-26.md for evidence and remaining acceptance limits. Production readiness is not asserted.

Movement follow-up deployed: application commit fa327ca4bdf9cd850e87775ffb78d8cc89ea52ab, Railway 395edafb-336a-45ba-a09c-ff6bab7aed61 SUCCESS. 217 backend tests passed locally and independently in the Railway image; frontend build passed. Existing-account live four-action Paris unlock, entry, five-XP fruit pickup and refresh persistence were verified. Final quick-input retest and logout/login persistence remain unverified after secure sign-in was declined. Physical-device/GPU/multi-user acceptance remains open; see WORLD_MOTION_VALIDATION_2026-09-26.md.

## 2026-09-29 premium visual transformation

Upgraded the shared MyLilWorlds HUD, cards, business information, city facades, roads, pavements, vegetation, vehicles, avatars, advertisements, scoreboards and auditorium presentation in place. Lower-sensitivity damped 360 camera input preserves server movement and all existing actions. Static colour batching retains spatial culling while reducing draw calls. No backend, database, wallet, access or media architecture changes.

Local evidence: 217 backend tests, 25 frontend tests, 40 camera projection checks and production build passed. Software-WebGL browser checks covered desktop/mobile Whitehouse, Cambridge, Paris, rankings, movement and a local auditorium event without page exceptions. Real-device performance and multi-device media acceptance remain open. See VISUAL_TRANSFORMATION_VALIDATION_2026-09-29.md and ADR-0015-premium-visual-layer.md; production readiness is not claimed.

Visual release deployed: commit 8a488740a35e5c274f4528462d2a9e7b01019ce0, Railway f1ca6190-e4f6-4a56-a1a5-b7a01576d0ea SUCCESS. Railway independently passed all 217 backend tests and the health check. Live updated branding/interface, the unchanged 45-place catalogue and Paris map/collectibles were verified through the public preview. Cloud browser verification used the existing 2D fallback; local Chromium verified 3D. Real-device/GPU and authenticated multi-user media acceptance remain open.


## 2026-09-29 multiplayer, movement, media and transit stability

Application commit `bd7e33dedc537b655a394fe4577fdc33bd6b1e30` repairs shared remote rental/passenger presentation, continuous human gait, stale-presence recovery, stable event/media playback and immediate atomic bus boarding acknowledgement. Buildings use mapped-type visual families; the auditorium gains shared stage/interior detailing. Existing economy, authentication, access, media room and transport authorization systems remain in place.

All nine jobs in CI run 36628764796 passed: 222 backend regressions, PostGIS migration/check, dependency audits, 30 frontend tests and production builds, infrastructure checks, plus six real-browser/LiveKit city jobs. London, Birmingham, Madrid, Dubai, Mumbai and New York each passed 29 checks (174 total) without browser errors. Events used one speaker and two participants; bus tests checked the complete destination journey and one fare debit. Separate Whitehouse WebGL observer and renderer checks cover vehicle attachment/poses.

Railway deployment `cff86ad4-f33e-4eef-a683-cece7611ea17` is SUCCESS for exact application commit `bd7e33dedc537b655a394fe4577fdc33bd6b1e30`. Its image independently passed all 222 backend tests; startup/readiness passed. Live public landing, 45-place catalogue and Whitehouse/Madrid map previews loaded through the existing cloud-browser fallback. Physical devices, Safari, normal-GPU performance and authenticated calls through the production LiveKit provider remain open acceptance gates. See MULTIPLAYER_STABILITY_VALIDATION_2026-09-29.md and the committed compact acceptance evidence. Release readiness is not asserted.

## 2026-09-30 — Event presentation extension (deployed; acceptance gates remain)

Previous application release `bd7e33de` was freshly confirmed SUCCESS on the existing Railway service before this work. Live landing/preview and HTTP health logs were checked; no deployment was restarted.

Shared movement calibration, connection-state CTA, source-specific Event screen sharing, local presentation views, shared venue lighting, optional purchased-credit reservations, admin Credit packs and lazy collectible rotations are implemented. Exact release CI 36711938964 passed all ten jobs: 336 production-build multiuser checks across London, Birmingham, Madrid, Dubai, Mumbai, New York and Sydney, all 229 backend tests, 31 frontend tests, migration checks, dependency audits and builds. The shared auditorium fixture uses 110 draws, two lights and one title texture. A separate production-build check passed at 390/820/1100 widths, exercising event controls, all six host tabs and a first-click shared lighting change. New additive migrations are fn30/fo30/fp30; existing ledger/claims and architecture remain intact. See ADR-0017.

Application commit `426edc7b536d0f66227f412b42443bf945b194a2` is live in existing-service Railway deployment `631b9960-7ccc-45e1-852c-0fb3fe41f8ce`, SUCCESS at 12:09:18 UTC. The actual image independently passed 229 backend tests in 417.72 seconds. Fail-fast migration startup, readiness and the deployment health check succeeded; proxy health returned HTTP 200. Live public landing, unchanged 45-place catalogue, Whitehouse/Sydney previews, shared release UI and the preserved 1.5-metre Preview keyboard step were verified. Cloud browser rendering used the existing map fallback.

Full production acceptance remains incomplete: production Stripe payment/webhook configuration is absent, authorised existing multiuser production test sessions were unavailable in this pass, and physical Safari/iOS/Android/tablet/normal-GPU checks are unverified. CI uses synthetic capture over real LiveKit/WebRTC and is not a substitute for those gates. No fake production users, funds, activity or new service were created. See EVENT_PRESENTATION_VALIDATION_2026-09-30.md for all 79 acceptance rows, 30 implementation/root-cause answers and committed evidence.


## 2026-10-01: targeted outdoor speed and XP mobility

ADR-0020 adds a shared outdoor-only 3× movement multiplier and the approved bike/car speed ceilings. Preview and indoor movement, polling safety, vehicle controls and bus routing remain unchanged. Car/bike/e-bike rentals and bus tickets now use configured numeric prices in XP through the existing atomic ledger; scooters/boats and all unrelated Credit uses remain unchanged. Explicit currency quotes reject stale Credit checkouts. No migration or production data conversion is required. Fixed-route baseline and initial after-change evidence are recorded; release gates and production verification remain pending until documented.


## 2026-10-20: Independent Mindaam release candidate

The 442-file source snapshot at Mindaam commit 68744eb passed all 16 baseline jobs. Approved logo/domain rebrand, media cost controls and cache optimization are now implemented in the independent Mindaam repository. Local frontend: 49 unit tests and production build pass. Focused backend policy/cache/event tests pass; full backend run exposed two outdated mocked function signatures, corrected and retested with their assertions preserved. The new revision subsequently passed all 16 remote CI jobs in run 39431534357; no repeat is required for unchanged application source. Measured idle snapshot SQL reduction is 90% (920 to 92 statements over 20 samples); active/moving-world performance is not certified.

GCP Console remains inaccessible (Site Unavailable); no project, staging service, production service, DNS target or billable resource was created. No GCP voice/video/Stripe or device acceptance is claimed. Original source repository and Railway remain untouched. See ADR-0021 and infrastructure/gcp/README.md.

## 2026-10-20 — GCP automation continuation

- Continue from remote application head `87ec2fb1c022abdf79fe6c975fedc69a1cf6bb18`, full Validation run `39431534357` (all 16 jobs PASS). No completed application/media/rebrand/snapshot development was repeated or reimplemented.
- Added Mindaam-only keyless bootstrap, idempotent foundation/release scripts, GCP Docker packaging, runtime SQL role/migration job, VM reconciler, direct/forced-TURN staging acceptance, monitoring and release-cost evidence gates. Added separate deployment validation; existing application CI job definitions unchanged.
- Production Cloud Run min0/max2; staging min0/max1; one e2-small media/Redis VM; db-f1-micro PostgreSQL, bounded disk and pools; no GKE/NAT/CDN/load balancer provisioned. Preserve existing 360p/720p, selective subscriptions, audience-off, host+3 and screen-share policy; preserve snapshot cache/SQL reduction.
- Account-owner steps and exact resume sequence are in infrastructure/gcp/README.md. First owner action: create/select dedicated **Mindaam Production** using `sain@scalivora.com`, proposed ID `mindaam-production`. Bootstrap automates APIs/IAM/WIF/variables/budget after billing and owner authorization. DNS targets are emitted only after a real reserved IP exists.
- **GCP deployment NOT PASS:** no real staging/production URLs, cloud configuration, DNS, cost measurements, physical-device acceptance or restore test yet. Infrastructure validation is not deployment. Google Console remains inaccessible from the agent environment; do not retry those pages. Old GitHub/Railway/database/domains/variables untouched.
