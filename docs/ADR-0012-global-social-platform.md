# ADR 0012: Global discovery, demand, mobility and attributed businesses

Date: 2026-09-25. Status: implemented; live acceptance tracked separately.

Continue the existing FastAPI modular monolith, SQLAlchemy database, Redis/WebSocket presence, Next consumer/business/admin routes and existing LiveKit sessions. No replacement services, credentials, reward ledger, messaging model or geography engine.

## Destinations and demand

`Destination` extends the installed location catalogue with flags, public/joinable metadata, lifecycle and owner-controlled thresholds. The 28 international names and 19 future request locations are catalogue entries, not invented playable worlds. They remain REQUESTABLE without installed approved map data. Reviewed `backend/data/world-manifest.json` entries can install maps into the shared engine; installation starts IN_PREPARATION and Super Admin activation remains explicit. World access continues through the existing four-Starter-World/share-unlock ledger. Existing entitlements are untouched.

The existing unique CityInterest table records explicit interest. Destination-row locking serializes goal qualification. A qualified city never grants access or starts a world. Opaque request links, idempotent share records, opens and explicit vote conversions are independent of Share-to-Unlock and referral rewards.

## Mobility and safe escape

RentalAsset and RentalLease are extensions of existing Presence and the immutable Credits ledger. Asset-row locking prevents duplicate vehicle occupation; user locking prevents concurrent rentals and duplicate charges. Historical leases retain the agreed name, price and handling values. Existing paid/welcome vehicle entitlements provide zero-cost pickup during their validity. The old unrestricted mode-rental route now directs clients to configured pickup points. Speed/acceleration/braking and swept collision are authoritative. Rentals support one rider per vehicle; existing buses remain the multi-passenger service.

Water activities are opt-in mapped polygons, with holes excluded and a stored safe shore. Only the configured Willen Lake virtual recreation zone is seeded. Swimming does not exclusively reserve the entire zone. Boat assets are exclusive. No real-world water safety or permission is implied.

Interior visits survive expired presence. Exit reconstructs a safe outdoor position even after closure/disconnect and is idempotent, without payment or cooldown. A physical doorway and an independent UI Exit remain available. Mall store entry preserves the original exterior return point.

## Businesses

Unclaimed licensed map listings use the existing Business identity with nullable ownership and an additive BusinessSpatial profile. No artificial merchant/user account is created. BusinessMember extends existing tenant checks for authorised managers. Rewards still require existing verified merchant campaigns; importing a map listing does not create rewards, offers or verified ownership.

OSM enrichment for Midsummer Place uses relation 1650413 and preserves its inner ring. Known points within the mapped mall polygon are associated with its directory; uncertain placement stays uncertain. The Body Shop's supplied OSM point is outside that polygon and is not forced into it. Source data and acquisition URLs are retained in `business-enrichment.json`. Unknown websites, descriptions and opening hours are omitted. Public cards offer sourced links, coordinate-based directions, virtual category templates, and a disabled Coming Soon assistant. No AI runtime is invoked.

## Gifts and reactions

Gifts resolve an existing consented conversation family or live event. Recipient membership, blocks, price quote and balance are checked server-side. One idempotency ID creates one immutable wallet debit and delivery record; the recipient receives no arbitrary Credit transfer. Free reactions have a server-side rate limit. Shared controls are added to current chat/media/event surfaces without replacing their layouts. Catalogue edits do not mutate historical receipts.

## Operations and migration

`fj25_global_expansion` and `fk25_social_mobility` are additive, apart from relaxing Business.owner_id nullability. The business funds constraint is explicitly preserved during SQLite table recreation; PostgreSQL uses an in-place nullability alteration. Financial rows are not reset. Inventory seeds are idempotent. The deployment readiness window accommodates first-time imports, while the previous Railway deployment remains available until health checks pass. No new Railway service or database is required.
