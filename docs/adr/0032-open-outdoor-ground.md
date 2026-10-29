# Open outdoor ground

Pedestrians may traverse unclassified virtual outdoor ground within the existing district bounds. Explicit mapped restrictions, water, barriers and building collisions take precedence. Vehicles retain road restrictions; server integration, speed and reward rules are unchanged. Client navigation uses the same policy and spatial index.

Bird passes anchor in world space once per cycle rather than following the player each frame. Existing sky/weather and disposal remain intact. World-selection spacing and responsive dialog sizing reuse the existing theme.

Local validation: nine backend terrain tests, three frontend terrain tests, production build, authenticated movement/camera regressions, camera-projected bird displacement and wing animation, four-city and mobile joystick preview traversal pass. Responsive suite completed 98 captures with no runtime or sampled solid-surface contrast failures. These are local results, not staging or production acceptance. Exact-release CI, staging, recovery/security and owner review remain required before production.
