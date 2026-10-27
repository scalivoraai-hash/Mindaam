# Mindaam combined release — revised procedural-avatar scope

The owner revised the release scope on 27 October 2026: improve the existing avatars, finish city upgrades and staging validation, and publish to Mindaam GitHub for GCP deployment. External rigged character assets are no longer a release prerequisite. This report supersedes the earlier unpublished report; it does not claim every aspirational item from the original 24-section brief.

## Implemented

- Shared procedural human geometry: smoother head and tapered torso/limbs, connected joints, facial detail, blink/speaking motion and distance detail controls. Existing saved appearance and movement remain compatible. Remote appearance edits refresh without replacing the player's movement root. Profile and editor share a rotatable 3D preview. These are stylised procedural humans, not photorealistic scanned or rigged GLB characters.
- Regional British, Gulf, Indian and North American facade palettes, masonry variation, recessed windows, regional roof defaults and road markings. Literal mapped colours override defaults. Building footprints/heights, collision geometry, OSM attribution and source data remain intact. Regional styling is not a claim of surveyed facade reconstruction.
- Living weather/seasons, sky, connected traffic routes, arena placement/discovery, ticketing/refunds, purchased-credit bookings, event engagement/creators, compact chat and shared 40% walk-speed reduction (running preserved).
- Signed-in public profile page/modal/card; metadata and normalized visible social links; independent follow/unfollow and friendship; privacy-filtered data; cropped profile/cover photos with bounded decoding and metadata stripping; deletion/export support.
- Approved venue defaults: 2 hours 180 PC; 10 hours 700 PC. Additive migration fs27 fills missing catalogue prices without overwriting configured values, disabled catalogues or historical charges.
- Existing GCP workflow automatically stages only successful, trusted main-push Validation runs at the current main SHA. Fork/PR/failure/stale sources are rejected. Production promotion remains separately gated.

## Local verification

- Frontend unit suites: 55 passed, including geometry budget, movement, city palette and climate contracts.
- Backend full run: 275 passed; one test-code NameError was corrected. The corrected growth module passed all seven tests separately; the initial full run is not misrepresented as green.
- GCP automation: 59 tests passed. Mock infrastructure output is not live GCP evidence.
- Real WebGL renderer: five remote-avatar/vehicle transitions and remote restyling passed.
- Five mapped city fixtures (110 m spawn radius): London, Milton Keynes, Dubai, Mumbai and New York rendered with unchanged input geometry and attribution; repeated-city GPU resource counts stable; no renderer errors. This is not a full-map or physical-device FPS certification.
- Final production build and booking/profile/photo browser acceptance passed (exit 0); see evidence/combined-validation.json. Browser acceptance intentionally tested the map fallback; standalone renderer checks exercised WebGL. Local fixture credits exist only in disposable test databases, never staging/production.

## Staging acceptance and operations

The workflow tests real HTTPS, multiplayer and direct/forced-TURN media against the exact staging revision. Its paid venue journey requires a dedicated, onboarded staging account with legitimately purchased credits. Configure repository secrets MINDAAM_STAGING_QA_HOST_IDENTIFIER and MINDAAM_STAGING_QA_HOST_PASSWORD, plus variable MINDAAM_STAGING_QA_MAX_RESERVATION_PC (the explicit maximum per booking). Keep passwords in GitHub secrets, never in source or chat. Direct and relay acceptance each reserve one one-hour venue; with the default price this consumes 100 PC per journey. The host is retained; disposable peers are deleted. Missing funding/configuration fails acceptance and prevents readiness certification. No test ledger credits are injected remotely.

Target repository: https://github.com/scalivoraai-hash/Mindaam, main. Parent source: 9533e15f7dd9fd8e689845338ef4932365bbd795. Publication preserves the existing tree/history, including earlier evidence absent from the recovered checkout. GitHub Actions run results are the authoritative CI/deployment status after publication. Local checks do not certify staging or production. Original MyLilWorlds, Railway, DNS and production promotion are outside this release.
