# Targeted movement/camera validation — 2026-10-01

Base: a97d63e1be0113ad6ae2bc11500822061bafd2de. Publication requires the exact candidate to pass the existing CI gates and the new movement/camera job. No new repository, project or service.

## Measured baseline and correction

Production-build browser input on the same 262 m clear Whitehouse road; short trials include input-tick alignment and acceleration. Units are virtual metres/second, not physical human speeds.

| Measurement | Before | Corrected local browser |
|---|---:|---:|
| Public preview, full input | 12.90 | 12.99 |
| Authenticated default full hold | 6.68 (walk throughout) | 21.95 (walk then run) |
| Authenticated explicit run | 12.52 | 23.30 |
| Authenticated light joystick, 60% | 3.95 | 7.36 (walk throughout) |
| Bike, measured after acceleration | 18.45 | 27.35 |
| Car, measured after acceleration | 31.47 | 39.12 |

The preview has no distinct run state. Its nominal full-input pace is 12.5. Corrected server walk/run ceilings are 12.5/23.4375; elapsed-time endpoint tests measure both at 60/120/240 ms update intervals and verify release stops. Do not describe configured ceilings as browser measurements. The first browser baseline used the unmodified release frontend and backend. The vehicle baseline used a disposable copy of the original backend with the same rendered controls; its default-hold result is not the original frontend baseline.

## Root causes and scope

The walk calibration divided the preview pace instead of matching it. Run required an explicit control; duration of ordinary input was never considered. There was no measured 7–10× discrepancy, separate authenticated world-scale conversion or mobile-only speed multiplier. The server authoritatively integrates elapsed time and collisions; client snapshots reject older revisions. No reconciliation pullback occurred in the two-user route check. A further cold CI trial measured only 3.53 m/s during the first held input, with server gaps of 0.47–1.66 seconds and overlapping fallback batches during entry. The connection now suppresses fallback while entry is pending, starts its socket grace after entry, and serializes fallback batches, waiting for all reads to settle even when a sibling fails. Server long-gap safety clamps remain; this is not an offline-movement guarantee.

The camera's auditorium focus moved with yaw and its radius was clipped against venue meshes/bounds. Cartesian position damping also shortened the path during turns. The correction separates authenticated sensitivity, explicit zoom, angular damping and an indoor orbit whose focus/radius do not depend on drag angle. Mouse sensitivity: .0022 → .0012 rad/pixel. Touch: .0028 → .0016. Public preview sensitivity stays unchanged. Authenticated zoom: 6–38 outdoors; 6–10 indoors. Exterior obstacle clearance remains a safety adjustment.

Only movement, avatar gait, camera modules, related tests/workflow and documentation are changed. Existing UI layout, media/screen sharing, event logic, businesses, flags, rewards, wallets, auth and schemas are preserved. E-bike/scooter speed minima follow the same hierarchy so those existing vehicles are not slower than running.

## Observed validation

- Local production build passed.
- Candidate 9403cb1 CI passed all 235 backend tests, PostGIS migration validation, dependency audits, infrastructure, 44 frontend tests, 40 projection checks, lighting and world presentation. Its new movement job exposed a software-WebGL landing timeout in the harness; the final harness uses the established map fallback before entering real WebGL, waits on settled camera poses, and measures view orientation independently of its moving follow target. Exact final release CI is still required before publication.
- Shared camera/movement unit checks passed; elapsed-time and old-lease preservation tests passed.
- Actual browser short-press and hold-to-run transitions passed.
- Two users saw walk/run state and identical final authoritative coordinates.
- Actual WebGL auditorium mouse drag produced controlled rotation at constant distance; explicit wheel zoom passed.
- Actual WebGL at 390 and 820 px passed single-finger orbit at constant radius, two-finger pinch without rotation, and joystick movement without camera rotation. Event-panel dragging/scrolling did not move the camera. Real keyboard short press walked, hold ran, and release stopped. Screenshots were inspected; browser exceptions were absent.
- Local evidence is in docs/evidence/movement-camera-2026-10-01/measurements.json. The workflow uploads full measurements and screenshots as presentation-movement. Its seven-city multiplayer matrix covers London, Birmingham, Madrid, Dubai, Mumbai, New York and Sydney; geographic collision tests cover every active destination at the new maximum running step. Publication requires this full matrix to pass.
- Camera damping, continuous run blending and direction projection have 30/60/120 Hz regression coverage. The server endpoint measures 12.5/23.4375 m/s at different input intervals. The public preview still has its original fixed input-tick implementation and separate camera/gait profile; it is not rewritten by this task.

