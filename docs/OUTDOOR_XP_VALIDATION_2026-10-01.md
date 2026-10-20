# MyLilWorlds — outdoor movement and XP mobility validation

Release candidate: `fd0d1163d7b316829ecf7189d612cd7604c3199e`.

Historical 2026-10-01 checkpoint (superseded by the dated continuation below): implementation and local checks were already complete when recovery started. Exact-commit release-branch CI run 36884435751 completed successfully with all 16/16 jobs passing. Main-branch CI run 36886472154 also passed 16/16. Railway deployment and public live checks passed; authenticated live movement/XP acceptance remains blocked by the missing authorized existing test account. No implementation or assertion changes were made during recovery.

## Deployed repair and live balance-display follow-up — 2026-10-05

Commit `5bf5bedde87cc9a5a5eda596d724decc36af6f44` passed all 16 jobs in CI run 37360651180, including 170 outdoor/XP browser assertions and 245 backend tests. Railway deployment `5d94830c-380b-4795-a4ef-3b6247820777` built this exact SHA and reached SUCCESS. Runtime startup completed; `/api/health` returned HTTP 200 with `status=ready`. The existing `environment=staging` and `release_ready=false` response remains unchanged and is not a public-readiness certification.

Authenticated live verification loaded London with its mapped roads, businesses, collectibles, buses and realtime connection. A City Bike rental charged 10 XP once (250 → 240); PC remained 120. One click on Exit vehicle returned to WALK, with no stale No active vehicle error. Wallet history confirmed the single debit. The same check caught a separate display defect: the header remained at 250 while the wallet correctly showed 240.

The follow-up uses balances already returned by the successful rental/boarding endpoint, rather than relying on another immediate wallet GET. A revision guard prevents a wallet read started before the mutation from overwriting its acknowledged balance. No frontend subtraction or fabricated completion is used. Rental and bus header assertions are added, including a deliberately delayed old wallet response and a check that rentals do not issue a redundant wallet read. The local production-build browser suite passed 27 assertions, including the new delayed-wallet and header checks; 46 frontend tests, typecheck and build passed. Evidence: `evidence/outdoor-xp-2026-10-01/balance-browser-20261005.json`. This follow-up requires CI, deployment and live verification before previous-release closure.

## Snapshot catalog query repair — 2026-10-05

The test-only server profiler measured roughly 292 SQL statements per world snapshot. An isolated catalog call for 127 destinations performed 128 queries (127 repeated reads of `city_demand`), taking 21.441ms locally. Reading the default once per catalog reduces this to two queries / 3.521ms in the same isolated setup. There is no cross-request config cache: changed admin defaults and per-city overrides remain current. A bounded-query regression verifies both properties.

The production-build desktop browser regression passed all 22 assertions after this repair: light walk 22.585m/s, run 71.274m/s, movement acknowledgement median 8ms, maximum 66/67ms respectively, with no observed browser long tasks during either sample. These are disposable local QA measurements, not production or physical-device benchmarks. Evidence: `evidence/outdoor-xp-2026-10-01/catalog-browser-20261005.json`.

CI run 37359663925 also exposed a timing-dependent geography test defect: it moved the player and then spawned a collectible at the old entry coordinates. With faster walking, claiming it correctly returned “Move closer”. The test now places the item at the movement response's authoritative location. No claim radius, movement speed, or browser acceptance threshold changed. Nine discovery/geography tests passed locally. Full CI and live verification remain required before deployment.

## Billing recovery and cold trail caches — 2026-10-05

GitHub billing eligibility was restored by the owner and run 37350382930 was rerun. The jobs now execute. The outdoor-XP job failed the unchanged approximate-3x walking gate: 16.612 m/s, with a 1,401ms maximum acknowledgement and 1,773ms server-update gap; running measured 70.732 m/s. The failure is retained. No threshold, route or input strength was changed.

Investigation found a separate concrete synchronous cold-path problem: eight UK trail cache entries had version 2, while the loader requires 3, and another nine UK maps had no prepared entry. The preparation script deliberately skipped the UK even though hourly rotations use the same loader. A fresh-process `prepared_points(city,48)` measurement took 6,162.42ms for Whitehouse and 1,368.27ms for London. Cache preparation now includes all installed cities; Nottingham records completed preparation at 96 requested points even though its safe mapped area yields only 14. This prevents falsely treating a complete small-city result as a missing cache.

