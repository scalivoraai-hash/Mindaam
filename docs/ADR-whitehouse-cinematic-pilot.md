# Whitehouse cinematic pilot — development checkpoint

Status: incomplete feature branch; no staging or production deployment authorised by this checkpoint.

The pilot is gated by APP_ENV=staging, city=milton-keynes and the exact server configuration MINDAAM_VISUAL_PROFILE=cinematic-world-v1. Production is ineligible even if that configuration is accidentally present. The configuration is not enabled in any deployed service. Optional profile lookup is bounded to 1.5 seconds and defaults to the standard renderer on failure. No gameplay endpoint, position, footprint, movement or reward rule is changed.

CinematicDistrict adds original procedural masonry and roof artwork, instanced window/door/trim geometry and rectangular residential-context roof approximations. Unknown building uses remain unknown; residential landuse provides visual context, not a verified individual building classification. The immutable base footprint renderer remains the far LOD. The detailed layer indexes the whole dataset, lazily builds one 80-metre tile per update and evicts tiles outside the selected neighbourhood. Low/balanced quality limits the neighbourhood to nine tiles; high uses at most 25. Shared resources are disposed explicitly. The legacy entrance pass is omitted only for cinematic Whitehouse to prevent duplicate overlapping entrances.

Run `python3 scripts/audit-whitehouse.py --output /tmp/whitehouse-inventory.json` for the full per-feature inventory. Source summary and isolated renderer measurements are in docs/evidence/whitehouse-cinematic. The audit establishes input eligibility, not complete geographic truth. No new buildings have been invented or added. No fresh external OSM survey has been performed.

Local validation: existing 71 frontend unit checks passed; three new streaming/isolation tests passed; backend rollout matrix passed; TypeScript passed. Full-dataset software-rendered desktop, mobile and tablet fixtures passed geometry, immutable-input, eviction and resource-disposal assertions. Renderer timings are not end-to-end frame rates, physical-device benchmarks or staging browser acceptance.

Still required: complete commercial and POI audit against reliable licensed sources; rigged character/NPC visual work; vehicle/vegetation/weather presentation; close-range spatial review; complete-app baseline and performance budgets; portrait/landscape input and full gameplay regressions; CI; safe staging-only activation/deployment and live acceptance. Current screenshot quality does not meet the complete cinematic brief. Do not promote this checkpoint to main or deploy it as a finished pilot.

Production remains outside this pilot. No production/finalize workflow, traffic, database, DNS, payment gate or Railway change is part of this work.
