# ADR 0018 — Contextual launch presentation

The authoritative `world.scene.template === 'auditorium'` snapshot is the single presentation boundary. Event discovery and city-only HUD controls remain available outside that boundary. Inside, the existing Event component exposes only the current event; server-returned management permissions still gate host tools. The drawer is local UI state and does not own the world canvas or media room.

Camera tiles use each avatar's projected head position, including the host, instead of a shared fixed stage coordinate. The existing media owner and track routing are preserved. Stage presentation opens only on a local explicit action. Lighting uses the existing two fixtures with inexpensive additive, feathered beam meshes; permissions and synchronized preset/intensity semantics are unchanged.

World readiness is the first rendered coherent local scene (or the existing map fallback), following geography availability. Public bundled geography requests are coalesced in a four-entry memory cache; no user, entitlement or presence data is cached. Country flags derive from canonical destination country metadata through one helper. Business cards continue using the existing attributed business endpoints and omit absent optional fields.

No new seat state is introduced: auditorium sit/stand is not currently implemented and remains a post-launch enhancement. Browser viewport and synthetic-media tests must not be represented as physical-device or production-provider acceptance.

Role moderation keeps permission reconciliation and its blocking database commit in one worker-thread operation. The ASGI event loop must remain available to complete competing requests while a commit waits for a lock. This preserves the existing authorization, current-revision provider update and transaction boundary without adding retries or changing database configuration.