After preparation, fresh-process calls measured 2.061ms / 1.899ms respectively (Nottingham 1.838ms). These are isolated function timings, not world-ready times or FPS. All 17 UK runtime point sequences were regenerated and compared with the cache's first 48: identical, including Nottingham's complete 14-point sequence. Authored database collectibles, claims and ledgers were not modified. The existing provisioning/idempotency tests remain passing.

43 affected backend tests passed, including a new test that forbids request-time trail generation for every installed world and validates all returned points against roads/buildings/private areas. Browser diagnostics now record long tasks during measured movement; the intermittent CI walking delay is not declared resolved solely from the cache benchmark. The candidate must pass the unchanged browser gate and full CI, then deploy and verify live. New living-world/profile/concert features have not started.

Evidence: `evidence/outdoor-xp-2026-10-01/cold-trail-cache-20261005.json`.

## Authenticated continuation — 2026-10-05

The earlier missing-account blocker below is historical. Secure browser sign-in to the existing user-authorized account now succeeds. Live Whitehouse, Paris and London loaded with the authenticated connection and existing map fallback; walk/run controls changed position. Live numeric movement speeds and physical-device/GPU performance were not measured.

A real Whitehouse-to-London bus ticket deducted 20 XP once (285 → 265 XP); PC remained 120. A page reload restored the same paid journey and balance. The complete journey and London disembarkation succeeded. Wallet history contained one bus-ticket debit, plus the previously tested car and e-bike debits. Evidence: `evidence/outdoor-xp-2026-10-01/live-bus-20261005.jpg`.

A subsequent London e-bike rental deducted 15 XP once (265 → 250 XP), with PC still 120. Exiting ended the lease but displayed `No active vehicle`. This is a reproduced previous-release defect, so the new living-world/profile/concert upgrade has **not started**.

The repair pauses movement synchronously during rental exit, clears unsent input, rejects superseded HTTP/WebSocket replies by input sequence, and applies the endpoint's authoritative safe walking position without another world fetch. Both rental exit controls use this same transition. Genuine current movement errors and failed exits remain visible. Server authorization, prices, balances, movement ceilings and migrations are unchanged.

Local checks: typecheck, 46 frontend unit tests, 40 camera projection checks and production build passed. The existing outdoor-XP browser suite now delays the exit response and asserts immediate feedback, one exit request and no stale movement error. Local browser runs passed 22 desktop + 24 mobile + 24 tablet assertions (70 total), including both delayed rental exits, native touch and unchanged speed/XP/bus assertions. Exact-commit CI, deployment and repaired live acceptance are still pending at this checkpoint. The previous-release gate is **FAIL / pending repair verification**, not complete.

### CI blocker confirmed after secure GitHub sign-in

Repair commit: `106d273e3e85f634fd0ad4c99c5ec5471731d168` on the existing `fix/outdoor-speed-xp-mobility-20261001` branch. Validation run `37350382930` failed before execution: all 16 jobs were prevented from starting. The authenticated run annotations state that recent account payments failed or the spending limit needs increasing. This is a GitHub account billing/spending blocker, not a failing test assertion. No tests were skipped or weakened and no alternate release gate was substituted.

Main and Railway remain at `fd0d1163d7b316829ecf7189d612cd7604c3199e`; deployment `c5b52edb-ad54-42ba-a2ea-3683c1e1b17d` remains SUCCESS with no staged changes. The exit repair is not deployed and must not be marked live. After the account owner restores Actions eligibility, rerun the failed jobs for the repair commit, resolve any actual failures, promote the exact green commit, build/deploy it on the existing service, and verify live rental exit before starting the new upgrade. No schema changes are needed.

