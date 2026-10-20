# ADR 0017 — Event presentations and bounded exploration

2026-09-30. Extends the existing Event/Attendee, LiveKit room, world input and immutable ledger. No new service, authentication, transport or social architecture.

## Presentation ownership and consent

Event presentation JSON stores the primary presenter and provider-confirmed screen/video-audio SIDs, plus a short pending-picker reservation and a heartbeat lease. Attendee screen approval is separate from speaking/stage role. Joining or being approved never starts capture. An explicit Share screen click invokes the browser picker; cancellation stops its temporary capture and preserves the previous presenter. The selected replacement is published and verified through the existing LiveKit server API before taking over the wall. Revocation updates source-level provider permissions without replacing the room or other users' microphone tracks.

Event-row locks serialize switches/revokes and permission reconciliation. Maintenance reads current permissions under that same lock rather than applying stale snapshots. Media tokens remain room scoped and short lived. Like the existing provider grants, self-hosted LiveKit tokens cannot be retroactively invalidated merely by updating permissions; the authenticated wall additionally accepts only the selected owner and verified SID. LiveKit Cloud supports token revocation. No captured media is stored by this feature.

Client playback is source and SID owned: camera remains in the avatar card, mic remains attached once, screen goes to the stage, optional screen audio has a separate playback element. Wall priority is authorized screen, existing speaker camera, then event artwork. The presentation viewer changes only local React state; no view mode endpoint or network message exists. Camera/microphone and room lifecycle remain owned by the original MediaPanel.

## Shared lighting

Existing two shadow-free venue spotlights receive a shared preset/intensity/target from Event state. A reusable canvas supplies title/description/status artwork. Slow waves and a low-contrast approximately 14-second pulse avoid strobing. Rounded seating uses two instanced draws for all 36 seats; the local venue fixture dropped from 240 to 110 draws while retaining one title texture and two lights. No extra shadow maps, reflection targets, heavy assets or per-frame API calls are introduced. Existing venue title, social actions and event shortcuts use a bounded column to avoid covering one another.

## Movement calibration

The preview has one input pace: 1.5 virtual metres each 120 ms, or 12.5 m/s. It has no independent run selector; the existing automatic animation interprets that pace as running. `shared/movement.json` preserves both preview values exactly. Authenticated run now matches 12.5; walk is derived using the already established 1.875 ratio (6.6667). Vehicle limits remain unchanged. The prior 3.2/6 pedestrian constants caused the mismatch. A 240 ms acceleration transition and an idle-first-input cap prevent a banked 300 ms leap. Preview collision, input, interpolation and gait behavior remain unchanged; authenticated collision continues to be server authoritative.

## Conversations

The request CTA derives pending/connected state from existing consent and active membership, including group peers. Rendering or media layout cannot reset it. Immediate local acknowledgement covers the interval before the next authoritative snapshot. Backend pair locks and existing-group detection make retries idempotent.

## Economy and reservations

Venue reservations are additive, optional and city scoped. Destination-row locking prevents overlap. The event creator confirms an admin price and UUID request; one debit and one reservation commit atomically. Purchased-credit eligibility is derived conservatively from historical ledger entries, consuming purchased balance first on spending. It does not create a wallet, convert XP or reinterpret earned Credits as purchases. Previously confirmed prices are immutable. Existing unreserved events retain their flow but cannot start across a paid reservation.

Consumer packs reuse the existing signed Stripe webhook and checkout idempotency. A catalogue edit preserves merchant products. Frontend quotes come from the server and are checked again before creating checkout. Missing provider credentials fail closed; a browser success URL never grants credits. Existing gift catalogue and ledger behavior are unchanged.

## Rotating collectibles

Authored objects and historical claims are preserved. Each active destination exposes a bounded, deterministic rotation on vetted existing trail points. Unclaimed rotations are not database rows. Only an authoritative, nearby claim materializes an instance; city and user locks plus existing uniqueness/ledger keys prevent duplicate rewards. Time windows, a global daily allowance and a minimum claim interval survive refresh, reconnect and multiple tabs. Old materialized instances remain immutable history and expire from view. The `origin` marker distinguishes these instances from authored content. Existing XP amounts and mission rules are reused.

## Validation and limits

New targeted permission, source-routing, movement, reservation, price-confirmation and rotating-claim tests accompany the changes. The production-build browser matrix is extended to host plus three receivers in London, Birmingham, Madrid, Dubai, Mumbai, New York and Sydney. CI uses synthetic browser camera/mic/desktop sources over real LiveKit/WebRTC; it is not physical iPhone/Android or real-screen picker certification. Production Stripe currently lacks its secret and webhook signing secret. CI run 36710128208 passed all 336 multiuser checks (48 per city), 229 backend tests, 31 frontend tests, migrations and production builds. A separate production-build responsive fixture checks existing event controls and host tabs. The final release additionally handles a failed credit-catalogue background refresh without an unhandled rejection. Existing-service deployment and live-provider/physical-device acceptance are recorded separately in the release report.
