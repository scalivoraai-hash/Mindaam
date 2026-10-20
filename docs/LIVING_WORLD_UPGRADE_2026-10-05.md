# MyLilWorlds upgrade checkpoint — 2026-10-05

**NOT COMPLETE. Billing is resolved. Repair 5bf5bed is deployed. Header fix c1cd3c1 passes local tests and 210 outdoor/XP CI assertions; eight remaining checks were cancelled before execution by GitHub. A deployed-main retry also exposed an intermittent movement-performance failure. New feature phases have not started.**

## Historical billing block — now resolved

GitHub Actions run [37350382930](https://github.com/sainsabu41-cmyk/pulseworld/actions/runs/37350382930) rejected all 16 jobs before they started. After secure GitHub sign-in, the actual annotations confirmed an account payment/spending-limit restriction. The account owner subsequently resolved billing; this is historical evidence. No payment, spending-limit change or CI bypass was attempted.

Production: `5bf5bedde87cc9a5a5eda596d724decc36af6f44`, Railway deployment `5d94830c-380b-4795-a4ef-3b6247820777` (SUCCESS). Full release-branch CI run 37360651180 passed 16/16 jobs. Live London entry, rental, clean first-click exit, ledger and refreshed 240 XP / 120 PC balances were verified. Follow-up `c1cd3c10f08784514978d20330b7abf9129717b5` remains on the existing release branch, blocked in CI run 37363973776. No new project, service, database or migration; no data reset.

GitHub's later main-branch run 37362173653 passed 14 jobs but cancelled media/outdoor before execution: “The job was not acquired by Runner of type hosted even after multiple attempts”, with an internal server error. Only those failed infrastructure jobs were retried. This is separate from the resolved billing block and from the earlier successful 16/16 release-branch run.

## Billing recovery and cold trail caches — 2026-10-05

GitHub billing eligibility was restored by the owner and run 37350382930 was rerun. The jobs now execute. The outdoor-XP job failed the unchanged approximate-3x walking gate: 16.612 m/s, with a 1,401ms maximum acknowledgement and 1,773ms server-update gap; running measured 70.732 m/s. The failure is retained. No threshold, route or input strength was changed.

Investigation found a separate concrete synchronous cold-path problem: eight UK trail cache entries had version 2, while the loader requires 3, and another nine UK maps had no prepared entry. The preparation script deliberately skipped the UK even though hourly rotations use the same loader. A fresh-process `prepared_points(city,48)` measurement took 6,162.42ms for Whitehouse and 1,368.27ms for London. Cache preparation now includes all installed cities; Nottingham records completed preparation at 96 requested points even though its safe mapped area yields only 14. This prevents falsely treating a complete small-city result as a missing cache.

After preparation, fresh-process calls measured 2.061ms / 1.899ms respectively (Nottingham 1.838ms). These are isolated function timings, not world-ready times or FPS. All 17 UK runtime point sequences were regenerated and compared with the cache's first 48: identical, including Nottingham's complete 14-point sequence. Authored database collectibles, claims and ledgers were not modified. The existing provisioning/idempotency tests remain passing.

43 affected backend tests passed, including a new test that forbids request-time trail generation for every installed world and validates all returned points against roads/buildings/private areas. Browser diagnostics now record long tasks during measured movement; the intermittent CI walking delay is not declared resolved solely from the cache benchmark. The candidate must pass the unchanged browser gate and full CI, then deploy and verify live. New living-world/profile/concert features have not started.

Evidence: `evidence/outdoor-xp-2026-10-01/cold-trail-cache-20261005.json`.

## Previous work and repair

Recovered the existing repository, latest commits, previous request evidence, 16/16 passing CI runs for fd0d116, Railway build/deployment, runtime readiness and missing live acceptance. The previous movement/XP implementation was already deployed. Its pending work was authenticated production verification.

Live secure sign-in to the existing authorized account succeeded. Whitehouse, Paris and London loaded with a live connection in the map fallback. A Whitehouse-to-London bus ticket charged 20 XP once (285 → 265); 120 PC was unchanged. Reload restored the paid journey; the journey completed and disembarkation succeeded. Historical car/e-bike XP debits were visible in the wallet. A London e-bike rental then charged 15 XP (265 → 250), again leaving 120 PC unchanged.

Exiting that e-bike reproduced `No active vehicle` after the exit succeeded. The 120ms input loop still saw an active rental while the exit flow awaited a second full world request. Late HTTP/WebSocket replies could display the stale error. The repair pauses input synchronously, drops unsent movement, rejects superseded replies by sequence, and applies the exit endpoint's authoritative safe walking position directly. Both exit controls share this path and show immediate pending feedback. Failed exits/current movement errors remain visible. No changes to server authorization, movement speeds, prices, wallet accounting or migration history.

Local verification: 46 frontend unit tests, 40 camera projection checks, typecheck and production build passed. Desktop outdoor-XP browser suite passed 22 assertions, including delayed exit responses for bike/car, single exit requests, existing approximate-3x speed checks, XP debit and bus retry checks. Mobile and tablet each passed 24 assertions, including native touch input. Total: 70 browser assertions across three viewports. Results are recorded below. These are local production-build checks, not deployed-repair verification.

The production browser has no WebGL. Live GPU rendering, physical mobile/tablet, Safari/Edge and two-device media have not been certified. CI browser emulation is not physical-device testing.

## Requested acceptance matrix

Results below are **completion gates for this requested upgrade**, not claims that every existing feature is broken. `FAIL — blocked/not verified` means the required implementation or live evidence is absent. Existing-release observations and local checks are explicitly scoped. Nothing is marked complete merely because an earlier CI run passed.

## PREVIOUS PENDING WORK

| Check | Result / evidence |
|---|---|
| Previous Tasks Reviewed | PASS — repository, commits, CI, Railway and earlier evidence recovered |
| Pending Work Completed | FAIL — exit/cache/catalog repairs deployed; balance-header follow-up awaits CI/deployment/live acceptance |
| Previous Tests | FAIL — 5bf5bed passed 16/16 CI; c1cd3c1 full CI pending hosted runners |
| Previous Deployment | PASS — 5bf5bed Railway deployment SUCCESS; subsequent balance follow-up pending |
| Previous Live Verification | FAIL — repaired exit verified live; balance-header follow-up not yet live |

## PERFORMANCE

| Check | Result / evidence |
|---|---|
| Initial Landing | FAIL — new upgrade not started; not verified live |
| Login → World | FAIL — new upgrade not started; not verified live |
| City Switch | FAIL — new upgrade not started; not verified live |
| Refresh | FAIL — new upgrade not started; not verified live |
| First-Tap Feedback | FAIL — new upgrade not started; not verified live |
| No UI Freeze | FAIL — new upgrade not started; not verified live |
| No Duplicate Requests | FAIL — new upgrade not started; not verified live |
| World FPS | FAIL — new upgrade not started; not verified live |

## PROFILE

| Check | Result / evidence |
|---|---|
| Own Profile | FAIL — new upgrade not started; not verified live |
| Public Profile | FAIL — new upgrade not started; not verified live |
| Social Links | FAIL — new upgrade not started; not verified live |
| Privacy | FAIL — new upgrade not started; not verified live |
| XP / Stats | FAIL — new upgrade not started; not verified live |

## AVATAR

| Check | Result / evidence |
|---|---|
| Human Proportions | FAIL — new upgrade not started; not verified live |
| Hair | FAIL — new upgrade not started; not verified live |
| Clothing | FAIL — new upgrade not started; not verified live |
| Shoes | FAIL — new upgrade not started; not verified live |
| Accessories | FAIL — new upgrade not started; not verified live |
| Free Options | FAIL — new upgrade not started; not verified live |
| Animation | FAIL — new upgrade not started; not verified live |
| LOD | FAIL — new upgrade not started; not verified live |

## LIVING WORLD

| Check | Result / evidence |
|---|---|
| Rain | FAIL — new upgrade not started; not verified live |
| Snow | FAIL — new upgrade not started; not verified live |
| Fog | FAIL — new upgrade not started; not verified live |
| Seasons | FAIL — new upgrade not started; not verified live |
| Rainbow | FAIL — new upgrade not started; not verified live |
| Bird Variants | FAIL — new upgrade not started; not verified live |
| Cats | FAIL — new upgrade not started; not verified live |
| Dogs | FAIL — new upgrade not started; not verified live |
| Aircraft | FAIL — new upgrade not started; not verified live |
| Balloons | FAIL — new upgrade not started; not verified live |
| Ambient Cars | FAIL — new upgrade not started; not verified live |
| Cycles | FAIL — new upgrade not started; not verified live |
| NPC Pedestrians | FAIL — new upgrade not started; not verified live |
| No Fake Online Counts | FAIL — new upgrade not started; not verified live |

## CONCERT

| Check | Result / evidence |
|---|---|
| Venue In Every Active City | FAIL — new upgrade not started; not verified live |
| Safe Placement | FAIL — new upgrade not started; not verified live |
| Not In Road | FAIL — new upgrade not started; not verified live |
| Not Blocking Buildings/Houses | FAIL — new upgrade not started; not verified live |
| Exterior Board | FAIL — new upgrade not started; not verified live |
| Interior | FAIL — new upgrade not started; not verified live |
| Stage | FAIL — new upgrade not started; not verified live |
| Screen Share | FAIL — new upgrade not started; not verified live |
| Lighting | FAIL — new upgrade not started; not verified live |
| Booking | FAIL — new upgrade not started; not verified live |
| PC Pricing | FAIL — new upgrade not started; not verified live |
| No Double Booking | FAIL — new upgrade not started; not verified live |
| Sponsor Panels | FAIL — new upgrade not started; not verified live |

## STRIPE / PC

| Check | Result / evidence |
|---|---|
| Stripe Integration | FAIL — new upgrade not started; not verified live |
| Webhook Signature | FAIL — new upgrade not started; not verified live |
| Idempotency | FAIL — new upgrade not started; not verified live |
| PC Packages | FAIL — new upgrade not started; not verified live |
| Wallet Credit | FAIL — new upgrade not started; not verified live |
| Failed Payment Safety | FAIL — new upgrade not started; not verified live |
| Refund Safety | FAIL — new upgrade not started; not verified live |

## RESPONSIVE

| Check | Result / evidence |
|---|---|
| Desktop | FAIL — new upgrade not started; not verified live |
| Mobile | FAIL — new upgrade not started; not verified live |
| Tablet | FAIL — new upgrade not started; not verified live |
| No Text Overlap | FAIL — new upgrade not started; not verified live |
| No Horizontal Overflow | FAIL — new upgrade not started; not verified live |
| First Tap | FAIL — new upgrade not started; not verified live |

## GLOBAL

| Check | Result / evidence |
|---|---|
| UK | FAIL — new upgrade not started; not verified live |
| Europe | FAIL — new upgrade not started; not verified live |
| Gulf | FAIL — new upgrade not started; not verified live |
| India | FAIL — new upgrade not started; not verified live |
| Asia | FAIL — new upgrade not started; not verified live |
| North America | FAIL — new upgrade not started; not verified live |
| Australia | FAIL — new upgrade not started; not verified live |

## REGRESSION

| Check | Result / evidence |
|---|---|
| Authentication | PASS — observed on existing fd0d116 production; new upgrade still not certified |
| Friends | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Chat | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Voice | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| LiveFace | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Events | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Screen Sharing | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Businesses | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Vehicles | PASS — rental/exit and single XP debit verified live on 5bf5bed |
| Bus | PASS — observed on existing fd0d116 production; new upgrade still not certified |
| Collectibles | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |
| Share-to-Unlock | FAIL — new upgrade not started; 5bf5bed regression CI passed, broad live certification not claimed |

## PRODUCTION

| Check | Result / evidence |
|---|---|
| Backend Tests | PASS — 245 tests in green 5bf5bed CI and Railway build; no backend change in c1cd3c1 |
| Frontend Tests | PASS — 46 unit tests, typecheck and 85 local browser assertions for c1cd3c1; full CI pending |
| Production Build | PASS — 5bf5bed Railway build and c1cd3c1 local production build |
| Migration | PASS — no schema change in repair; earlier deployed migration check passed |
| Railway Deployment | PASS — 5bf5bed deployed; c1cd3c1 deployment pending |
| Live Health Check | PASS — 5bf5bed returned HTTP 200/ready; existing release_ready=false is disclosed |
| Post-Deployment Verification | FAIL — exit repair verified live; subsequent balance-header follow-up not deployed |

## Required performance measurements

New performance profiling has not started, respecting the previous-release-first instruction. No before/after latency or FPS values were invented.

| Metric | Before | After |
|---|---|---|
| Cold landing → usable world | Not measured | Not measured |
| Warm landing → usable world | Not measured | Not measured |
| Login → usable world | Not measured | Not measured |
| City selection → local world usable | Not measured | Not measured |
| Refresh → usable world | Not measured | Not measured |
| Profile opening | Not measured | Not measured |
| Event-panel opening | Not measured | Not measured |
| Business-card opening | Not measured | Not measured |
| Average desktop FPS | Not measured | Not measured |
| Average tested-mobile FPS | Not measured | Not measured |
| Network requests during city switch | Not measured | Not measured |
| Largest/slowest blocking request | Not measured | Not measured |

Remaining broader performance bottlenecks: full page/world/FPS profiling has not started. Two isolated slow paths were measured and repaired: Whitehouse cold trail preparation 6,162.42 → 2.061ms (London 1,368.27 → 1.899ms); 127-destination catalog 128 → 2 SQL queries and 21.441 → 3.521ms locally. These are isolated function measurements, not end-to-end loading or FPS claims.

Separate previous-request movement evidence: local current repair build measured 22.549 m/s light walk and 70.749 m/s run; original local baseline was 7.502 / 23.485 m/s on the same test route. These are movement speeds, not page/world loading or FPS figures.

## Implementation report

| # | Topic | Result |
|---:|---|---|
| 1 | Previous work pending | Authenticated live acceptance of the deployed outdoor-speed/XP-mobility release. |
| 2 | Finished first | Recovered CI/build/deployment evidence; verified live sign-in, owned UK/international cities, XP ledger, bus reload/completion and e-bike purchase; reproduced and repaired rental exit. Remaining release gate is blocked. |
| 3 | Root causes of slowness | Rental exit waited on a full world fetch while vehicle input continued; cold UK trails regenerated synchronously; catalog read the same configuration 127 times. End-to-end profiling remains pending. |
| 4 | Performance changes | Removed post-exit world fetch; input pause/sequence reconciliation; prepared UK trail caches; reduced catalog from 128 to 2 queries. Follow-up reconciles acknowledged wallet balances. No overall loading/FPS claim. |
| 5 | Profile schema | Unchanged; new phase not started. |
| 6 | Social URL/privacy | Unchanged; new validation and server visibility work not started. |
| 7 | Avatar changes | None in this continuation; existing avatar preserved. |
| 8 | Weather provider/cache | No provider selected/configured; new phase not started. |
| 9 | Seasonal logic | No changes. |
| 10 | Bird variants | No new variants. |
| 11 | Cats/dogs | No architecture changes. |
| 12 | Ambient traffic | No changes. |
| 13 | NPC/user separation | No changes to presence or online counts; requested new ambient framework not implemented. |
| 14 | Concert placement | No new placement algorithm or venue created. |
| 15 | Overlap prevention | Not implemented/validated for the requested venues. |
| 16 | Booking locks | No new booking implementation; not validated for the requested concert economy. |
| 17 | Stripe architecture | Existing integration preserved. Production Stripe secret/webhook variable names are absent; wallet currently reports purchases unavailable. No live payment or test-card scenario executed. |
| 18 | Webhook idempotency | Unchanged; new PC purchase acceptance not tested. |
| 19 | PC ledger | Unchanged. Live XP mobility checks left 120 PC unchanged. |
| 20 | Sponsor/ad inventory | Unchanged; new phase not started. |
| 21 | Files changed | Product/test files listed below plus validation/evidence documents. |
| 22 | Migrations | None. |
| 23 | Cities tested | Live: Whitehouse, Paris, London (London on 5bf5bed). 5bf5bed CI: Milton Keynes, London, Birmingham, Madrid, Dubai, Mumbai, New York, Sydney. c1cd3c1 local balance checks: Milton Keynes at three widths. |
| 24 | Devices tested | Live cloud desktop browser, 1363px, map fallback. Local Chromium desktop 1440px and mobile/tablet emulation as recorded below. No physical devices or Safari/Edge certification. |
| 25 | Final production commit | 5bf5bedde87cc9a5a5eda596d724decc36af6f44 is live. Balance follow-up c1cd3c10f08784514978d20330b7abf9129717b5 awaits full CI. |
| 26 | Railway result | 5d94830c-380b-4795-a4ef-3b6247820777 SUCCESS at exact SHA 5bf5bed; live ready/HTTP200 confirmed. |
| 27 | Remaining blockers | GitHub hosted-runner acquisition/internal errors block remaining validation. Complete c1cd3c1 CI, exact-commit deployment and live header verification before new phases. GPU/physical-device and multiuser media evidence remains limited; Stripe production configuration is absent. |

### Product/test files

- `apps/consumer-web/components/useWorldMotion.ts`
- `apps/consumer-web/components/Mobility.tsx`
- `apps/consumer-web/app/page.tsx`
- `apps/consumer-web/lib/motionState.ts`
- `apps/consumer-web/lib/motionState.test.mjs`
- `scripts/tests/outdoor-xp.cjs`
- `scripts/tests/motion_profile_server.py`
- `scripts/prepare-world-trails.py`
- `apps/consumer-web/components/Transit.tsx`
- `backend/api/discovery.py`
- `backend/api/expansion.py`
- `backend/api/world_content.py`
- `backend/data/world-trails.json`
- `backend/tests/test_discovery.py`
- `backend/tests/test_geography.py`
- `backend/tests/test_world_motion_parity.py`

### Evidence

- `OUTDOOR_XP_VALIDATION_2026-10-01.md` (dated continuation and historical evidence)
- `evidence/outdoor-xp-2026-10-01/exit-repair-local-20261005.json`
- `evidence/outdoor-xp-2026-10-01/live-bus-20261005.jpg`
- `evidence/outdoor-xp-2026-10-01/ci-billing-blocked-20261005.jpg` (historical)
- `evidence/outdoor-xp-2026-10-01/deployment-20261005.json`
- `evidence/outdoor-xp-2026-10-01/balance-browser-20261005.json`
- `evidence/outdoor-xp-2026-10-01/balance-browser-390-20261005.json`
- `evidence/outdoor-xp-2026-10-01/balance-browser-820-20261005.json`
- `evidence/outdoor-xp-2026-10-01/mylilworlds-live-refresh-20261005.jpg`
- `evidence/outdoor-xp-2026-10-01/mylilworlds-live-wallet-20261005.jpg`
- `evidence/outdoor-xp-2026-10-01/mylilworlds-live-exit-fixed-20261005.jpg`
- `evidence/outdoor-xp-2026-10-01/mylilworlds-ci-runner-error-20261005.jpg`

The follow-up run subsequently cancelled 13 jobs before execution with the same hosted-runner acquisition annotation. Movement, Dubai and Sydney passed; the remaining 13 jobs were cancelled before execution. No failing test was hidden, disabled or marked passed. The retry of the two infrastructure-failed main jobs was also cancelled before execution.

### Resume sequence

Wait for GitHub runner recovery, complete c1cd3c1 CI run 37363973776 and the infrastructure-failed main retry, promote the exact green follow-up, deploy it explicitly to the existing Railway service, and verify the live header after one rental. Only then begin the new performance/profile/avatar/living-world/concert/Stripe phases in the requested order.

## Final local viewport results

| Viewport | Assertions passed | Scope |
|---|---:|---|
| 1440px desktop | 27 | PASS — local Chromium production build |
| 390px touch emulation | 29 | PASS — local, not physical device |
| 820px touch emulation | 29 | PASS — local, not physical device |

46 frontend unit tests, typecheck and local production build also passed for c1cd3c1. The deployed 5bf5bed passed all 16 CI jobs including projection checks and 170 outdoor/XP assertions. Latest follow-up CI cancelled 13 jobs before execution because hosted runners could not acquire them; local passes do not override the remaining gate.


## Resumption after 20:15 UTC — final result

Resumed the saved branch without application-code changes. Candidate run 37363973776 attempt 2 finished with **8 successful checks and 8 cancelled before execution**. Newly passing checks: infrastructure, Mumbai, Birmingham, layout, and outdoor/XP. Movement, Dubai and Sydney retain their earlier success. Outdoor/XP job 111959840705 passed **210 assertions**, including stale wallet response rejection, authoritative rental/bus header balances, single deductions, and delayed vehicle exits. GitHub's frontend annotation again states: “The job was not acquired by Runner of type hosted even after multiple attempts.” Billing is not the reported cause.

The deployed-main run 37362173653 attempt 3 finished with 14 successful checks, one provider-cancelled media check, and **one actual failing outdoor/XP performance check**. Job 111959972123 measured walking at 22.612279 m/s and running at 46.281217 m/s, failing the unchanged approximately-3x running assertion. Running acknowledgement median was 8ms, p95 549ms, maximum 1,203ms; maximum server-update gap 938.886ms. No browser long tasks were recorded. The profiler recorded a 324.25ms event-loop delay, SELECT calls of 328.96ms and 929.58ms, and a 1,200.67ms realtime-motion call. Database contention and host scheduling/I/O have not been distinguished; the root cause remains unconfirmed. No performance threshold was weakened.

A focused local desktop reproduction completed successfully with **27 assertions**: walking 22.594914 m/s, running 71.464052 m/s, acknowledgement medians 8ms/8ms and maxima 71ms/67ms, no browser long tasks. This passing reproduction and candidate run do not erase the intermittent failure. The execution connection disconnected after the local test completed; the results and checkpoint were preserved through GitHub.

Production remains `5bf5bedde87cc9a5a5eda596d724decc36af6f44`, Railway deployment `5d94830c-380b-4795-a4ef-3b6247820777`. The existing authenticated London session was inspected at the production URL and showed 240 XP / 120 PC. No deployment, migration, application restart, new service, data reset, or new feature phase was performed in this resumption. The stale-header fix is **not live**.

Next required work: complete the eight unexecuted CI checks, investigate the intermittent performance failure without hiding it, then promote/deploy the verified candidate and verify the live rental header. The prior-release gate remains incomplete. Evidence: `evidence/outdoor-xp-2026-10-01/resumed-ci-20261005.json`.