Evidence: [blocked backend job](https://github.com/sainsabu41-cmyk/pulseworld/actions/runs/37350382930/job/111899458556), `evidence/outdoor-xp-2026-10-01/ci-billing-blocked-20261005.jpg`.

## Root cause and effective movement

The previous production release already serialized fallback polling. Its outdoor speed still used the Preview baseline: 12.5 m/s walk and 23.4375 m/s run. Those limits were functioning as configured but did not meet the newly requested fast-exploration pace. The shared outdoor-only multiplier now sets full-input caps to 37.5/70.3125 m/s, with matching acceleration scaling. Input timing, normalization, server safety caps, reconciliation, collision stepping and indoor/Preview movement are unchanged.

Both before and after measurements ran against local production builds with disposable test data; the before build matched the then-deployed `6ae7fac` source. They were not authenticated live-production measurements. Measured on the same mapped Whitehouse road, starting at (641.534, 100.767), until crossing the same 180-metre route threshold. Walking uses identical 60% input in both runs; sustained full input deliberately transitions to running. Distances vary slightly because the threshold is crossed on a discrete authoritative update. These are browser-observed displacements and elapsed times, not constant-only tests.

| Mode | Before time | After time | Effective speed | Improvement |
|---|---:|---:|---:|---:|
| authenticated light walk | 24.006 s | 8.011 s | 7.502 → 22.534 m/s | 3.004× |
| authenticated explicit run | 7.752 s | 2.588 s | 23.485 → 70.186 m/s | 2.989× |

The after run above uses the 820-pixel tablet viewport. Desktop and 390-pixel mobile measurements are also recorded in the evidence directory. Native tablet touch input measured 21.679 m/s walking at 60% strength and 72.561 m/s running over short intervals. The short release interval may include one final acknowledged movement step.

Measured rental movement on mapped ground: bike 84 m/s; car 120 m/s, using displacement and the timestamps of the same authoritative acknowledgements. Vehicle acceleration, braking, steering, ownership, spawning and rental lifecycle code remain unchanged; the existing speed-floor helper raises acceleration with the new ceilings. The approved hierarchy calibration also sets e-bike to 93 m/s. Unchanged braking rates mean longer stopping distances at higher speeds. Bus speed, schedules, routes, boarding and access rules are unchanged.

The local regression run passed 27 checks, including keyboard walk/held-run/release, Preview, remote movement, real WebGL auditorium camera checks, and cold fallback polling. Delayed entry took 4.327 s; the first fallback poll began 7.663 s after entry completed; maximum concurrent world requests was one. A first CI vehicle test used mismatched host-time and snapshot intervals and was corrected to pair acknowledgement positions/timestamps. A separate CI cold-start walk sample reached only 2.37× after a 1.413-second acknowledgement delay; it remains recorded as a failed run, not a PASS. The current release must pass the unchanged effective-speed gate.

## XP mobility and data safety

Configured numeric prices are retained 1:1 and interpreted as XP for new car/bike/e-bike rentals and bus tickets. Current defaults are car 25 XP, bike 10 XP, e-bike 15 XP and bus 20 XP; admin-configured prices and existing included-access entitlements remain authoritative.

`mobility_payments.py` selects XP only for these actions. Checkout requires an explicit matching currency quote, so a stale page showing Credits cannot silently charge XP. The server validates eligibility, availability, fare/price and balance under the existing user-row lock, then writes the debit and rental/ticket in one transaction. Ledger kinds are `car_rental_xp`, `bike_rental_xp` and `bus_ticket_xp`. Rental snapshots carry the new payment currency, and bus audit records identify XP.

Same-ID retries return the prior purchase. Another rental request cannot charge while a lease is active. Bus user/vehicle uniqueness also prevents a different request UUID from purchasing the same ticket twice. Existing ledger uniqueness and nonnegative-balance constraints remain. Insufficient XP returns the exact shortfall, with no Credit fallback; UI offers a return to exploration.

No schema migration or price/balance conversion is needed. Historical ledger rows, old rentals/tickets and balances are not rewritten. Historical Credit rental retries and remaining scooter Credit purchases pass regression tests. Other Credit uses—including gifts, venues and paid features—retain their existing code paths.

## Files changed

Product files: `shared/movement.json`; `backend/api/world.py`, `mobility.py`, `transit.py`, new `mobility_payments.py`; `apps/consumer-web/components/Mobility.tsx`, `Transit.tsx`, `CityAssets.ts`, `PlatformCatalogues.tsx`; and the transport fare labels in `apps/consumer-web/app/super-admin/page.tsx`.

Supporting changes add XP/quote/history/concurrency tests, update affected rental/bus fixtures and assertions, add `scripts/tests/outdoor-xp.cjs`, improve timestamp pairing in the vehicle measurement, extend the existing CI presentation matrix, and document ADR-0020 and measurement evidence. No Event, Auditorium, Chat, Voice, LiveFace, screen-sharing, Friend, Gift, business-card, advertising, scoreboard, collectible, access, Share-to-Unlock or authentication implementation was edited.

## Validation and production status

- Local backend suite: 240 tests passed, followed by all seven targeted XP tests, including two added history/remaining-Credit cases (243 total distinct tests including the additional scoped admin-limit test).
- Frontend tests: 44 passed; 40 camera-relative projection checks passed; production build passed.
- Local movement/camera/polling regression: 27 checks passed.
- Local browser: 390-pixel mobile and 820-pixel tablet XP pricing/checkout/retry checks passed; native touch movement passed at 820 pixels. Browser viewport emulation is not physical-device certification.
- Exact-commit release-branch CI: PASS, run 36884435751, 16/16 jobs at commit fd0d1163d7b316829ecf7189d612cd7604c3199e. Fresh-session outdoor XP job 110444016623 passed all eight scenarios: 1440/390/820-pixel Whitehouse and London/Madrid/Dubai/Mumbai/New York. Movement regression job 110444016484 passed, including server reconciliation, keyboard release and non-overlapping fallback requests. The earlier socket timeout did not recur in this diagnostic run; its intermittent root cause is not established by a successful run. No application behavior, assertions or test thresholds were changed during recovery.
- Local five-region browser matrix: London, Madrid, Dubai, Mumbai and New York each passed all 12 movement, XP pricing, single-debit, unchanged-Credit, bus retry and layout checks. Release-branch CI now also passes all five regional scenarios; main-branch rerun also passed 16/16.
- Existing Railway deployment: PASS — c5b52edb-ad54-42ba-a2ea-3683c1e1b17d, exact commit fd0d1163d7b316829ecf7189d612cd7604c3199e, SUCCESS at 2026-10-01T16:05:31.581Z. The actual image passed 243 backend tests in 382.60 seconds and its frontend production build. No new service, provider or database changes.
- Authenticated production verification: blocked pending identification/authorization of existing test accounts. A prior automatic approval review rejected production sign-in because no specific authorized account was provided. No credentials were submitted and no synthetic production users were created.


## Requested acceptance matrix

Movement, XP and regression PASS results below describe local/CI production-build testing. Mobile/tablet are Chromium viewport/touch emulation, not physical-device certification. Live authenticated acceptance is listed separately and is not claimed.

| MOVEMENT | Result |
|---|---|
| Normal-World Walk Speed | PASS |
| Normal-World Run Speed | PASS |
| At Least ~3X Effective Improvement | PASS — measured local before/after route |
| UK Cities | PASS |
| International Cities | PASS |
| Desktop | PASS — automated Chromium |
| Mobile | PASS — 390-pixel browser emulation |
| Tablet | PASS — 820-pixel browser/touch emulation |

| XP MOBILITY | Result |
|---|---|
| Car Uses XP | PASS |
| Bike Uses XP | PASS — including e-bike |
| Bus Uses XP | PASS |
| Pulse Credits Not Used For Mobility | PASS — requested car/bike/bus scope |
| XP Deduction Atomic | PASS |
| No Negative XP | PASS |
| No Duplicate Deduction | PASS |
| Insufficient XP Handling | PASS |

| REGRESSION | Result |
|---|---|
| Vehicle Logic Preserved | PASS — approved speed ceilings excepted |
| Bus Logic Preserved | PASS |
| Pulse Credits Preserved Elsewhere | PASS |
| Historical Data Preserved | PASS |
| Other Features Unchanged | PASS — scoped source review and regression suite |

| PRODUCTION | Result |
|---|---|
| Tests | PASS — release-branch and main-branch each 16/16 |
| Production Build | PASS |
| Migration If Required | PASS — no new migration; Alembic check passes |
| Railway Deployment | PASS — exact candidate, existing service |
| Live Health Check | PASS — HTTP 200, status ready; release_ready remains false |
| Post-Deployment Verification | FAIL / BLOCKED — authenticated live checks require an identified existing test account |

## Recovery continuation — 2026-10-01

The remote candidate was five commits ahead of production main, with no divergence. The existing local checkout retained an older git HEAD and accumulated working files; blob comparison confirmed all candidate source files matched except the local web package manifest. Existing local changes were preserved, and deployment promotion used the exact tested remote commit. Main was fast-forwarded to fd0d116; no migration files changed.

The release-branch outdoor browser measured Whitehouse light walk at 22.582 / 22.788 / 22.659 m/s and run at 71.029 / 73.332 / 73.336 m/s for desktop/mobile/tablet. The route sampling includes final acknowledged displacement; these are effective measured results, not revised configured caps. Configured outdoor full-input limits remain 37.5 m/s walk and 70.3125 m/s run. The existing approximate-3x gate passed unchanged. Native-touch walk and run passed at both 390 and 820 pixels.

All eight scenarios passed car/bike XP labels and single-debit checkout, bus XP fare/checkout and retry idempotency, unchanged Credits, layout checks and absence of browser errors. Shared backend handlers and UI components apply the policy to all applicable worlds; this does not claim every city/device was individually tested.

Main promotion automatically started run 36886472154. Automatic approval review rejected the first Railway redeploy attempt while that main-branch run was still in progress. No deployment was triggered by that rejected call. The remaining gate will be awaited without cancelling, skipping or bypassing tests.

Main CI 36886472154 completed SUCCESS on the same exact commit, including 106 outdoor-XP browser assertions. Desktop measured 22.510 m/s light walk and 70.233 m/s run; mobile 22.541/68.438; tablet 22.532/69.123. All original approximate-3x gates, native-touch checks, checkout assertions and layout assertions passed unchanged.

After both CI gates passed, the generic Railway redeploy action created 26f1b1cc-2572-4bb4-9001-3574cf8f6d12 from the OLD 6ae7fac snapshot. The commit mismatch was caught by deployment metadata, not mistaken for a release. An explicit-SHA deployment was then triggered on the same service: c5b52edb-ad54-42ba-a2ea-3683c1e1b17d, commit fd0d1163d7b316829ecf7189d612cd7604c3199e. The build and public live verification subsequently passed; authenticated live acceptance remains blocked as described below.

## Production result and remaining acceptance

Railway deployment c5b52edb-ad54-42ba-a2ea-3683c1e1b17d reached SUCCESS for fd0d1163d7b316829ecf7189d612cd7604c3199e at 2026-10-01T16:05:31.581Z. Both old-commit deployments are REMOVED. The image independently passed 243 backend tests, the Next.js production build and its health check. Runtime logs show application startup complete and /ready and /api/health returning HTTP 200.

An external HTTPS request after deployment returned HTTP 200 with `{"status":"ready","environment":"staging","release_ready":false}`. This is the existing Railway production environment, but the application retains its pre-existing staging label and false release-readiness flag. Neither was changed or hidden.

A fresh live browser reload loaded the landing/sign-in form and public world catalogue. Whitehouse (UK) and Madrid (international) loaded; the city selector switched the mapped district and collectibles successfully. Both reported data-ready=true, with no horizontal overflow at a 1363-pixel desktop viewport. This cloud browser has WebGL disabled and used the existing map fallback; console WebGL creation errors therefore remain a stated environment limitation, not a clean GPU certification. No live mobile/tablet, successful login, authenticated walk/run or XP purchase is claimed.

Remaining blocker: the user must identify/authorize an existing production test account for sign-in and controlled XP rental/bus checks. Prior automatic review rejected an unspecified-account sign-in. No production account, XP balance or transaction was fabricated. Full live acceptance remains FAIL / BLOCKED. CI desktop/mobile/tablet and cross-city passes do not substitute for those production checks.

## Hosted-runner checkpoint

Balance follow-up c1cd3c1 passed 27 desktop + 29 mobile + 29 tablet browser assertions locally (85 total), 46 frontend unit tests, typecheck and production build. GitHub run 37363973776 cancelled 13 jobs before execution with “The job was not acquired by Runner of type hosted even after multiple attempts”. Movement, Dubai and Sydney passed; the remaining 13 jobs were cancelled before execution. The previous main run also suffered runner acquisition/internal server errors, and only its two failed infrastructure jobs were retried; both were cancelled again before execution. This is a provider execution blocker, not an application test pass. Follow-up deployment remains pending.
