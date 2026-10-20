# ADR 0014 — World movement, street rentals and shared exploration trails

## Decision

Keep the existing Presence, geography collision sweep, rental lease, wallet, collectible, mission and WebSocket models. Extend the existing socket with a versioned input/acknowledgement message, rather than replacing the transport or adding a second movement engine.

The old browser path ignored input whenever its previous HTTP request was still pending. At higher latency this dropped turns and releases and reduced travel speed. The socket accepts bounded intent at the existing UI cadence (~8 Hz); authentication, city/zone context, entitlement, elapsed time, collision and rental checks remain server owned. A two-element queue preserves an immediate press/release pair; overflow replaces the oldest pending intent instead of replaying an unbounded backlog. Live quick-tap checks exposed the one-slot collapse and prompted this correction. Processing is capped at 15 Hz with a 30-message/sec abuse ceiling; intent older than 350 ms is discarded. Authenticated HTTP remains a bounded fallback and retains the latest unsent intent. Snapshots cannot rewind newer movement.

A zero/released input stops pedestrian motion. Blur, hidden tabs, text focus, pointer cancellation and lost pointer capture clear held controls. Touch ownership is explicit. Pedestrian running accelerates from walking pace to the existing 13 m/s cap. The walk/bike/car/bus caps remain 6/18/32/46 m/s, respectively. Vehicle acceleration and braking reuse lease settings; right steering now turns in the correct direction. Visual interpolation/animation follows actual displacement.

Blocked movement generates rate-limited operational diagnostics after `WORLD_STALL_SECONDS` (default 2.5, bounded 1.5–10). Diagnostics contain virtual location and collision category, not device GPS. Unstuck remains the existing maximum-three-metre invalid-position recovery; a valid position cannot be teleported. Rentals use their existing safe Exit Vehicle path. This is a fallback, not evidence that every device movement issue has been eliminated.

## Parked vehicles

The original ornament placement is reproduced with stable per-instance identifiers. Eligible cars are backed by the existing RentalAsset table at the same position. Suitable nearby bikes share that model. Invalid car placements remain explicitly SCENERY_ONLY without a Rent action. There is one visual instance, not a decorative car plus a duplicate rental. Existing formal pickup assets remain intact. Existing wallet debits, policy consent, exclusivity, immutable lease price and idempotency are preserved.

## World content

`world_content.seed_world` locks the existing destination and provisions only when that destination has no collectible rows. Existing authored items, claims, missions, entitlements and ledger rows are not rewritten. The default new trail has 48 items (36 fruit, 12 gems), configurable through the existing `world_trails` config (12–96, optional per-destination overrides). The mission reuses existing 3-fruit/1-gem requirements and 30 Credits/50 XP.

Prepared positions are generated from each installed OSM map using the existing traversability/swept-collision rules, then selected away from driving lanes, water and mapped private property/path centres. A connected flood from the existing spawn prevents isolated item placement. Narrow routes use a finer grid. Coordinates retain full precision after a rounding defect was found at a collision edge. A map checksum and generator version invalidate obsolete prepared positions. Future ACTIVE transitions call this same provisioner. No copied city geometry, fabricated people/businesses or new currency is involved.

There is no new respawn or repeat-grant mechanism: the existing once-per-user claim semantics stay intact.

## Touch presentation

The mobile/tablet HUD has a compact location control, one Quick Actions menu, a collapsible Camera panel, preserved walk/run control, joystick, six-item navigation and optional minimap. Vehicle/journey controls are contextual; safe exits remain available in Hide Controls mode. Existing secondary panels close conflicting business/menu panels. Permanent mobile Rentals/Transit/advertising controls move out of the gameplay HUD; physical ad boards retain their action. Desktop controls and communication layouts are retained.

## Migration and rollback

`fm25_world_movement` adds one defaulted Presence speed column. Startup adds only missing shared content and rental identities, idempotently. Application rollback can leave the additive column and records intact; never delete claims, ledger entries or rentals to roll back UI code.

## Validation limit

Automated movement/collision/authorization tests are not proof of smoothness on a real phone or GPU. The cloud browser blocks local HTTP and file previews; no alternate browser or policy workaround was used. Production authenticated device/multi-user acceptance is still required.
