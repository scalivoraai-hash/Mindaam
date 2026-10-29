# ADR-0030: conservative public terrain and bounded outdoor visuals

Use the existing attributed OSM snapshots and coordinate system to extend pedestrian traversal beyond road strips. Only explicitly supported public-ground classes are eligible; unknown access is not permission to enter private gardens, farmland or unmapped terrain. Water, restrictions and buildings take precedence. Cache spatial buckets within world bounds. Preserve sweep/slide, server speed integration, reward validation and separate vehicle routing. The preview consumes server classification and cannot grant rewards or sessions.

Keep environment animation client-side, seeded and pooled. Use one small original grass atlas/material and a bounded near-camera blade pool, lower densities at low quality, visible rain under reduced effects, and owned-resource disposal. Parachutists leave the visible area above ground; no real landing access is inferred.

No schema/data migration or map replacement. Rollback uses the previous immutable application image through the existing release workflow. Deployment requires existing CI and staging gates; production additionally requires a new exact-image release review. Local software-rendered evidence is not represented as physical-device or public-domain acceptance.