Production-account and physical-device acceptance remain unverified. The previous secure production sign-in was rejected by automatic approval review because no specific authorised accounts were identified; this work uses only local fixtures.


## Changed files

- Shared contract: `shared/movement.json`.
- Input and rendering: `apps/consumer-web/components/useWorldMotion.ts`, `World.tsx`, `WorldAssets.ts`, `RemoteExplorer.ts`; connection polling in `apps/consumer-web/app/page.tsx`.
- Shared movement/camera/gait: `apps/consumer-web/lib/movement.ts`, `cameraMotion.ts`, `worldCamera.ts`, `locomotion.ts` and their tests.
- Authoritative integration: `backend/api/world.py`, `backend/api/mobility.py`; related `backend/tests/test_release_movement_geography.py`.
- Browser measurements: `scripts/tests/movement-camera.cjs`, `scripts/tests/motion_fixture.py`, `.github/workflows/ci.yml`; the existing media browser test now stops movement on acknowledgements rather than delayed observer snapshots and brings both speakers into the mobile field of view through ordinary controls.
- ADR 0019, this validation record and compact evidence.

## Requested acceptance matrix

PASS refers to the local production build and automated coverage described below; final CI and deployment status must be checked on the exact published commit. Physical devices and authenticated production sessions are separate unverified acceptance items, not implied by viewport emulation.

| Requested check | Result and evidence |
|---|---|
| Preview walk baseline | PASS — measured 12.90 m/s before; approximately 12.99 afterward on the same mapped road. |
| Preview run baseline | N/A — preview has one pace and no separate run state. |
| Authenticated walk | PASS — actual authoritative endpoint measures 12.5 m/s; light joystick browser trials remain walking. |
| Authenticated run | PASS — actual browser full hold transitions to run; explicit run approximately 23.4 m/s. |
| Short press walk / hold to run | PASS — browser input and keyboard acknowledgements; 350 ms sustained strong input threshold. |
| Natural walk / natural run | PASS for gait mechanics — continuous run blend, stride, arm swing, lean and bounded cadence; subjective physical-device visual acceptance remains unverified. |
| Frame-rate independence | PASS for authenticated integration and camera/gait at 30/60/120 Hz; preview implementation is preserved. |
| Remote movement sync | PASS — remote walk/run states and final authoritative coordinates agree. |
| Walk < run < bike < car | PASS — measured endpoints and real rented bike/car browser movement. |
| Camera 360 rotation | PASS — constant-radius room-bound tests over full circle; actual WebGL drag verified. |
| Camera sensitivity reduced / smoothing | PASS — rendered drag measurements plus exponential-damping tests. |
| No accidental zoom | PASS for drag/pinch separation and indoor orbit. Exterior obstacle protection can shorten effective radius without changing explicit zoom. |
| Zoom limits / auditorium camera | PASS — outdoor 6–38 m, indoor 6–10 m; rendered auditorium mouse, wheel and touch checks. |
| UI does not rotate camera | PASS — event-panel drag/scroll and joystick interaction. |
| Mobile touch separation | PASS in Chromium touch emulation — one-finger orbit, two-finger pinch, joystick ownership. |
| UK cities / international cities | PASS for shared collision coverage across all 45 active destinations; seven-city multiplayer matrix is a release gate. |
| Events / auditoriums | PASS for movement/camera integration and local event entry; existing event/media/layout gates remain required. |
| Desktop | PASS in local Chromium, including real software WebGL. |
| Mobile / tablet | PASS at 390/820 px with touch emulation; physical iOS/Android/Safari NOT VERIFIED. |
| Preview unchanged | PASS — separate preview step, timing, sensitivity and gait preserved. |
| Multiplayer / vehicles / events preserved | Covered by existing CI gates and targeted lease/remote/browser checks; all gates must pass before publishing. |
| Other functionality unchanged | No unrelated application source changed in this task. Existing full regression gates remain required; exhaustive manual acceptance is not claimed. |

## Twenty requested root-cause answers

