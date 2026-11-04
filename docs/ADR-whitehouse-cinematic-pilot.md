# Whitehouse cinematic pilot — development checkpoint

Status: incomplete feature branch; no staging or production deployment authorised by this checkpoint.

The pilot is gated by APP_ENV=staging, city=milton-keynes and the exact server configuration MINDAAM_VISUAL_PROFILE=cinematic-world-v1. Production is ineligible even if that configuration is accidentally present. The configuration is not enabled in any deployed service. Optional profile lookup is bounded to 1.5 seconds and defaults to the standard renderer on failure. No gameplay endpoint, position, footprint, movement or reward rule is changed.

CinematicDistrict adds original procedural masonry and roof artwork, instanced window/door/trim geometry and rectangular residential-context roof approximations. Unknown building uses remain unknown; residential landuse provides visual context, not a verified individual building classification. The immutable base footprint renderer remains the far LOD. The detailed layer indexes the whole dataset, lazily builds one 80-metre tile per update and evicts tiles outside the selected neighbourhood. Low/balanced quality limits the neighbourhood to nine tiles; high uses at most 25. Shared resources are disposed explicitly. The legacy entrance pass is omitted only for cinematic Whitehouse to prevent duplicate overlapping entrances.

Run `python3 scripts/audit-whitehouse.py --output /tmp/whitehouse-inventory.json` for the full per-feature inventory. Source summary and isolated renderer measurements are in docs/evidence/whitehouse-cinematic. The audit establishes input eligibility, not complete geographic truth. No new buildings have been invented or added. No fresh external OSM survey has been performed.

Local validation: existing 71 frontend unit checks passed; three new streaming/isolation tests passed; backend rollout matrix passed; TypeScript passed. Full-dataset software-rendered desktop, mobile and tablet fixtures passed geometry, immutable-input, eviction and resource-disposal assertions. Renderer timings are not end-to-end frame rates, physical-device benchmarks or staging browser acceptance.

Still required: complete commercial and POI audit against reliable licensed sources; rigged character/NPC visual work; vehicle/vegetation/weather presentation; close-range spatial review; complete-app baseline and performance budgets; portrait/landscape input and full gameplay regressions; CI; safe staging-only activation/deployment and live acceptance. Current screenshot quality does not meet the complete cinematic brief. Do not promote this checkpoint to main or deploy it as a finished pilot.

Production remains outside this pilot. No production/finalize workflow, traffic, database, DNS, payment gate or Railway change is part of this work.

## Character integration and frontage checkpoint

The optional Whitehouse profile now loads the pinned, CC0-derived character GLB (1,922,556 bytes; SHA-256 `5f945139ffd86cbd4f8877784412adb97c388eb10b65eda931983eb716ea375e`) for the player, supported NPC appearances and remote players. The existing renderer remains the fallback on asset failure and for unsupported hair styles. Shared geometry/textures and isolated skeleton/material instances are disposed on city exit; distant instances retain existing avatar animation hooks. No movement, speed or ownership changes are included.

Entrances use nearby mapped route frontage. Contained mapped business POIs may inform facade style; unclassified residential-context buildings retain explicitly approximate classification. Footprints, heights and authoritative collision data are unchanged.

Local validation: production build and type check passed; seven character tests and twelve architecture/renderer tests passed. The full application loaded the character asset and passed nine emulated viewport smoke checks (320 through 1280 pixels), with no page exceptions or horizontal page overflow. See `docs/evidence/whitehouse-cinematic/local-world-smoke.json`. This is software-rendered local testing with an intercepted profile response, not staging acceptance or physical-device performance. The raw RAF cadence is not an FPS measurement.

Current OSM comparison retains all 1,247 original footprints. It found no new building IDs in its supported-square candidate filter; partial map relations and incomplete OSM coverage prevent claiming real-world completeness. Street-furniture candidates are not yet admitted rendered assets.

**Pilot remains incomplete and not deployed.** Remaining work includes appearance coverage, comprehensive district visual review, environment/vehicle visual acceptance, safe mapped-prop enrichment, actual performance baselines, and staging acceptance. The original scooter CI failure remains unexplained despite subsequent passing unchanged assertions; sanitized input/ack/focus/long-task evidence is now retained by the original scenario to diagnose recurrence. No assertion or deadline was relaxed. No production change is authorised or made.

## Recovery and staging configuration

The Whitehouse-only scenery pass now places 104 previously unrepresented mapped points from the retained OSM comparison, including 40 trees, 24 bus stop signs, 21 litter bins and 10 benches. The static district renderer batches these objects. Crossings still need tag and orientation review before their road markings can be placed. Central pedestrian settings now control the authoritative indoor and outdoor walk and run step. The conversation panel reserves separate space for the composer and compact call controls. Staging manifests explicitly select the cinematic profile, with city and environment eligibility enforced by the API. Completing a feature-branch checkpoint does not deploy it.
