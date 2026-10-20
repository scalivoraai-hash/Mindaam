# Multiplayer, movement, media, transit and visual stability — 29 September 2026

## Scope and release state

Targeted continuation of the existing MyLilWorlds application, repository and Railway service. No new project/service, replacement backend, schema migration, new world/vehicle, economy rule, authentication system or media architecture. Final application candidate bd7e33dedc537b655a394fe4577fdc33bd6b1e30 passed every CI job. Railway deployment cff86ad4-f33e-4eef-a683-cece7611ea17 is SUCCESS on the existing service at https://pulseworld-production.up.railway.app/. The physical-device and production-provider acceptance limits below remain open.

## Confirmed root causes and changes

1. **Remote cars and bikes:** world snapshots omitted authoritative rental identity, heading and speed. The remote renderer always instantiated a walking human. The existing state message now includes a read-only vehicle projection and movement state. One transform owns the vehicle and driver; existing rental availability prevents a second parked copy. Exit removes that vehicle and blends back into walking.
2. **Remote smoothing:** timestamped samples, wrapped heading, frame-independent damping and prediction bounded to 550 ms cover the existing 500 ms snapshot cadence. A 32 m/s car regression stays within two metres during steady motion and freezes bounded prediction on packet loss. No per-frame HTTP traffic or new realtime service.
3. **Robotic movement:** the former gait used absolute time multiplied by changing speed, producing phase jumps, and lacked articulated knee/run transitions. Distance-integrated phase, articulated knees/elbows, distinct running posture and smooth blend weights now persist across packets. Walk is 3.2 virtual m/s; run is 6 (1.875x). Rentals and fast transport retain their existing speed settings. Coordinates, collision sweeps, XP and reward rules remain authoritative and unchanged.
4. **Position resets around media:** no direct call-to-teleport instruction or media-driven world remount was found. A confirmed reconnect defect deleted Presence after 60 seconds even with valid authentication; reconnect could then respawn at the district entry. Virtual coordinates now survive that interruption, while existing 45-second visibility expiry still hides stale users. Snapshot time and movement revisions prevent older responses rewinding newer positions. This fixes the reproduced reconnect path; it is not a claim that every historical reported teleport had the same cause.
5. **Event audio/video:** accepting/entering an event did not connect audience clients to its media room. Already joined audience members now connect as listeners, with devices off and existing publish grants unchanged. The former track renderer detached/recreated every playback element on unrelated track changes. Identity/SID-owned elements now survive those changes; only removed/replaced tracks detach. Autoplay rejection exposes a tap-to-listen action. Camera-off/removal clears the stage screen without interrupting audio.
6. **Bus boarding:** the existing ticket purchase is already an atomic ticket/seat/boarding transaction, not a separate payment followed by a separate ticket endpoint. Its boarding transition did not advance `last_move`, allowing stale walking snapshots to overwrite the seated presentation. Boarding now advances that revision, returns the seated position and reconciles immediately. The one-click UI performs the existing validated hail step, locks duplicate submissions, and does not treat a failed background refresh as a failed purchase. Existing fare, access, capacity, proximity and idempotency validation remain intact.
7. **Covered controls:** a city-action layer could intercept Expand/other call controls. The call layer now sits above it; the approved LiveFace layout is retained.
8. **Visuals:** existing map tags select residential, apartment, shop, office, civic and utility families, with four shared facade atlases and eight deterministic palettes. Unknown buildings remain neutral. Roofs respect mapped footprints; business names are not invented. Auditorium presentation adds lighting rigs, acoustic panels, a framed video wall, seating/aisles and coloured stage lighting. Existing event logic and geospatial collision positions are retained.
9. **CI inspection:** the pre-existing Alembic check mistook PostGIS extension-owned tables for removed application tables and equivalent PostgreSQL TRIM spellings for different username indexes. Read-only inspection now handles those cases. Missing/changed/nonunique application indexes still fail. No database schema or authentication normalization rule changed. Test clients use separate identities so independent fixtures do not exhaust one shared Redis rate bucket; production limits are unchanged. The existing dependency audit identified vulnerabilities in the pinned cryptography 46.0.0; it is updated to 50.0.1, with authentication/media regression coverage. No signing, password, encryption or grant logic is replaced.

## Realtime/API compatibility

Existing `state` messages gain `server_time`; peer objects gain `vehicle`, `movement_state`, `speed`, `sampled_at` and `last_move`. Vehicle presentation contains existing asset/vehicle IDs, kind, heading, position, speed and seat. Existing `input`, `motion`, room names, grants and WebSocket paths remain in place. `/transit/board` adds acknowledged position. `/media` adds the viewer's event role and active speaker IDs. No endpoint was removed.

