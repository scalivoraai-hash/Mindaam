# MyLilWorlds movement, rentals, world content and mobile HUD validation

Target: existing `sainsabu41-cmyk/pulseworld` and `pulseworld-production.up.railway.app`.
Base release: `b7662ec2e47054a9d19de5f29c38ea6eacc0dec9`.

**Automated gates pass. Full live/device acceptance is not certified.** PASS below is limited to its stated evidence. NOT VERIFIED is an unmet acceptance gate, not a claim that the feature is defective.

## Automated release gates

| Gate | Result | Evidence |
|---|---|---|
| Full backend regression | PASS | 217 tests, 146.80 seconds; two dependency deprecation warnings |
| Frontend logic | PASS | 16 tests |
| Camera-relative input | PASS | 40 projected-direction/diagonal checks |
| Production build and TypeScript | PASS | Next production build; all 12 static pages generated |
| Fresh additive migration | PASS | Alembic upgrade to fm25_world_movement |
| Authored content preservation | PASS | 132 existing items retained with identical IDs, coordinates and types |
| International trail provisioning | PASS | 48 items in each of 28 international worlds; 1,344 total |
| Idempotent startup | PASS | Repeated provisioning did not duplicate content; zero wallet transactions created |
| Startup/rental provisioning | PASS | 1,061 rental identities; complete startup plus repeated provisioning in 43.18 seconds on local SQLite |

## Movement

| Requirement | Automated result | Live/device result |
|---|---|---|
| Input delivery and release/stop | PASS — real local socket exchange, including a coalesced press/release pair | Follow-up production retest NOT VERIFIED; see live findings below |
| Random movement freezing completely eliminated | Not certifiable from automated tests alone | NOT VERIFIED |
| Smooth walk/run and animation match | Build checked; actual-displacement interpolation implemented | NOT VERIFIED |
| Run faster than walk / bounded acceleration | PASS — server-clock and diagonal-cap tests | NOT VERIFIED |
| Stale city/interior input rejected | PASS — HTTP and socket checks | NOT VERIFIED |
| Boundary/collision movement | PASS — installed districts and collision sweep | NOT VERIFIED |
| Bounded stuck recovery | PASS — invalid position only, cooldown and no rental bypass | NOT VERIFIED |
| Mobile first touch / multitouch / release | Logic implemented; build checked | NOT VERIFIED |
| Two-user chat after socket change | PASS — local two-client text exchange and existing regressions | NOT VERIFIED on production |

## Vehicles

| Requirement | Result and scope |
|---|---|
| Bike faster than run; car faster than bike | PASS — configured maxima and authoritative acceleration tests |
| Bus faster than pedestrian/vehicle | PASS — existing transit speed regression |
| Acceleration, braking, right steering | PASS — authenticated rental setup and server kinematics |
| Parked bike and car outside bay | PASS — stable street assets, rental endpoint and exclusivity tests |
| Formal rental bay | PASS — existing lease/policy tests |
| Wallet debit once / no double rental | PASS — retry/concurrency and second-user tests |
| Safe exit / end rental / availability restored | PASS — authoritative lease and traversability assertions |
| Real-device camera/vehicle smoothness | NOT VERIFIED |

## International content

The following all PASS prepared-position checks: 48 unique points, reachable through the existing swept path search, off driving lanes, not inside buildings, water or mapped private areas, spread more than 50 metres, with approximately five metres minimum item spacing.

| Destinations | Result |
|---|---|
| Paris, Berlin, Amsterdam, Madrid, Barcelona, Rome, Milan, Dublin | PASS — automated |
| New York, Los Angeles, Miami, Toronto, Vancouver | PASS — automated |
| Dubai, Abu Dhabi, Riyadh, Jeddah, Doha | PASS — automated |
| Mumbai, Bengaluru, Kochi, Singapore, Tokyo, Seoul, Bangkok, Shanghai | PASS — automated |
| Sydney, Melbourne | PASS — automated |
| Existing UK items, reward ledger, duplicate-claim protection | PASS — preservation and claim regression |
| Future ACTIVE world provisioning | PASS — shared activation/provisioning path and idempotency tests |
| Live pickup journey in all required cities | NOT VERIFIED |
| Repeat/respawn reward acceptance | NOT IMPLEMENTED as a new policy: existing once-per-user claims preserved; no repeat grants introduced |

## Mobile/tablet presentation

Implemented: compact status/location, one Quick Actions control, Camera panel, collapsed Rentals/Transit/Daily Drop/Rankings, physical-world advertising action, contextual rentals, safe exits, six-item bottom navigation, safe-area spacing, Hide/Show Controls, business bottom sheets, long-name wrapping and input ownership/cancellation.

Actual small/standard/large phone, tablet portrait/landscape, desktop visual bounds, first-tap response, overlap, GPU performance and media/HUD interaction are **NOT VERIFIED**. A local fixture using actual components was built, but the supported cloud browser blocked both local HTTP and file previews. No alternate browser or policy workaround was used. TypeScript/build success is not reported as responsive visual acceptance.

