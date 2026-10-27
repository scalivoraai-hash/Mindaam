# Historical living-world intake notes

This is the earlier work-in-progress inventory, retained for traceability. Its pending statuses and pricing/deployment notes are superseded by COMBINED_RELEASE_REPORT.md and evidence/combined-validation.json for the owner’s revised procedural-avatar release. It is not current release status.

# Mindaam living world release — work in progress

Pinned upstream source: `9533e15f7dd9fd8e689845338ef4932365bbd795` (2026-10-27).
The local source was retrieved through the connected GitHub account. Each retrieved file was checked against its Git blob SHA. No remote commit, push, infrastructure modification, or deployment has occurred.

All seven owner-provided engineering skills apply: UI/UX, multiplayer, performance, application security/payments, QA, GitHub CI/cost controls, cloud deployment. The owner supplied the complete 22-phase specification and explicitly confirmed implementation here.

## Acceptance matrix

| Phase | Existing implementation / work | Status and remaining evidence |
|---|---|---|
| 1 Audit | Read AGENTS, product/architecture/status, source inventory and deployment workflow | Scope traceability in progress; historical claims are not fresh validation |
| 2 Weather/seasons | New shared clock, deterministic five-minute schedule, shader seasons, pooled precipitation and quality controls | Local implementation; GPU, snow/foliage, day/night and audio acceptance pending |
| 3 Traffic/NPCs | Existing human NPCs; new bounded road-following cars/bikes/scooters/taxis | Local implementation; corner waits, endpoint parking/reversal, larger-road buses/delivery and bounded NPC variation implemented; connected-network routing, richer social actions and long-run acceptance remain |
| 4 Sky | Bounded birds, planes, helicopters, balloons, clouds | Local implementation; actual public-event balloon banner and stars implemented; kites and full-world visual acceptance pending |
| 5 Movement | Separate 0.6 outdoor walking factor; running/indoor/vehicle values preserved | Controlled-time tests verify the 0.6 outdoor walk change and unchanged running; final full-suite result pending |
| 6 Branding | Existing approved raster retained; adaptive header treatment and rendering filter | Local implementation; all-screen visual validation pending |
| 7 Chat | Existing handlers preserved; compact labelled icon toolbar and tooltips | Type checking passed in initial pass; two-user/mobile acceptance pending |
| 8 Arena | New shared premium exterior, real event billboard, navigation, deterministic safe placement | 45/45 placements regenerated with collectible clearance; all-city connected-entry and collectible test passes; full-city visual review pending |
| 9 Reservations | Existing user/destination locks and immutable ledger; 1/2/10/24 selection; UTC/DST slot calendar, receipts, top-up resume | 2/10-hour production prices require owner/admin configuration; concurrency and cancellation tests running |
| 10 Ticketing | Added Event ticket_price/programme and immutable-ledger ticket entitlements | Local code and additive migration; private-event approval, purchase races, refunds and media bypass tests pending |
| 11 Auditorium | Existing stage, roles, media, hand raising, announcements, reactions retained | Polls/Q&A, countdown, welcome and presenter introductions connected; audience API tests pass; two-browser media checks pending |
| 12 Lighting | 0–200% API/control bounds, synchronized slow colour/pulse, local reduced effects | Existing permission tests passed; new limit/reduced-effects tests and GPU validation pending |
| 13 Notifications | Existing invitation/reminder/announcement infrastructure | Booking/ticket notifications, ticket-holder start reminders and City Pulse discovery implemented; notification UX acceptance pending |
| 14 Promotion | Real arena billboard, event price/availability, sharing and cross-city detail links | Advertising board linkage, imagery and world-wide discovery incomplete |
| 15 Engagement | Existing social graph and event attendees | City Pulse, public creator profiles, consented highlights and bounded ambient arena groups added; full UI acceptance pending |
| 16 Screening | Added event categories and rights declaration/metadata; existing authorised screen share | Foundation only; no DRM, VOD, cash-out or geo-licensing enforcement claim |
| 17 Performance | Bounded particle/traffic/sky budgets, caching, no ambient DB writes, hidden-tab render pause | Placement precomputed; arena metadata uses a separate 30-second endpoint; fixture resource replacement checks pass. Full-world desktop/mobile benchmarks and prolonged city switching pending |
| 18 Security | Existing ledger/provider checks retained; tickets server enforced | Full abuse/concurrency/provider/migration review pending |
| 19 Responsive/accessibility | Compact toolbar, minimum hit targets, focus labels, reduced-effects setting | Multi-viewport, keyboard and GPU checks pending |
| 20 E2E | Existing test infrastructure; new climate/DST/booking/ticket cases | No full end-to-end or live-provider certification |
| 21 Backlog | Existing documented public rentals, transport, avatar, social and event modules identified | Full regression and gap closure incomplete |
| 22 Release | GCP deployment workflow is workflow_dispatch; old Railway prohibited | No commit/push until all required local gates pass. CI and staging not run |

## Evidence so far

- Existing frontend movement unit tests: 2 passed.
- New deterministic climate/clock/route tests: 3 passed.
- Focused existing backend outdoor movement and event presentation tests passed before subsequent ticket/arena edits; those edits require revalidation.
- TypeScript checks passed after Q&A and creator syntax fixes. Subsequent atmospheric changes require the final build.
- Placement: all 45 installed cities now have deterministic precomputed footprints and connected walking entrances. A separate test verifies collectible clearance and traversable entry samples in every city.

## Commercial and release boundaries

New 2-hour and 10-hour prices are deliberately absent until an authorised admin configures them. Test-only prices are isolated fixtures. No production prices, balances, users, paid resources, Stripe credentials, media policies or DNS were changed.

No functionality is represented as production-ready. The attached specification forbids pushing partial work. Outstanding items above must be completed or reported as blockers before any release claim.

