# Versioned Movement & Transport settings

The existing configuration_versions table stores one movement_transport_v1 record.
No schema migration or new service is required. Until the first save, approved
outdoor defaults are walk 2 and run 4.6875 m/s. Existing effective rental settings
are preserved when creating the record; these become its immutable defaults.
The current code defaults are bicycle 84, electric bicycle 93, motorbike/city
scooter 34, car 120, boat 20 and swimming 3 m/s. Buses are scheduled passenger
transport and are not a manually controlled speed setting. Indoor venue and
public preview pacing remain unchanged.

Bounds (m/s): walk 0.5–4; run 1–8; bicycle 2–84; electric bicycle 2–100;
motorbike/scooter 2–45; car 5–120; boat 1–30; swim 0.5–5. Walk must be below run.
An existing approved rental maximum above these standard bounds is retained as
that movement type's ceiling, so initial configuration and default restoration
do not silently reduce existing speeds. It cannot be increased beyond that ceiling.
No client-provided speed or multiplier is accepted. Non-finite values and
unknown fields are rejected. Rental eligibility, price, duration, acceleration,
braking, collision and wallet snapshots are preserved.

Super Admin saves require the current version and a reason. Atomic insert-on-
conflict plus row locking serializes initial and later saves. Audit records retain
old/new values, actor, timestamp and version. Restore defaults or a previous
recorded version creates a new version. No history or balances are rewritten.

Server movement and existing lease controllers read the central record on every
input transaction. There is no cross-instance configuration cache to invalidate.
The existing post-commit Redis state revision invalidates world snapshots; idle
sockets refresh within the existing five-second maximum state-cache age. Both
world snapshots and movement acknowledgements carry the public version/speeds.
The existing client sends normalized intent, not independently calculated world
positions; rendering interpolates authoritative server positions. It therefore
cannot multiply the new speeds or race a separate prediction engine. Older
snapshots cannot overwrite a newer received configuration. A speed reduction
clamps the next server-integrated step; increases retain bounded acceleration.

Tests cover role denial, invalid bounds, stale saves, restoration/audit, measured
server displacement, active rentals, no commercial balance changes and actual
separate-admin/player browser updates. Browser acceptance uses explicitly local
fixtures; it is never evidence of production payment or owner authentication.
