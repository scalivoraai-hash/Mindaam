# ADR 0023 — Living world and Grand Arena extension

Status: implemented locally; release gates remain open. Extends ADR 0017 and ADR 0020 within the existing modular application.

## Shared atmosphere and movement

Each city derives its virtual season and weather from a stable city seed and 300-second server-time bucket. A monotonic client clock advances between authoritative snapshots. Ambient traffic, sky objects, precipitation and seasonal shaders are cosmetic, bounded by local quality settings and never enter authenticated presence or rewards. No scheduled weather writes, paid streams or new service are introduced. Rain ambience is opt-in. Reduced effects are local; shared stage lighting remains host controlled.

The prior effective outdoor walk limit was 12.5 × 3 = 37.5 units/second. The new separate factor is 0.6, producing 22.5; walk acceleration receives the same factor. Outdoor running, vehicle settings, preview steps, interior movement and collision authority remain unchanged. Actual controlled-time movement tests compare both factors.

## Arena placement and discovery

One deterministic exterior per installed city uses conservative building, road, water, landmark and collectible clearance. Where necessary a pedestrian spur reaches a dedicated edge plaza. Reviewed coordinates are precomputed against installed geography, enrichment and trail hashes. A changed source invalidates that cache. Arena footprints do not grant access to buildings, rewards or other cities.

Arena event discovery is authenticated and refreshed separately every 30 seconds. Event lists are not attached to high-frequency movement snapshots. Public and invited/private visibility remains derived from existing Event/Attendee/social permissions. Billboards and ambient promotional banners use actual event records. Ambient spectators never affect online or attendance counts.

## Reservations, tickets and refunds

New auditorium events require a reservation. The server sets and preserves this requirement; submitted client flags cannot disable it. Historical events retain their prior optional-reservation contract. New selectable durations are 1/2/10/24 hours; historical 3/6/12-hour records and API values remain supported. Existing prices are preserved; new durations are unavailable until an admin supplies approved prices.

A city-local half-hour calendar resolves DST gaps and repeated times to distinct UTC instants. Destination-row locks serialize overlapping bookings. User/event locks, expected-price checks, UUID confirmation keys and the existing immutable ledger govern debits. Booking top-up never silently reserves a slot or debits again on return.

Tickets are unique per event/user, debit Credits once and are required for paid attendance and venue entry. Private guests require host approval before purchasing. Price, time, venue, visibility and capacity are protected after ticket sales. Cancellation appends idempotent ticket refunds and refunds an unstarted reservation; an upcoming paid event cannot evade refunds through the end action. Refund attribution restores only the purchased portion of mixed-source ticket spending. No creator transfers, settlement, cash-out or payment provider replacement is added.

The additive migration adds Event programme/ticket pricing and ticket entitlements. Existing ledgers and booking rows are not rewritten.

## Participation and authorised content

Polls and Q&A live in bounded Event metadata under the existing event lock. Voting requires active attendance and entitlement; moderation uses existing host/co-host authority. Creator profiles expose public events. Highlights require explicit organiser rights and participant-consent attestations and retain event visibility. There is no automatic recording.

Screening categories and licensing notes reuse authorised presentation and screen sharing. This is not DRM, geographic-rights enforcement, VOD or revenue distribution. Existing camera/microphone defaults, live publisher limits and primary presenter selection remain authoritative.

## Release boundaries

See the release acceptance matrix for actual evidence and unfinished checks. No final commit, CI, staging rollout or production promotion is represented by this ADR. GCP foundation, billing, DNS, original MyLilWorlds and Railway production are outside the changes.
