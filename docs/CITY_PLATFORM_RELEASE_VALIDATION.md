# Connected city platform — release evidence, 2026-09-25

This is an implementation and verification record, not a claim of complete production readiness. PASS below identifies the specific automated evidence. The requested live acceptance remains NOT VERIFIED wherever authenticated real-user, GPU or physical-device testing has not occurred.

## Automated evidence

| Check | Result | Scope |
|---|---|---|
| Backend regression | PASS — 133 tests | Existing auth, growth, ledger, messages, groups, events, geography, missions/businesses and new city-platform tests |
| Final review retest | PASS — 16 tests | City-platform and event tests after separated venue arrivals, initial seat allocation, camera corrections and stale-price protection |
| Frontend units | PASS — 18 tests | Media attachment safety, conversation state, pickup, sharing, avatar geometry, building signs, orbit math |
| Camera-relative projection | PASS — 40 checks | WASD direction against five yaw views; not a real mobile gesture test |
| TypeScript and production build | PASS | Existing Next.js application including /super-admin |
| Fresh Alembic migration | PASS locally | Additive schema through fi25; immutable existing ledger tests |
| Fresh inventory bootstrap | PASS locally | 32 directed routes, 34 stops, 2,129 supported public entries, 17 boards; 7.25 seconds |
| Road approach validation | PASS locally | All 17 hub segments checked against existing driving/traversability data |

`backend/tests/test_city_platform.py` checks mutual friendships/blocking/cross-world request consent, room authority and four-member cap, concurrent ticket deduplication and seat conflict, full/insufficient/locked no-charge responses, stop windows/travel bypass, supported public-building isolation, admin RBAC/enquiry deduplication/ad expiry, one-time owner bootstrap/forced-password gate, auditorium gifts/chat/stage/hand decline. These are local API integration tests using isolated test data. They are not live camera calls or a PostgreSQL load test.

## Deployment and live evidence

Application commit: `45c8f7b4f259ff0f33ae5e353e5682cd0135444e`.
Existing Railway deployment: `1749f97d-4016-4031-bd03-38626fb8fdf3`, **SUCCESS** on 2026-09-25.
Live app: https://pulseworld-production.up.railway.app/
Owner route: https://pulseworld-production.up.railway.app/super-admin

The Railway image build independently ran **133 backend tests, all passed**, in 130.66 seconds. The existing migration launcher completed, API startup completed and Railway readiness checks returned HTTP 200. The deployment used the same PostgreSQL/PostGIS and Redis services; no new project/repository/service or production test population was created. No infrastructure/variable/autodeploy settings changed. APP_ENV remains staging; release_ready remains false.

Live browser checks passed for the login landing page, unauthenticated Super Admin sign-in gate, public preview with all 17 independent destinations, and switching from Whitehouse to London. The first live inspection found camera presets overlapping the minimap; a follow-up fixes their placement/touch sizes and hides unavailable 3D controls in the map fallback. Live retest on the final deployment found 17 options, no horizontal overflow, and no unavailable camera controls visible in map fallback. The current selection read “✓ London”; each other option read “Name · Explore Now”; no dropdown option contained “Quiet right now.” All three Milton Keynes destinations remained independent. The count/empty-state stayed outside the dropdown. Selecting London completed and displayed its mapped streets. These verify loading and visible controls only. WebGL is unavailable in the cloud browser, so it displayed the application's existing map fallback; no 3D visual or camera-operation PASS is inferred.

Evidence: `docs/evidence/city-platform-admin-gate-20260925.jpg` and `docs/evidence/city-platform-preview-20260925.jpg` (initial preview before camera-control fix), and `docs/evidence/city-platform-preview-final-20260925.jpg` (final live London selector/map fallback). Structured automated/deployment evidence is in `docs/evidence/city-platform-automated-20260925.json`. A runtime sample contained 199 HTTP 200 responses and two 429 fast-travel cooldown responses, with no server exception observed. Existing authenticated movement requests returned 200; observing these logs is not a substitute for executing the full user journey.

The connector did not support manual database backup creation. No backup ID exists for this attempt. An erroneous staged volume edit made by the provider agent was discarded before deployment; the agent verified no staged infrastructure changes remained. Recovery/restore is not certified.

## Required live acceptance matrix

FAIL (unverified) means this release gate has not been demonstrated in the live environment. It does not mean an automated assertion failed. No item is marked live PASS from source inspection or a local test alone.

