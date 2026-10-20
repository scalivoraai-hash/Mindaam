# Validation recovery and requirements gap review — 2026-10-07

Status: IN PROGRESS. No new deployment or overall completion claim.

## Root cause and intended rule

ADR-0020 and shared/movement.json specify a 3x increase over the previous outdoor walk AND run speeds. They do not specify running at 3x walking. Equal-strength run/walk remains 1.875. Full-strength outdoor targets remain 37.5 and 70.3125 virtual metres/second; the browser's light walking input is 60%, giving 22.5 at steady speed.

The failed browser assertion divided mapped displacement by performance.now() elapsed time, then compared it with a historical wall-clock benchmark from another run. world.move integrates server time with a 0.3s cap and resets elapsed time to one 0.12s tick after gaps above 0.5s. A host/network/database delay therefore counts fully in the browser denominator but intentionally does not count fully as simulation time. The approximately-3x wall-clock assertion conflated a movement-law contract with end-to-end responsiveness. A previous failure logged run 46.281217m/s, 1,203ms maximum acknowledgement, and server delays; this repair does not claim to eliminate those delays.

Controlled-time reproduction invokes the actual database-backed world.move handler for both modes, with regular ticks and a sequence containing 0.35s/0.8s gaps. The old wall-time threshold fails in the delayed sequence even while every displacement is exactly 3x its old-multiplier counterpart. This is a deterministic reproduction of the faulty assertion methodology, not a claim that the unmodified browser suite randomly failed locally today.

## Small scoped repair

- backend/tests/test_outdoor_speed_contract.py: actual handler, controlled local clock, acceleration preserved, positive displacements, exact 3x comparison and 1.875 run/walk contract. Four parameterized cases. No production clock hook, speed change, database schema change, or relaxed tolerance.
- scripts/tests/outdoor-xp.cjs: execute the controlled-time contract as a mandatory gate; keep actual browser distance, elapsed speed, acknowledgement percentiles, server gaps and long-task diagnostics. Browser assertions still require real mapped movement, selected server mode, native touch movement, single XP debit, server-confirmed header balances, stale response rejection, safe exit and bus idempotency.
- Startup: start backend first, poll http://127.0.0.1:8000/api/health for HTTP 200 with a 60-second deadline and bounded requests, then start Next and check its proxy. Cleanup now covers startup failures too.
- Existing CI invokes this same script; no workflow job is skipped or disabled. Existing production application code remains unchanged in this repair. The lockfile updates only sharp/native dependencies to 0.35.5 (libvips 1.3.4) and source-map-js to 1.2.2 for newly reported high-severity advisories; the existing PostCSS override is preserved. Advisory sources: https://github.com/advisories/GHSA-wq5f-xc86-pv6w and https://github.com/advisories/GHSA-68fv-2mgg-jv7q.

Before:
```js
results.improvement.run = run.mps / before.speeds[1].mps;
check('measured run approximately 3x', results.improvement.run >= 2.8);
```
After (actual handler under equal controlled tick sequences):
```python
previous = integrate(1)
upgraded = integrate(3)
assert all(distance > 0 for distance in previous)
assert upgraded == pytest.approx([distance * 3 for distance in previous])
```

## Validation

- Backend: 249 passed (SQLite local/test; PostgreSQL CI still required).
- Frontend: 46 passed.
- Projection: 40 passed.
- Typecheck and Next production build: passed. Local SQLite migration upgrade and consistency check passed; PostgreSQL remains a CI gate.
- Five full outdoor/XP repetitions: all passed, 29 browser checks each (145 total), plus four controlled-time contract cases in every run. No startup proxy errors in any of the five frontend logs. Evidence: evidence/outdoor-xp-2026-10-01/deterministic-five-runs-20261007.json.
- Layout, world, lighting, movement, infrastructure and PostgreSQL/migrations: current repair's CI pending. Docker and Terraform are not installed in this execution workspace; do not infer passes.
- Production: still 5bf5bed / Railway deployment 5d94830c-380b-4795-a4ef-3b6247820777. Header fix c1cd3c1 remains on the existing release branch until the combined candidate is verified and deployed.

## Gap review against the full supplied upgrade

This maps all feature groups, not just the examples in the latest message. Existing code is not proof of production acceptance. The detailed original acceptance matrix remains in LIVING_WORLD_UPGRADE_2026-10-05.md. The prior-release gate must close before new feature implementation, as requested.