Diagnostics retain existing rental/boarding/recovery audit records and add safe lifecycle status logs, room joins, publish/subscribe events and disconnect reasons. They do not log credentials, media contents or private messages.

## Evidence and limits

- Three new backend regressions failed on the previous implementation and passed after the fix: remote rental identity/exit, boarding revision/passenger projection, and stale-presence recovery.
- All 222 backend tests passed locally with APP_ENV=test and cryptography 50.0.1; the final candidate CI also passed the full suite, real PostGIS migration upgrade/check and dependency audit (no known vulnerabilities). The affected human-pace/geography/integration run passed 60 tests after tuning.
- 30 frontend tests and the final production Next.js build passed locally. Final-candidate CI type checking, frontend tests/build/audit and infrastructure/Docker checks passed. The Railway production image independently passed all 222 backend tests in 237.28 seconds.
- Real-browser multiuser tests run production Next.js, the existing API, disposable SQLite fixtures and real LiveKit 1.13.7. Two independent authenticated contexts drive/call; events use one publisher plus two participants. Synthetic camera and sine-wave microphone exercise actual WebRTC; receivers verify decoded frames and nonzero audio energy. No production fixtures/users/credits are created.
- Cross-city matrix: London, Birmingham, Madrid, Dubai, Mumbai and New York. Paris additionally passed calls, reciprocal rentals, event toggles/late join/rejoin and viewport checks. Paris has no existing enabled same-country bus route; Madrid supplies the European journey test. No Paris route was invented.
- Whitehouse additionally passed a two-session test with a real WebGL observer: car/bike enter/exit, passenger projection, first-click purchase, single fare debit and destination exit. Isolated renderer checks confirm one avatar/vehicle transform and inspect seated poses.
- Separate full-scene 3D checks covered the auditorium and desktop/mobile Whitehouse without browser exceptions. Software rendering averaged about 2.4 FPS; this is not evidence of normal-device GPU performance. Draw calls were slightly lower than the previous visual release.
- Browser environments: Chromium on Linux; desktop 1100×760 and 1440×900; 390×844 mobile and 820×1180 tablet layouts. The final event participant also uses mobile/touch emulation. Physical iOS/Android/Safari, real microphones/cameras, separate external networks and the production LiveKit provider are not yet signed off.
- All shared fixes apply to enabled UK/international worlds. Cross-city sampling does not claim that every world was manually visited.

## Changed areas

Backend: the audited `requirements.txt` pin; `world.py`, `player_presentation.py`, `transit.py`, `main.py`, `media.py`; migration inspection only in `migrations/env.py` and `inspection.py`.

Frontend: `World`, `RemoteExplorer`, `WorldAssets`, `WorldScenery`, `CityAssets`, `DisplayAssets`, `MediaPanel`, `MediaTiles`, `Transit`, `Mobility`, the acknowledged-boarding handler, motion reconciliation, locomotion/remote-motion/building-style helpers, API error presentation and narrowly scoped media CSS.

Tests/documentation: regression and migration-inspection tests, isolated fixture identities, the six-city production-build browser workflow, local-only browser fixtures, renderer checks and ADR-0016. Exact paths and diffs are in the fix branch.

## Final acceptance

All nine jobs in final CI run 36628764796 passed. Six cities each passed 29 browser checks (174 total), with no browser errors. Exact compact evidence is preserved in MULTIPLAYER_ACCEPTANCE_EVIDENCE_2026-09-29.json. Deployment cff86ad4-f33e-4eef-a683-cece7611ea17 is SUCCESS for exact application commit bd7e33dedc537b655a394fe4577fdc33bd6b1e30. Railway startup/readiness passed. The live public landing, unchanged 45-destination catalogue, Whitehouse preview and Madrid map/collectibles loaded successfully. The cloud browser has WebGL disabled and used the existing map fallback; its WebGL initialization messages are not GPU acceptance evidence. Railway HTTP logs confirm /, /explore and /api/health returned 200 without upstream errors; startup/readiness and the platform deployment health check passed. No blanket production-readiness or physical-device performance claim is made.


## Acceptance matrix

PASS means the specific behavior was observed in the production-build test environments described above, or in the cited renderer/visual checks. It does not imply a production-provider or physical-device certification. FAIL below means an outstanding acceptance gate, rather than a newly observed functional defect. All six city jobs and all remaining CI jobs passed on final candidate `bd7e33dedc537b655a394fe4577fdc33bd6b1e30`. Each city passed all 29 checks without browser errors.

