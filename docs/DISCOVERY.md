# City discovery, waiting lists and passport

`GET /api/cities` returns supported London/Birmingham/Milton Keynes and explicitly unavailable future cities, with country/region fields and actual persisted interest counts. These records describe availability, not real city population or a licensed navigation graph. `POST /api/cities/{city}/interest` and DELETE use authenticated user identity; composite primary keys prevent duplicate interest. Users can inspect only their own subscriptions through `GET /api/cities/interests`. Counts start at zero; there is no fabricated unlock threshold or email notification claim.

`GET /api/passport` returns only the current user's earned virtual-city stamps. A trusted server city-enter hook records one stamp per user/city; there is no client grant route. These stamps do not verify physical travel. Account export and deletion must include `passport_stamps` and `city_interests`.

`GET /api/people/search?q=` searches usernames with literal wildcard escaping, output bounds, block filtering and conservative privacy filtering. Private email, GPS, session, role and consent fields are omitted. Ghost, Zone and Event users are excluded from global search; Friends Only requires a friendship. The caller must be authenticated. `GET /api/world-provider` explicitly describes the local procedural renderer; it is not an external map integration.

Validation: four local SQLite tests passed for unique/reversible real interest counts, privacy-safe search, private/idempotent server-earned stamps and truthful renderer metadata. PostgreSQL concurrency and integrated browser routes remain additional acceptance checks. No new PostGIS geometry schema, AI FAQ provider or waiting-list outbound notification delivery is claimed.