| Requirement group | Existing implementation/evidence | Remaining gap / production acceptance |
|---|---|---|
| Previous release, XP car/bike/bus rentals | Existing APIs/UI and immutable ledger; earlier production rental/bus verification | Header reconciliation undeployed; finish current CI repair and live header verification |
| Performance measurement and first tap | Existing movement timing, sequence guards, world loading component, cache/query repairs | Full cold/warm/login/switch/panel/FPS/request before-after measurements; coherent spawn reveal and all touched first-tap checks |
| Deduplication, prefetch, asset caches, workers | Existing request serialization and geographic cache | Audit all named paths, canvas mount count, asset reuse and heavy work; no global PASS yet |
| Own/public profile and stats | ProfileEditor and PUT /me/profile exist with identity/location privacy | Requested photo, bio, display name, comprehensive stats, favourite world and public profile integration incomplete |
| Social links and per-link privacy | No such fields in ProfileFields | Eight platforms, HTTPS/domain validation, server Everyone/Friends/Only Me enforcement and two-user tests |
| Appropriate profile actions/moderation | Existing social/block/report and media engines | Connect public-profile actions with access/privacy checks and reported-profile/social abuse moderation |
| Human avatar customisation | Existing procedural human, colour controls, short/long/cap styles and distance LOD | Full body/face/hair/clothing/shoes/accessory catalogue, persistence/peer updates, animations and admin asset compatibility |
| Weather and seasons | Existing static sky/fog/light | Shared dynamic climate/hemisphere/date-aware engine, weather cache, rain/snow/fog/rainbow/day-night and admin controls |
| Birds, pets, aircraft, balloons | Requested ambient systems not found in current world implementation | Species, safe paths, density, LOD/culling and quality budgets across active cities |
| Ambient cars/cycles/pedestrians | Existing explicitly labelled Neighbour NPCs follow road segments; gameplay transport exists | Pavement-safe pedestrians, ambient road vehicles/cycles separate from rentable vehicles; verified online-count separation |
| Premium concert exterior and safe location | Existing auditorium/event scene and civic/world rendering | Shared venue anchors, road/building/entrance/accessibility validation, safe entertainment-hub fallback, exterior live/upcoming/available board in every active destination |
| Interior and existing event/media engine | Auditorium, stage, screen-sharing/host tools already exist | Integrate premium venue exterior/interior/sponsor assets and verify all existing media/moderation/gift capabilities |
| Concert/auditorium rental UI | VenueReservation imported by Events through EventHostTools | Public discoverability and booking-first flow; current UI is event-host reservation flow |
| PC booking economics | venue_rentals.py locks destination/user, checks overlap, unique request, existing ledger | Existing durations 1/3/6/12/24 differ from requested 1/2/4/8/day; purchased-only Credits gate differs from latest PC requirement; states, notice/opening/cancellation/refund policies and admin controls incomplete |
| Stripe PC purchase | Existing /payments/checkout and signed /payments/webhook, PaymentEvent deduplication, amount checks and ledger credit | Railway variable-name inspection on October 7 confirmed STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are absent; provider sandbox success/decline/3DS/network/duplicate/refund journeys; package currency/bonus/admin requirements and refund reconciliation incomplete |
| Closed-loop ledger | Existing immutable Credits/XP ledger | Extend existing transaction taxonomy as required; preserve history; no cashout |
| Advertising/sponsorship | Existing merchant campaigns and digital displays | Venue inventory/priority, legitimate sponsors, host/admin controls and safe CTA/logo integration |
| Super Admin | Existing operational, pricing and catalogue tools | Add only missing profile/environment/venue/Stripe/avatar settings; never expose secrets |
| Global and future-city inheritance | Shared world/event/transport components and destination catalogues | Ensure each new feature uses shared configuration; validate all requested climate regions and every active venue anchor |
| Responsive and first tap | Existing responsive UI and emulated-browser checks | New flows on desktop/mobile/tablet, overlap/overflow checks, physical Safari/Android testing where available |
| Regression, migrations, deployment/live | Existing test suites, migration history, Railway service | Full green candidate suite, security/migration checks, safe additive migrations where needed, exact-SHA deployment and actual live acceptance for every feature |

No new project, repository, database, service, second event engine, second wallet or fake production users/payments has been introduced.

Security verification after targeted lockfile changes: npm audit reports zero vulnerabilities; pip-audit reports no known vulnerabilities. No package manifest, Next version, CI tolerance or production movement constants were changed.