## Additional local validation

- Focused backend suite: 24 passed (arena bookings/tickets/refunds, outdoor speed, original venue/rotating-collectible and event-presentation tests). Later financial guards and notification edits require revalidation.
- Audience polls, Q&A moderation, consented highlights and private paid admission: 2 new integration tests passed.
- Existing auditorium gifts/chat regression passed with the required paid booking added to its arrangement.
- Existing host-plus-three publisher-limit regression passed after explicitly selecting the destination and booking the arena. Its permission assertions remain intact.
- All 45 arena entry/collectible-clearance check passed.
- Client climate and movement tests: 5 passed.
- Initial isolated WebGL smoke: no shader/runtime errors; stable geometry/texture counts across five ambient replacements. Warm sampled render submission averages were 7–12 ms, with a cold sample of 156 ms. This is a small software-rendered fixture, NOT a full-world FPS or mobile performance claim.
- A broader backend run was interrupted to isolate the resource-heavy full-app browser check. It is not a passing full regression result.
- Fresh SQLite additive migration reached `fq27_grand_arena`; PostgreSQL/provider validation remains pending.
- All client library/component unit tests: 45 passed.
- Arena authenticated discovery/no arena payload in movement snapshots, and upcoming paid-event end/refund guard: 2 passed.
- Ticket-holder reminders and suspended-host upcoming cancellation/refund: 1 passed.
- Final production build, actual-app browser workflow and complete regression remain under validation. The current full backend run has reported failures; do not interpret focused passes as a green full suite.

## Latest validation pass

- The fresh isolated production build completed successfully (all 12 static pages, type checking and build traces). Two subsequent visual CSS/layout corrections are rebuilding.
- Final living-world renderer: all 14 weather states, no console/page errors, stable texture and geometry counts across five ambient scene replacements. Evidence: `evidence/living-world-renderer.json`.
- Auditorium renderer: all 11 presets plus 200% intensity and reduced-effects checks passed, no console/page errors. Evidence: `evidence/auditorium-renderer.json`. These fixtures do not certify full-world frame rates or real device performance.
- Full backend run reached all 271 tests with four failures: an obsolete walk-speed expectation, the live-event cancellation compatibility guard, a cooldown wall-clock assertion, and SQLite locking under concurrent load. The first two were corrected; targeted revalidation is running.
- The first loaded-world browser check exposed HUD overlap and an unreliable logo filter; CSS placement and the logo rendering treatment were corrected while preserving approved artwork. The reservation workflow stopped on an overly strict test selector. The local WebSocket origin setting was also corrected in the harness. Neither issue is counted as a completed E2E pass.

## Continuation audit — 2026-10-27

The source and previous uncommitted changes were recovered intact. Remote main was independently verified at `9533e15f7dd9fd8e689845338ef4932365bbd795`. No feature commit, push or deployment has occurred.

Additional changes:
- Public arena events now populate unused advertising boards; paid advertising campaigns retain precedence. Clicking promoted signage opens the actual event. Private records are excluded.
- Ambient traffic can continue through matching mapped endpoints, excludes disconnected shortcuts and does not reverse onto one-way links. Added a bounded seasonal kite. Four climate/route unit tests pass.
- The onboarding destination select has an explicit accessible name. The GCP browser test scopes its selection to the first-world fieldset, addressing the exact recorded staging timeout.
- Local multiplayer browser fixtures now fund and purchase arena reservations through the existing API before starting new auditorium events. Funding is restricted to disposable local SQLite QA databases. No production or staging funds were fabricated.
- Share-cooldown and movement elapsed-time regressions use controlled clocks so CI load does not change the tested time interval. Original behavioural assertions are preserved.
- Added a reproducible local booking browser check with isolated database, single-debit, receipt, runtime-error and mobile-overflow assertions.

Verification:
- Full backend run: 269 passed, one failed (wall-clock movement interval), 270 collected. The failing test was made deterministic and passed in a subsequent focused run; the share-cooldown regression also passed. This is not a second all-green full-suite run.
- Final frontend unit suite: 53 passed, zero failed.
- GCP automation unit tests: 58 passed. These mocked tests do not represent a live deployment.
- Prior isolated production build passed. The final source including continuation edits is being validated separately.

Observed external deployment state:
- GitHub GCP run `40438256961` failed at `onboarding-0` selecting Destination. Its saved evidence shows the onboarding page and destination list were present.
- Its existing staging release is `f53898771471b96debf3a91b65fa0de015152982`, revision `mindaam-staging-00002-bw9`, URL `https://mindaam-staging-qfrofqn4pq-nw.a.run.app`. Its recorded smoke result says ready, but `release_ready: false`. This is historical run evidence, not a new live verification.
- Connected GitHub operations do not provide workflow dispatch. The browser was logged out and returned GitHub's private-repository 404. No authenticated gcloud or gh executable is available in this workspace.
- Staging's existing media acceptance creates new auditorium events without a funded reservation. It must exercise an authorised funded booking or verified Stripe test checkout before it can validate the new reservation requirement. Do not disable the requirement or invent staging purchases.

Open release gates:
- Authorised 2-hour and 10-hour prices must be configured by the owner/admin; these durations intentionally remain unavailable until then.
- Final browser reservation and final-source build results must be recorded.
- Full-world desktop/mobile performance, prolonged city switching, physical-device checks and complete multi-user media/Stripe staging acceptance remain unverified. Renderer fixtures do not satisfy these gates.
- Richer mapped NPC behaviours (crossing coordination, entering/exiting public buildings and bus-stop activities) and all-screen visual acceptance remain incomplete relative to the full supplied brief.
- No partial release is permitted by the supplied brief. Do not mark this work complete or publish it while these mandatory gates remain open.
