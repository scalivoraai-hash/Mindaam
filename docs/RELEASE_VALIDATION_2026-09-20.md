# Release acceptance evidence — 20 September 2026

Release decision: **NOT approved as production-ready.** FAIL below means the required live acceptance gate has not passed; it does not automatically mean a demonstrated application defect. Local tests are not substituted for live acceptance.

- Existing application: https://pulseworld-production.up.railway.app/
- Deployed code: `a0eb613c5a96d04c2dd2c997b2ae54508184fc02`
- Existing Railway service: `f28de9c9-b5c5-43da-bdfe-73aa4826d0b0`
- Successful deployment with `/api/health`: `bb6cece2-2926-4bd3-ac32-61c80e1c4214`
- No new repository, service, database, production test accounts or fabricated merchant records created.

## Evidence

75 backend tests passed. Coverage includes local two-user WebSocket invitations/messages, media consent/token restrictions, blocking, expiry/cancellation/cooldown, ledger invariants, migration execution, normalized username registration/login, cookie CSRF, password/session revocation, storefront tenant authorization and mail-worker threading. Production Next.js build and TypeScript checks passed. Three auto-pickup tests and 40 camera-relative movement checks passed.

Live browser verified the email-or-username login UI, registration confirmation and separate consent fields, hidden unavailable providers and working geographic 2D fallback. Live provider endpoint reports google=false, apple=false, facebook=false, emailPassword=true. Live health reports ready with runtime environment staging and release_ready=false. Railway startup/readiness succeeded without migration errors; final healthcheck used /api/health. Recent server logs also show successful world-entry, wallet, mission and collectible requests by existing sessions; these are not a controlled end-to-end test.

## Live release matrix

| Area | Feature | Result | Evidence / limitation |
|---|---|---|---|
| Authentication | Email registration | FAIL — blocked | Form inspected; no real account created in this test |
| Authentication | Email login | FAIL — blocked | Secure sign-in ended on login screen |
| Authentication | Username login | FAIL — blocked | Local test passes; no signed-in live session |
| Authentication | Google login | FAIL — configuration | Google credentials absent from all inspected Railway scopes |
| Authentication | Logout | FAIL — blocked | No signed-in live session |
| Authentication | Password reset | FAIL — configuration | SMTP and mail encryption configuration absent |
| World | 3D world | FAIL — environment | Browser GPU/WebGL disabled; fallback works |
| World | Movement | FAIL — blocked | No controlled authenticated browser journey |
| World | Nearby users | FAIL — blocked | Two isolated signed-in sessions unavailable |
| World | NPC distinction | FAIL — blocked | Labels implemented; authenticated 3D visual test unavailable |
| World | Fruit | FAIL — blocked | Local tests pass; live log success does not complete UI acceptance |
| World | Gems | FAIL — blocked | No controlled live collection test |
| World | Missions | FAIL — blocked | No controlled live progression test |
| Social | Wave | FAIL — blocked | Two signed-in sessions required |
| Social | Can We Talk request | FAIL — blocked | Local two-client WebSocket test passes |
| Social | Accept | FAIL — blocked | Local tests pass |
| Social | Decline | FAIL — blocked | Local tests pass |
| Social | Cooldown | FAIL — blocked | Local tests pass |
| Social | Text conversation | FAIL — blocked | Local two-client messages pass |
| Social | Voice | FAIL — blocked | LiveKit credentials exist; no live two-device call |
| Social | LiveFace | FAIL — blocked | No live camera exchange or avatar alignment validation |
| Social | Block termination | FAIL — blocked | Local authorization/cleanup tests pass; real room termination unverified |
| Social | Report | FAIL — blocked | No controlled live report submission |
| Business | 3D nameboard | FAIL — blocked | GPU and controlled merchant visual inspection required |
| Business | Storefront | FAIL — blocked | Owner configuration tests pass; live appearance unverified |
| Business | Business interaction | FAIL — blocked | Controlled real merchant/account required |
| Business | Products/services | FAIL — blocked | No controlled live merchant catalogue test |
| Business | Offers | FAIL — blocked | No controlled live offer redemption |
| Business | Visit & Earn | FAIL — blocked | Requires real participating merchant and explicit location check-in |
| Business | PulsePoint | FAIL — blocked | No controlled live merchant token verification |
| Business | Reward | FAIL — blocked | No live physical visit reward acceptance |
| Business | Analytics | FAIL — blocked | No controlled live merchant analytics journey |
| Economy | XP | FAIL — blocked | Local authoritative ledger tests pass |
| Economy | Pulse Credits | FAIL — blocked | Local ledger tests pass |
| Economy | Wallet ledger | FAIL — blocked | Local invariants pass; live controlled journey incomplete |
| Economy | Daily Drop | FAIL — blocked | No controlled live claim |
| Economy | Referral | FAIL — blocked | No controlled live referral journey |
| Infrastructure | PostgreSQL/PostGIS | PASS | Live /api/health validates DB/PostGIS |
| Infrastructure | Redis | PASS | Live /api/health validates Redis |
| Infrastructure | LiveKit | FAIL — blocked | Presence of credentials is not provider/call verification |
| Infrastructure | Railway deployment | PASS | Exact code SHA deployed, readiness succeeded |
| Infrastructure | Frontend build | PASS | Next.js production build and TypeScript checks |
| Infrastructure | Backend tests | PASS | 75 tests |
| Infrastructure | E2E tests | FAIL — blocked | Required two-user production path not completed |

