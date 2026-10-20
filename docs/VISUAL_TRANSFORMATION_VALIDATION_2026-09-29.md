# MyLilWorlds visual transformation — 2026-09-29

## Scope

Continues sainsabu41-cmyk/pulseworld from eed45715fcdefaa790f43f84806df706e81a7a53. Shared consumer UI, scenery, display assets, vehicles, avatar presentation and camera response only. No backend, authentication, wallet, XP/PC, mission, social, city-access, database or deployment-configuration edits. Existing maps, city catalogue, businesses, collectibles, rentals, transit, friends and event actions remain.

The visual system applies through the shared renderer to enabled UK and international districts. It does not substitute a new map or claim an exact real-world reconstruction.

## Automated checks

- Full existing backend suite: 217 tests passed locally (APP_ENV=test, temporary SQLite database).
- Frontend logic/component suite: 25 tests passed. Includes pickup, conversation reconciliation, media safety, movement state, sharing, signs, avatar LOD, new camera damping and static batching preservation.
- Camera-relative movement projection: 40 checks passed.
- Next.js production build, TypeScript validation and 12-page generation: passed.
- git diff --check: passed.

## Local browser evidence

Chromium with software WebGL2; local-only accounts and data. Normal registration, onboarding and owned-world entry were exercised through existing APIs/UI without bypassing permissions. No production QA accounts were created.

- Desktop 1440×900: 3D scene loaded; no horizontal overflow; HUD, rankings drawer, camera drag and walking exercised.
- Mobile viewport 390×844: no horizontal overflow; compact HUD, joystick and existing navigation visible. Legacy desktop control duplication corrected.
- Whitehouse, Cambridge and Paris scenes rendered using the shared visual layer.
- A local text auditorium event was created, started, entered and ended through existing endpoints. Stage, screen, audience furniture and existing chat UI rendered.
- Business card: source-backed Londis listing rendered with location, directions, virtual-store entry, claim-interest action and the existing assistant Coming Soon panel. No fabricated business fields were added.
- Final icon, auditorium lighting and caption-spacing pass: desktop and mobile rendered without overflow or page exceptions.
- No JavaScript page exceptions were observed in the full browser pass.

A sampled software-rendered view used approximately 756 draw calls/frame after colour batching; the earlier visual iteration used 1,265 and the baseline comparison used 1,040. Samples are diagnostic only: camera framing, live local NPCs and software-rendering timing vary. Software frame rate around 2fps is not a physical-device benchmark. No normal-device performance certification is claimed.

## Release target

Existing Railway project PULSEWORLD, production environment, service pulseworld (f28de9c9-b5c5-43da-bdfe-73aa4826d0b0), at https://pulseworld-production.up.railway.app. Existing PostGIS and Redis are retained. Deployment **f1ca6190-e4f6-4a56-a1a5-b7a01576d0ea** completed with **SUCCESS**, running application commit **8a488740a35e5c274f4528462d2a9e7b01019ce0**. Railway independently passed all 217 backend tests in 211.82 seconds, completed the frontend production build and passed `/api/health`.

Live verification: the new BETA treatment and interface loaded at the existing root URL; all 45 places remained available in the public selector; Paris loaded its correct mapped district and collectibles. The cloud browser used the supported 2D fallback, while the local Chromium pass verified 3D. No authenticated production session or real-device media test is claimed.

The generic redeploy wrapper initially selected the previous commit. An explicit deployment of the new commit corrected this; the prior deployments entered REMOVING after the new release became SUCCESS. No service or infrastructure was created, replaced or reconfigured. The published repository comparison confirmed no existing files removed and zero backend file changes.

## Remaining acceptance limits

Physical phone/tablet/GPU performance, all-city manual walkthroughs, full accessibility, real multi-user voice/video/LiveFace and privileged admin/merchant flows have not been re-certified in this visual change. Automated regression success is evidence within the tested scope, not proof of every production journey. The application retains its public testable status; release readiness is not asserted.