1. Preview effective full-input pace: 12.90 m/s before and approximately 12.99 afterward, including input-tick alignment.
2. Preview effective run pace: not applicable; it has no separate run state.
3. Authenticated walk before: 6.68 m/s, measured in the original production build.
4. Authenticated explicit run before: 12.52 m/s.
5. Authenticated walk after: 12.5 m/s measured by the real server endpoint at multiple intervals; browser 60% light-input trials measure approximately 7.4 m/s.
6. Authenticated explicit run after: approximately 23.4 m/s in browser; 23.4375 m/s measured endpoint ceiling. Full hold includes the initial walking/acceleration period and therefore averages about 22 m/s.
7. Slowdown causes: preview pace was assigned to run and then divided for walking; ordinary held input never selected run. Cold fallback polling also began before entry and overlapped slow batches, delaying input processing.
8. There was no independent wrong client world-scale multiplier. The shared walk/run mapping was wrong, and held-input mode selection was missing.
9. Server bounded elapsed time legitimately limits delayed inputs. Collision, acceleration, backlog and authorization safeguards remain unchanged. The two-user trial showed no reconciliation pullback.
10. Time-based integration was already present. Multi-second input gaps hit its existing safety bounds. Camera position damping additionally cut corners during orbit; that separate visual defect was corrected.
11. Mobile input did not have a different speed multiplier. Magnitude remains proportional; a light joystick stays walking and sustained strong input runs.
12. Shared previewStep 1.5, inputIntervalMs 120 and runMultiplier 1.875 define calibration; preview behavior is preserved. Shared hold and joystick thresholds govern authenticated input only.
13. Bike before/after: 18.45 m/s before and approximately 28 m/s after in accelerated browser trials; configured minimum is 28.
14. Car before/after: 31.47 m/s before and approximately 39–40 m/s after in accelerated browser trials; configured minimum is 40.
15. Camera sensitivity used the fast preview coefficients for authenticated scenes, including touch. It now has a separate lower profile.
16. Unwanted interior zoom came from yaw-dependent focus, venue clipping and Cartesian chord-cutting. A fixed pivot with damped spherical orbit removes those causes. Exterior obstruction protection remains intentional.
17. Mouse sensitivity .0022 → .0012 rad/pixel; touch .0028 → .0016. Preview coefficients remain unchanged.
18. Zoom limits: 6–38 outdoors, 6–10 indoors, with interior ceiling pitch protection.
19. Direct movement benchmark: Milton Keynes/Whitehouse; local auditorium WebGL at desktop, 390 and 820 px. Regression matrix: London, Birmingham, Madrid, Dubai, Mumbai, New York, Sydney. All 45 active destinations have swept-collision tests at the new maximum running step. Physical mobile hardware and production account tests remain unverified.
20. Exact affected modules are listed under Changed files above and in the base-to-release Git comparison.

## Cold-start polling regression

The fresh local build passed all 27 checks. Full held input averaged 22.23 m/s; 27 movement acknowledgement round trips measured median 32 ms, p95 97 ms and maximum 100 ms. The maximum server processing interval during that trial was 186.8 ms. These are local browser measurements, not a production latency SLA.

Fault injection delayed world entry by 4.30 seconds, kept each world response pending for 6.5 seconds and immediately failed a sibling notifications request. No fallback batch began during entry; the first began 7.69 seconds after entry completed (the five-second grace plus polling tick alignment). Two complete fallback batches ran with maximum one world request in flight and no overlap, including the early-failure case. CI uploads the same fault-injection measurements in presentation-movement.

The browser keyboard check is run after closing the separate software-WebGL observer process, with an explicit visible-page check and failure diagnostics. Real key events and server run/stop acknowledgements remain mandatory. The existing media check retains all assertions and retries a displayed local transport-join failure once through the existing Reconnect control.

## Outdoor XP continuation evidence

The subsequent scoped outdoor-speed/XP candidate fd0d1163d7b316829ecf7189d612cd7604c3199e passed the existing movement/camera regression gate in both CI runs 36884435751 and 36886472154 (16/16 jobs each). It is served by successful existing-service Railway deployment c5b52edb-ad54-42ba-a2ea-3683c1e1b17d. Public health and Whitehouse/Madrid map previews passed. Authenticated production movement and XP checkout remain unverified pending an authorized existing account. See OUTDOOR_XP_VALIDATION_2026-10-01.md and docs/evidence/outdoor-xp-2026-10-01/recovery.json; no previous blocked acceptance row is converted to PASS by this update.
