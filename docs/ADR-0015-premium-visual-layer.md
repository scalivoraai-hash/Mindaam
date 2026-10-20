# ADR-0015: Premium city presentation within the existing renderer

Date: 2026-09-29

## Decision

Retain the existing Next.js/Three.js consumer, FastAPI APIs, OSM district geometry, input transport, collision checks, social surfaces and Railway service. Apply the MyLilWorlds visual transformation through shared styling and reusable procedural geometry. No dependencies, database migrations, access rules, economy rules or backend routes change.

The shared premium stylesheet follows the existing layout and responsive state classes. Existing event, voice, chat, LiveFace and split-screen state machines retain their handlers. New business-card markup presents the same authoritative data and actions; the existing assistant remains Coming Soon.

City facades use five shared 256px procedural atlases, footprint-aligned walls, windows, cornices, storefront details and roof caps. Irregular footprints and holes are preserved. Roads retain their original 12m rendered corridor and 7m driving strip. Pavements, kerbs, lane markings and mapped crossings are visual only. Traffic signals render only where map data identifies them. No named business or map activity is fabricated.

Cars, motorbikes in the existing scooter category, bicycles, buses, shelters, trees and avatar clothes receive reusable detail. Boarding, seating, routes, rentals and server positions are unchanged. Two outward-facing display planes avoid mirrored labels. Advertising images and video still use the existing campaign texture path. Rankings retain authoritative scores and refresh logic; districts without one of the five original board placements receive a display near the map spawn.

Static meshes are merged by compatible geometry layout, material finish and 80m tile. Solid material colours are packed into vertex colours, reducing draw calls while retaining spatial culling. Existing avatar LOD and district-distance culling remain. Textures, generated batch materials and environment maps are disposed with the scene. Lighting uses a bounded 1024px shadow map and a generated environment map; pixel ratio is capped at 1.25 for coarse-pointer devices and 1.5 otherwise. No downloaded model pack, heavy texture dependency or runtime map-provider request is added.

Camera drag targets use lower mouse/touch sensitivity, bounded interrupted-pointer deltas and frame-rate independent exponential damping. Full yaw rotation, pitch bounds, pinch/zoom, camera presets, bus views and camera-relative movement remain. Movement aligns with the rendered camera, not its not-yet-displayed target. Walking/running speeds, authority, rewards and collision logic are unchanged.

## Validation and limits

See VISUAL_TRANSFORMATION_VALIDATION_2026-09-29.md. Visual fidelity is a stylised approximation within the existing procedural architecture. Local software-WebGL screenshots verify geometry and interaction, not normal-device frame rate, complete accessibility or multi-device audio/video correctness. Those broader production acceptance gates remain open.
