# ADR 0020 — Outdoor exploration speed and XP mobility

2026-10-01. Scope: authenticated outdoor walk/run and car/bike/bus payment currency only. The user approved raising bike/car speed ceilings to preserve the requested hierarchy at three times the previous outdoor speed. Electric bikes follow the bike policy. Scooter, boat, swim, gifts, venues and other purchases retain their previous currencies.

## Movement

The prior release already removed overlapping fallback requests and matched outdoor walking to Preview. Its 12.5 m/s walk and 23.4375 m/s run caps were still below the newly requested exploration pace. A shared `normalWorldMultiplier: 3` applies only when Presence.zone_id is `world`, including acceleration so time to reach target remains 0.24 seconds. New full-input outdoor targets are 37.5/70.3125 m/s. Preview and building/event speed constants remain unchanged. Bike/e-bike/car floors are 84/93/120 m/s. Existing vehicle controls, braking, collision stepping, ownership and bus schedules remain unchanged. Higher vehicle top speed consequently takes longer to brake with the unchanged brake rate.

The authoritative 0.3-second movement time cap, idle-time reset, normalized inputs, socket sequencing, fallback serialization and swept collision stepping are unchanged. No city-specific speed overrides exist. Fixed-route browser evidence compares actual authoritative displacement, not constants; walking uses the same 60% joystick strength because a sustained full-strength input intentionally transitions to run.

## Payments

`mobility_payments.py` centralizes the forward-only currency rule. Existing configured price/fare integers are retained 1:1 as XP amounts for cars, pedal/electric bikes and buses. No balances, prices, historical rows, rentals or tickets are rewritten. No schema migration is required. New rental snapshots include their currency, and new XP debits use car_rental_xp, bike_rental_xp and bus_ticket_xp kinds in the existing immutable ledger. Existing completed Credit records retain their currency and kind.

Both endpoints retain the user-row lock across eligibility validation, debit and rental/ticket creation. The ledger retains unique user/currency/idempotency keys and nonnegative-balance constraints. Rental UUID retries return the old lease, another UUID cannot charge while a lease is active, and bus user/vehicle uniqueness prevents a second purchase under a new UUID. Old-page Credit quotes are rejected before charging XP. Existing old rental/ticket retries return before the new currency validation. Insufficient XP reports the exact shortfall and never falls back to Credits. UI returns users to exploration to earn XP.

## Validation gates

Before/after fixed-route measurements are stored under docs/evidence/outdoor-xp-2026-10-01. Tests cover concurrency, same/different request IDs, stale currency quotes, zero balances, historical rentals and remaining Credit mobility. Existing full CI (including mapped collision checks, multiuser city tests, media/layout regressions, migrations and builds) remains mandatory before updating the existing Railway service. Browser viewport emulation is not a physical-device certification; authenticated production transactions require an authorized existing test account.