Browser flow evidence: [final candidate validation](https://github.com/sainsabu41-cmyk/pulseworld/actions/runs/36628764796). Each city has 29 acceptance checks and an uploaded artifact containing `results.json` and screenshots. The compact result, including unchanged call/layout coordinates, is also committed in `docs/MULTIPLAYER_ACCEPTANCE_EVIDENCE_2026-09-29.json`.

### HUMAN MOVEMENT

| Check | Result |
|---|---|
| Natural Walk | PASS — articulated distance-driven gait and smooth idle blend. |
| Natural Run | PASS — distinct posture, knee/elbow motion and stride. |
| Walk/Run Speed Difference | PASS |
| Animation Blending | PASS |
| Remote Player Animation | PASS |
| No Robotic/Stutter Movement | FAIL — continuous gait is verified; smooth frame rate on physical devices remains unverified. |

### WALK TOGETHER / SOCIAL MOVEMENT

| Check | Result |
|---|---|
| Walk While Voice Calling | PASS |
| Walk While Video Calling | PASS |
| Run While Calling | PASS |
| No Automatic Separation | PASS |
| No Location Reset | PASS |

### MULTIPLAYER VEHICLES

| Check | Result |
|---|---|
| Car Visible to Remote User | PASS |
| Bike Visible to Remote User | PASS |
| Correct Driver State | PASS |
| Correct Enter State | PASS |
| Correct Exit State | PASS |
| Remote Vehicle Smoothing | PASS |
| No Duplicate Walking Avatar | PASS |

### LIVEFACE / VIDEO CALL

| Check | Result |
|---|---|
| No Automatic Teleport | PASS |
| No Unexpected Position Change | PASS |
| Call Stable While Moving | PASS |
| Minimise Stable | PASS |
| Expand Stable | PASS |
| Full Screen Stable | PASS |

### EVENTS

| Check | Result |
|---|---|
| Speaker Microphone | PASS |
| Speaker Video | PASS |
| Participant Audio | PASS |
| Participant Video | PASS |
| Late Join | PASS |
| Mute / Unmute | PASS |
| Camera Toggle | PASS |
| Multiuser Test | PASS |

### BUS

| Check | Result |
|---|---|
| Ticket Purchase | PASS |
| Board Button | PASS |
| First Tap Boarding | PASS |
| Passenger Assignment | PASS |
| Remote Passenger Visibility | PASS |
| Exit Bus | PASS |
| No Duplicate Charge | PASS |

### AUDITORIUM

| Check | Result |
|---|---|
| Stage Visual | PASS |
| Lighting | PASS |
| Big Screen | PASS |
| Seating | PASS |
| Interior Quality | PASS |
| Existing Events Preserved | PASS |

### WORLD VISUAL VARIETY

| Check | Result |
|---|---|
| Houses | PASS |
| Flats/Apartments | PASS |
| Shops | PASS |
| Commercial Buildings | PASS |
| Offices | PASS |
| Building Colour Variation | PASS |
| Facade Variety | PASS |
| Road/Street Visuals | PASS — prior premium street layer retained; mapped geometry unchanged. |

### GLOBAL COVERAGE

| Check | Result |
|---|---|
| UK Worlds | PASS — London/Birmingham; additional Whitehouse 3D observer. |
| International Worlds | PASS — Madrid/Dubai/Mumbai/New York; additional Paris media checks. |
| Desktop | PASS — Linux Chromium; other browsers/hardware remain open. |
| Mobile | PASS — 390×844 Chromium touch emulation; physical device coverage remains open. |
| Tablet | PASS — 820×1180 Chromium viewport; physical device coverage remains open. |

### PRODUCTION

| Check | Result |
|---|---|
| Production Build | PASS |
| Existing Features Regression | PASS |
| Production Deployment | PASS — existing Railway service, exact validated application commit, SUCCESS. |

## Remaining release acceptance

- Physical mobile/tablet, Safari and normal-GPU frame-rate checks are still required. Software-WebGL evidence cannot establish mobile performance or a universal absence of stutter.
- Authenticated multiuser calls through the deployed production LiveKit provider, real camera/microphone devices and separate external networks have not been executed. Repository AGENTS.md prohibits fake production users; approved authenticated production test sessions are needed for that final check. Functional multiuser evidence uses actual WebRTC in disposable CI infrastructure, not production accounts or mocked media.
- The six-city WebRTC suite uses the existing map fallback to keep concurrent software renderers from starving media. A separate real-WebGL observer and isolated renderer checks cover remote vehicle parenting/poses. These complementary checks do not certify simultaneous full-3D/media performance on consumer hardware.
- Thus the functional repair/build can be deployed, but the user's universal all-device production definition of done is not yet fully signed off.