## Access and regression

Four total user-chosen Starter Worlds across UK/international, four-share permanent unlocks, preserved entitlements, separate future-city demand, authentication/CSRF, profile/privacy, friendship/blocking, chat/media/group authorization, events/stage, wallet/credits, gifts, missions/claims, businesses/buildings, transport, advertising and portal permissions remain covered by the full automated suite. Real provider delivery, multiple physical users/devices and broader production readiness are still separate acceptance gates.

## Deployment and live acceptance

Application release `d2a3c2c1e6f9ac8e45999826d8cbe7e167661146` is deployed to the existing Railway service in deployment `85cdee33-396b-4844-a710-be9b7be14dab` (SUCCESS). No service, database or authentication replacement was created. Public readiness returned ready; the existing deployment still reports staging and `release_ready: false`. This report does not override those production-readiness gates.

Authenticated live acceptance used the existing account through secure browser sign-in. No credentials, cookies or tokens were read or stored in the report. Evidence:

| Live check | Result and precise scope |
|---|---|
| Existing sign-in | PASS — secure sign-in and authenticated Explorer loaded |
| Existing entitlements | PASS — four prior Starter Worlds retained; legitimate additional owned worlds retained |
| Active catalogue | PASS — 45 active worlds, including all 28 international launch destinations; future request destinations separate |
| Paris locked state | PASS — normal locked active-world card, 0 / 4 shares, no demand target |
| Share progression | PASS — Copy Link, WhatsApp handoff, Facebook handoff and Instagram clipboard fallback advanced 1 / 4 through 4 / 4 |
| External social delivery | NOT VERIFIED — composers/fallbacks opened; no message or post was sent, and no external delivery claim is made |
| Fourth action unlock | PASS — permanent Paris entitlement and Enter Paris action displayed |
| International world entry | PASS — owned Paris loaded sourced streets, fruit/gem markers, mission and realtime connection |
| Live fruit reward | PASS — normal nearby pickup increased XP by five; Credit balance unchanged |
| Refresh persistence | PASS — Paris remained YOUR WORLD after refresh; reward balance retained and no second pickup grant observed |
| Logout/login persistence | NOT VERIFIED — logout completed, but subsequent secure browser sign-in request was declined; no alternate authentication method attempted |
| New-account four-choice flow | NOT VERIFIED live — existing account used, no fabricated production account or entitlement reset |
| Live public geometry | PASS — Paris: 3,785 mapped features, 34 street vehicle records / 9 rentable; Tokyo: 697 mapped features, 41 records / 19 rentable. These are content counts, not user counts |
| Runtime errors | No error entries in the inspected release log window; not a claim that all runtime paths are error-free |

Live quick-key testing exposed a press/release edge case: the single pending-input slot could collapse a complete short tap into its release. The follow-up patch preserves a bounded two-input pair; a deterministic regression reproduces the previously lost pair and passes with the correction. All 217 backend tests and a fresh production frontend build passed after this fix. It also loads the existing wallet data before world entry so the home header no longer starts with misleading zero balances. The final follow-up is deployed as recorded below. Authenticated retesting after logout remains unavailable without renewed sign-in.

The supported cloud browser used the existing map fallback because GPU rendering was unavailable. This does not certify 3D movement, animation, vehicle camera, touch input or physical phone/tablet performance.

Screenshot: [Paris unlock confirmation](validation/paris-unlocked-live.jpg).


## Final deployed revision

- Application commit: `fa327ca4bdf9cd850e87775ffb78d8cc89ea52ab`.
- Existing Railway deployment: `395edafb-336a-45ba-a09c-ff6bab7aed61` — **SUCCESS**.
- Railway image independently ran **217 backend tests, all passed**, in 211.55 seconds (one dependency deprecation warning).
- Runtime readiness returned HTTP 200. Startup completed and authenticated WebSocket connections were accepted in the inspected deployment log window; these are operational observations, not a substitute for a controlled multi-user test.
- Post-deployment public checks returned HTTP 200 for health, destination catalogue and Paris/Tokyo sourced geometry. Catalogue: **45 ACTIVE destinations, including 28 international**. Chicago, Beijing and Brisbane remain REQUESTABLE. No demand votes, entitlements or reward history were reset.
- Public health remains `environment: staging`, `release_ready: false`. Production certification is **NOT PASSED** until the outstanding live/device/provider gates are completed. No configuration was changed merely to make that flag appear ready.

### Outstanding acceptance gates

1. Secure authenticated retest of the final quick-input and pre-entry wallet fixes; logout/login entitlement persistence and a controlled new-account four-choice journey.
2. Physical phone/tablet portrait and landscape touch, GPU animation/camera, long walking/running and rental drives, interior exit and media/HUD overlap.
3. Two or more real user sessions for chat/voice/LiveFace regression and group/proximity behavior with actual media devices.
4. Live pickup routes in the remaining specified international cities; no new repeat/respawn economy is claimed.
5. Provider delivery and previously documented production readiness prerequisites. Composer/clipboard handoffs are verified only to the extent stated above.