## External actions required

1. In the **existing pulseworld service / production environment**, securely configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SMTP_HOST`, `SMTP_FROM`, provider-required SMTP login/password and `MAIL_ENCRYPTION_KEY`. Google callback: `https://pulseworld-production.up.railway.app/api/oauth/google/callback`; authorised origin: `https://pulseworld-production.up.railway.app`. Do not paste secrets into chat. The infrastructure connector confirmed these variables are absent, including shared/staged references; this is not a frontend detection failure.
2. Complete secure sign-in for a legitimate test account. Two real isolated sessions with supported WebGL, microphone and camera devices, plus a controlled participating merchant, are required for the specified live acceptance run. Cloud browser currently has WebGL disabled and is signed out.

This report does not certify every requested implementation or visual requirement as complete. Full visual quality, merchant customisation coverage, actual voice/video delivery and the full live journey still require acceptance; do not infer them from build or unit-test results.


## Recovery follow-up

The subsequent live secure-login submission returned **Invalid email, username or password**. The browser remains signed out. Its supported API advertises no isolated authentication contexts or GPU/camera execution control; creating two tabs would share cookies and would not prove two-user acceptance. No alternate supported device path was advertised. Test account creation through the browser requires owner-controlled credentials and acceptance of registration terms; neither was fabricated or bypassed.

Fresh Railway inspection confirmed the same app service, LiveKit variable names present, and Google/SMTP names absent from the 32 inspected references, including alternate names/shared/staged sources. The infrastructure agent could inspect container files but could not execute a LiveKit API query; its statement that SDK/configuration exist is not a connectivity PASS.

| Requested gate | Automated evidence | Live evidence |
|---|---|---|
| Registration, email/username login, sessions | PASS — backend authentication/session tests | BLOCKED — supplied live sign-in rejected |
| Google login | PASS — mocked identity/security tests only | BLOCKED — GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET absent |
| 3D rendering | Build PASS, not visual acceptance | BLOCKED — WebGL disabled in available browser |
| Movement | PASS — swept/sliding routes in London, Birmingham, Milton Keynes | BLOCKED — authenticated continuous walk not exercised |
| Stuck recovery | PASS — safe spawn, bounded recovery, no valid-position teleport, cooldown/auth | BLOCKED — authenticated live route unavailable |
| Nearby users | PASS — local authenticated two-user tests | BLOCKED — no two isolated authenticated sessions |
| Named building plates | PASS — facade normal, frontage, licensed POI assignment, no invented names | BLOCKED — 3D visual acceptance unavailable |
| Business storefront | PASS — ownership/configuration tests and build | BLOCKED — controlled merchant visual acceptance unavailable |
| Can We Talk, accept, decline, text | PASS — local two-client WebSocket tests | BLOCKED — no live account pair |
| Voice and LiveFace | PASS — consent, token scope, lifecycle tests | BLOCKED — actual bidirectional media not exercised |
| Moving during LiveFace | Build PASS only | BLOCKED — requires signed-in camera-capable pair |
| Block termination | PASS — local authorization and cleanup tests | BLOCKED — real provider-room revocation unverified |
| Report | Backend authorization tests; active-chat Report control builds | BLOCKED — no controlled live report |
| Fruit, gems, missions, XP, credits, wallet | PASS — authoritative claims/ledger regression tests | BLOCKED — controlled live gameplay journey incomplete |
| PostgreSQL/PostGIS, Redis | Existing health integration | PASS on preceding deployment; recheck after recovery deploy |
| LiveKit | SDK and configuration exist | BLOCKED — no provider connectivity or media acceptance |
| Railway/frontend/backend | Deployment/build/regression checks recorded in follow-up | Not equivalent to E2E PASS |
| E2E release journey | Local integration coverage only | BLOCKED — final product acceptance not achieved |

Movement changes address a demonstrated defect: the bundled Birmingham spawn is inside a solid footprint. Entry now chooses traversable ground. Movement sweeps small steps and slides when one axis remains open. Recovery has a 3m maximum and 30-second manual cooldown; valid users cannot teleport. Named map buildings now get street-facing fascia within a 100m/64-sign render budget. Active text chat now exposes End and Report; mini media tiles scale/cull by virtual distance. These implementations still require the specified live device acceptance.

## Deployed recovery verification — 2026-09-20

- Code commit: `200c34fdf6966b611ea12abdd69b4ff79782d157`.
- Existing Railway deployment: `97663d0f-bf12-477e-86c7-8ce601fdfeb4`, SUCCESS; exact commit verified.
- Backend suite: 81 passed. Building facade placement suite: 3 passed. Next.js production build: passed.
- Full map sign generation: London 798, Birmingham 229, Milton Keynes 19; zero non-finite placements. This validates data, not rendered appearance.
- Public `/api/health`: `status=ready`, `environment=staging`, `release_ready=false`. Dependency readiness succeeded; this remains intentionally not a production-release certification.
- Live browser entry screen loaded the updated “Map view · Explore your neighbourhood” fallback and login form. Available browser cannot verify GPU rendering.
- Live authentication attempt was rejected: “Invalid email, username or password”. No two-user live chat, voice or video acceptance is claimed.
- Google and SMTP configuration remain absent; owner-controlled credentials and supported live test sessions remain required as detailed above.

The preceding 75-test count is the earlier baseline; 81 is the final recovery regression count. The current deployment supersedes the preceding deployment references for executable code.