| Area | Required check | Live result |
|---|---|---|
| CITY DROPDOWN | Current location name only | PASS — live public preview; signed-in selector acceptance remains unverified |
| CITY DROPDOWN | Other locations "Explore Now" | PASS — live public preview; signed-in selector acceptance remains unverified |
| CITY DROPDOWN | "Quiet right now" removed | PASS — live public preview; signed-in selector acceptance remains unverified |
| TRANSIT | Central hubs | FAIL — not yet verified live |
| TRANSIT | Small stops | FAIL — not yet verified live |
| TRANSIT | 5/10-minute schedules | FAIL — not yet verified live |
| TRANSIT | Departure boards | FAIL — not yet verified live |
| TRANSIT | Destination signs | FAIL — not yet verified live |
| TRANSIT | Road-following buses | FAIL — not yet verified live |
| TRANSIT | Hail bus | FAIL — not yet verified live |
| TRANSIT | Credit ticket | FAIL — not yet verified live |
| TRANSIT | Insufficient balance | FAIL — not yet verified live |
| TRANSIT | Boarding | FAIL — not yet verified live |
| TRANSIT | Seats | FAIL — not yet verified live |
| TRANSIT | Passenger counts | FAIL — not yet verified live |
| TRANSIT | Social bus | FAIL — not yet verified live |
| TRANSIT | Stop request | FAIL — not yet verified live |
| TRANSIT | Safe exit | FAIL — not yet verified live |
| TRANSIT | Locked-world enforcement | FAIL — not yet verified live |
| FRIENDS | Send request | FAIL — not yet verified live |
| FRIENDS | Accept | FAIL — not yet verified live |
| FRIENDS | Decline | FAIL — not yet verified live |
| FRIENDS | Friends list | FAIL — not yet verified live |
| FRIENDS | Messages list | FAIL — not yet verified live |
| FRIENDS | Requests list | FAIL — not yet verified live |
| FRIENDS | Chat friend | FAIL — not yet verified live |
| FRIENDS | Voice friend | FAIL — not yet verified live |
| FRIENDS | LiveFace friend | FAIL — not yet verified live |
| FRIENDS | Remove friend | FAIL — not yet verified live |
| FRIENDS | Block | FAIL — not yet verified live |
| CONVERSATION | User-set participant maximum | FAIL — not yet verified live |
| CONVERSATION | Server enforcement | FAIL — not yet verified live |
| CONVERSATION | Full-room handling | FAIL — not yet verified live |
| 360 CAMERA | 360 orbit | FAIL — not yet verified live |
| 360 CAMERA | Front | FAIL — not yet verified live |
| 360 CAMERA | Back | FAIL — not yet verified live |
| 360 CAMERA | Left/right | FAIL — not yet verified live |
| 360 CAMERA | High | FAIL — not yet verified live |
| 360 CAMERA | Low | FAIL — not yet verified live |
| 360 CAMERA | Zoom | FAIL — not yet verified live |
| 360 CAMERA | Collision | FAIL — not yet verified live |
| 360 CAMERA | Mobile gestures | FAIL — not yet verified live |
| 360 CAMERA | Bus camera | FAIL — not yet verified live |
| 360 CAMERA | LiveFace compatibility | FAIL — not yet verified live |
| ADVERTISING | Boards | FAIL — not yet verified live |
| ADVERTISING | Default "Put Your Ad Here" | FAIL — not yet verified live |
| ADVERTISING | Contact form | FAIL — not yet verified live |
| ADVERTISING | Advertising enquiry persistence | FAIL — not yet verified live |
| ADVERTISING | Campaign creation | FAIL — not yet verified live |
| ADVERTISING | Ad scheduling | FAIL — not yet verified live |
| ADVERTISING | Board assignment | FAIL — not yet verified live |
| ADVERTISING | Fallback after campaign | FAIL — not yet verified live |
| SUPER ADMIN | Secure login | FAIL — not yet verified live |
| SUPER ADMIN | SUPER_ADMIN RBAC | FAIL — not yet verified live |
| SUPER ADMIN | Dashboard KPIs | FAIL — not yet verified live |
| SUPER ADMIN | Charts | FAIL — not yet verified live |
| SUPER ADMIN | Online users by destination | FAIL — not yet verified live |
| SUPER ADMIN | User management | FAIL — not yet verified live |
| SUPER ADMIN | World management | FAIL — not yet verified live |
| SUPER ADMIN | Transport management | FAIL — not yet verified live |
| SUPER ADMIN | Advertising requests | FAIL — not yet verified live |
| SUPER ADMIN | Advertising management | FAIL — not yet verified live |
| SUPER ADMIN | Audit logs | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Public building entry | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Interior exploration | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Realtime people inside | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Social interaction | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Safe exit | FAIL — not yet verified live |
| PUBLIC BUILDINGS | Private property blocked | FAIL — not yet verified live |
| LIVE AUDITORIUM | Existing Create Event preserved | FAIL — not yet verified live |
| LIVE AUDITORIUM | Live Auditorium option | FAIL — not yet verified live |
| LIVE AUDITORIUM | Stage | FAIL — not yet verified live |
| LIVE AUDITORIUM | Audience | FAIL — not yet verified live |
| LIVE AUDITORIUM | Reactions | FAIL — not yet verified live |
| LIVE AUDITORIUM | Gifts | FAIL — not yet verified live |
| LIVE AUDITORIUM | Chat | FAIL — not yet verified live |
| LIVE AUDITORIUM | Raise Hand | FAIL — not yet verified live |
| LIVE AUDITORIUM | Join Stage | FAIL — not yet verified live |
| LIVE AUDITORIUM | Friends nearby | FAIL — not yet verified live |
| LIVE AUDITORIUM | Existing Minimise UI preserved | FAIL — not yet verified live |
| LIVE AUDITORIUM | Existing Expand UI preserved | FAIL — not yet verified live |
| LIVE AUDITORIUM | Existing Full Screen preserved | FAIL — not yet verified live |
| PRODUCTION | Safe migrations | PASS — additive migration and startup completed on existing deployment |
| PRODUCTION | Existing production deployment | PASS — exact application commit, Railway SUCCESS and HTTP 200 readiness |
| PRODUCTION | Multi-user live test | FAIL — not yet verified live |
| PRODUCTION | Mobile production test | FAIL — not yet verified live |
| PRODUCTION | Desktop production test | FAIL — not yet verified live |
| PRODUCTION | Regression complete | FAIL — not yet verified live |

