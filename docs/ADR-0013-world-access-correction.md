# World access correction — 2026-09-25

The initial international catalogue was incorrectly presented as a demand waiting list. This correction preserves the existing world-access tables, identity, maps engine, sessions, wallets and demand history.

* ACTIVE + owned: enter with the existing entitlement.
* ACTIVE + unowned: explicitly select a Starter World while fewer than four worlds are owned; otherwise record four valid share actions for permanent access.
* Future/inactive: request interest in a separate country/place form. Shares promote its request link and never count as votes or unlock progress.

Migration `fl25_world_access_correction` updates the 28 existing international destination IDs after their map bundles validate. It preserves slugs, metadata and previous interest rows. Existing four-share progress becomes an entitlement once; no entitlement, share action, referral or economic record is removed or reset. Activation is a one-time, explicitly requested launch migration; subsequent Super Admin settings are preserved by normal startup.

The 28 installed districts use bounded OpenStreetMap extracts, attributed under ODbL 1.0. These are stylised central districts, matching the existing UK adapter—not full-city coverage, photorealistic replicas or surveyed interiors. Source hashes, bounds, dates, feature counts and collision-safe spawns are recorded in the bundles and `backend/data/international-import-audit.json`. Reproduction uses `scripts/import-international.py`; no production runtime map-provider dependency is introduced.

The main explorer remains flat flag + destination. Country selection exists only in Request a new place. Curated future places load from the backend. Other suggestions normalize names, deduplicate under a shared lock, limit each user to three new suggestions per day, and remain private until admin review. Existing demand uniqueness, thresholds and QUALIFIED/preparation/activation gates remain separate from access.

Share actions retain their UUID idempotency, configured cooldown, per-destination progress and original opaque invite links. Copying or opening a composer is honestly described as an action, never a verified post or new signup. Native cancellation does not count; Instagram/Messenger/Telegram availability is device-dependent. The existing OG card and private-data-free invite landing remain in use.

Activation also requires the shared world inventory to start within existing readiness limits. Sorting candidate entrances before collision checks preserves the nearest walkable-shoulder result while avoiding exhaustive checks after the best result is known. Sixty source-backed UK/international entrance cases matched the previous implementation exactly. Bounded map caches accommodate the 45-world release; destination assets still load on demand in the consumer.

Validation: 179 backend regression tests passed, 13 frontend logic tests passed, and Next.js production build passed. Targeted correction coverage includes mixed UK/international choices, final confirmation, 0/4–4/4 share progress, duplicate submissions, independent progress, logout/login persistence, safe migration, truthful/stale presence, custom demand review and all 28 safe map spawns. Local first inventory startup improved from ~106 seconds to ~21 seconds. Live and physical-device acceptance must be reported separately; automation is not proof of every real-device journey.
