# Staging snapshot contention and release completion

## Evidence and decision

The failed staging exploration run `42316968692` contains HTTP 500 world-entry
responses and delayed neutral-input acknowledgements. Read-only Cloud Run
diagnostics from run `42519694332`, against revision
`mindaam-staging-00025-p4h`, contain User row lock timeouts in realtime movement,
a world snapshot lock timeout, exhausted request connection pools and stale
Presence updates. The diagnostic log window is bounded; it does not establish
the first chronological failure in every district job.

A snapshot previously kept its authoritative player lock throughout the large
rendering read model. The correction refreshes and locks Presence after locking
User, performs heartbeat/expiry/interior repairs, then commits before rendering
reads for GET and realtime snapshots. Mutation callers retain their enclosing
transaction. PR #6's nonblocking User lock and narrow PostgreSQL `55P03` handling
remain: stale moving impulses are discarded, and an unsuperseded neutral input
can retry. Collision, movement timing, release deadlines and authorization are
unchanged. A PostgreSQL test blocks rendering and requires a concurrent
authenticated movement and stop to complete before rendering is released.

## Additive completion

Walk/run configuration permits up to 100 m/s with walk <= run. Default speeds
remain 2 and 4.6875 m/s. The existing server integration, diagonal normalization,
elapsed-time cap, collision sweep and auditorium audience boundary still apply.
This changes the configurable ceiling, not the deployed setting.

The existing 36 auditorium chairs gain server-owned occupancy. A stationary
approved attendee within 0.85 m of a chair can sit after 0.8 s. Movement stands;
venue exit releases occupancy. One unique event/chair and one unique user key
arbitrate competing transactions. An insert must return its chair number before
reporting success; driver-dependent rowcount is not evidence of insertion.
Snapshots synchronize the pose using existing sockets. No media, stage or
organizer permission is granted by a chair. Migration `fy08_auditorium_seating`
adds a table without modifying existing users, events, balances or properties.

Super Admin user details include real property inventory and account KPIs.
Profile corrections are limited to display name, biography, languages and theme,
require a reason and a matching reviewed profile, and preserve privacy fields.
The existing suspension and immutable XP adjustment mechanisms remain in use.
Record-page KPI aggregates apply the same filters as the table.

PC recovery accepts only an existing consumer Payment, with no caller-supplied
amount or provider ID. The server retrieves that Checkout Session from Stripe
using the existing environment credential, checks exact GBP amount and metadata,
successful PaymentIntent and captured, unrefunded, undisputed Charge, then
revalidates account and Payment under the webhook's User -> Payment lock order.
It reuses `payment:<payment-id>` in the existing immutable ledger. It cannot
credit a duplicate, refunded, disputed, mismatched or unverified purchase.
Purchase/ticketing enablement is untouched. Provider fixture tests are not live
Stripe acceptance, and an unavailable credential fails closed without issuance.

## Release boundary

PR #7's property implementation remains intact. The existing PR #6 is extended
with these corrections and synchronized with the actual main commit; no branch
history is discarded. CI, exact-image staging deployment, district exploration,
authenticated property/media acceptance and recovery/security gates must pass
before production consideration. Production still requires the separately
authenticated owner approval for that exact SHA and digest.