## Follow-up fixes

- Camera preset touch targets are at least 44px, arranged above the minimap. Map fallback hides unavailable 3D camera controls. The browser retest passed for this fallback layout.
- Front and Back use the avatar heading; first-person bus views use an onboard eye position, with transparent glazing. These require real GPU/device visual acceptance.
- Venue entries choose separated positions under venue-row locks, including stage promotion. Boarding assigns an available starting seat; passengers can still choose a different free seat. The affected 16 API tests passed locally, including stale ticket/gift prices and idempotent retries.
- Published source files were checked against their GitHub tree hashes. Only the intended application, tests, documentation and evidence files were published; local caches and unrelated untracked map datasets were excluded.
- Departure boards show the active vehicle’s fare/capacity snapshot. Ticket purchases and gifts require the price the user reviewed to match the server quote; a mismatch does not charge Credits. Repeated successful gift submissions return the original transaction and cost.
- Public preview uses the same current-world / Explore Now dropdown labels as the signed-in selector; online counts remain visible outside the dropdown.

## Remaining acceptance conditions

- Configure SUPER_ADMIN_EMAIL, SUPER_ADMIN_USERNAME and a strong one-time SUPER_ADMIN_INITIAL_PASSWORD through Railway secrets. Bootstrap refuses to elevate an existing account and does not log the password. The owner must change it before admin operations; remove the initial password secret after bootstrap.
- Sign in through the secure browser handoff and exercise the requested controlled-user flows. The cloud browser currently has no authenticated account, no advertised credential automation and no WebGL support. No API-created production test account was used to bypass that boundary.
- Complete two-user bus/Friends/building and multi-user auditorium/voice/LiveFace journeys on real devices, including reconnect, room limit and block/privacy behavior.
- Test desktop/tablet/mobile layout and touch gestures with GPU rendering, camera/microphone permissions and real media. Unit/build checks cannot certify visual alignment, collision or performance.
- Production PostgreSQL transaction contention/load, backup recovery and the pre-existing release checklist remain gates. The application continues to report release_ready=false.

## Intentional coverage boundaries

Bus approaches use approved mapped district roads. The intercity section is explicitly compressed; this implementation does not manufacture an entire national road mesh. Public interiors are real-world-inspired templates, not surveyed replicas. Current public-enquiry UI is authenticated; the schema permits a nullable owner reference for future approved public intake. Admin world management activates/configures installed licensed maps; adding an uninstalled city still requires its licensed map dataset. No fake passengers, viewers, social feed or historic analytics were added.
