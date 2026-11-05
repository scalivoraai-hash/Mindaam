# Cinematic V2 staging candidate

Source baseline: `33b4bfa940a4de70f5387ab6f8c435d1adc512cf`.
This is an implementation candidate, not a claim of full visual or performance acceptance.

The previous staging release was independently read from workflow artifact 13366913968: revision `mindaam-staging-00020-6b2`, image digest `sha256:ac4db70eb2665c0730c2f54a9a3193d36fbee87f0b63be5d35add611650b7ee2`. Production returned HTTP 200 / environment production, but its exact current revision and digest have not been independently retrieved. No production mutation has been performed.

## Implemented scope

- Shared staging V2 profile covers the 45 installed, approved destinations. Existing v1 and standard fallback remain available; production cannot select V2 through the profile endpoint.
- Mapped building polygons and existing authoritative terrain, movement, entitlement, wallet and rental data remain unchanged. Regional facade materials, window proportions, balconies and eligible rectangular roof approximations use shared city definitions.
- Street nameplates are indexed across the source district and pooled around the player. The former 45-name and 180-POI startup limits are removed. Dynamic signs are created after static batching so walking does not leave stale sign copies.
- Fresh OSM street furniture is separate, integrity-checked, lazily loaded visual data. It deliberately does not rewrite map gzip files: those hashes protect terrain/trail/billboard caches. Source requests succeeded for 14 destinations; 31 requests were blocked by the external network proxy. The import ledger preserves every result.
- Traffic-light colors use a shared visual clock, amber and all-red clearance. Opposing display axes never share green. This is approximate scenery timing; it does not alter authoritative driving behavior.
- Versioned, server-validated avatar appearance, category studio, presets, color controls, viewing controls, and rig-attached accessories. Preview, world and auditorium use the same renderer; legacy saves are adapted in memory. This is procedural wardrobe geometry on the existing licensed model, not a complete authored clothing collection or a photorealistic avatar system.
- Searchable city modal, compact destination cards, current-city marking, and six visible private-chat toolbar actions retain existing access and action APIs.

## Evidence and remaining acceptance

`city-inventory.json` / `.csv` distinguish source counts, approximate appearances, missing reconciliation and test status. `street-furniture-import.json` includes source IDs through the referenced assets, timestamps, hashes, licensing and blocked destinations.

The first all-city isolated Three.js pass rendered all 45 districts and indexed all 28,865 existing building footprints. These are actual browser renders on SwiftShader, not physical-device FPS acceptance. Subsequent aerial captures and final application checks remain separate. The source coordinates and street-name algorithm are tested; a passing geometry check alone does not establish visual quality.

Local frontend unit tests: 90 passed. Focused backend appearance/profile tests: 20 passed. GCP orchestration tests: 115 passed. An all-backend run using the initial map rewrite found that billboard cache hashes no longer matched. The map rewrite was removed, visual data isolated, and the exact billboard placement regression passed. The full backend suite must pass again on the final source in CI.

Outstanding items must not be described as done:

- Fresh map-furniture reconciliation for the remaining 31 destinations.
- Complete external-source building/POI reconciliation, new footprint admission, and verification of unknown building uses. No new building footprint is claimed.
- Fine garment fitting during all walking/running/seating/riding combinations and final visual approval of every catalog option.
- Physical Android/iOS/desktop GPU measurements against the prior staging baseline.
- Actual final-source GitHub CI, immutable staging deployment, and live two-user/browser acceptance; recorded only after completion.

There is no production release approval in this evidence packet.
