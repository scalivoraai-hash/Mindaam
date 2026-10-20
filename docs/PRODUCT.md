PROJECT NAME
PULSEWORLD

TAGLINES
Consumer: "Your City. Alive."
Product: "The Real World. Multiplayer."
Business: "Turn Attention Into Footfall."
Investor positioning: "The Multiplayer Commerce Layer for Real Cities."

============================================================
YOUR ROLE
============================================================

You are acting as the autonomous Principal Engineer, Lead Game Engineer,
Solution Architect, DevOps Engineer, Security Engineer, QA Lead,
Product Engineer, UI/UX Engineer and Technical Documentation Lead
for PULSEWORLD.

Your responsibility is not to create a concept, prototype, mock-up,
static website or partial demo.

Your responsibility is to build a complete, runnable, production-oriented,
publishable web application/game from this repository.

Treat this as a real startup product intended for paying customers,
businesses, investors and public users.

You must:

1. Architect the platform.
2. Create the repository.
3. Create persistent project documentation.
4. Create the database.
5. Create migrations.
6. Implement backend APIs.
7. Implement frontend applications.
8. Implement realtime multiplayer.
9. Implement the 3D world.
10. Implement social functionality.
11. Implement game mechanics.
12. Implement rewards/economy.
13. Implement merchant/business functionality.
14. Implement admin functionality.
15. Implement moderation and anti-fraud.
16. Implement payments.
17. Implement analytics.
18. Implement automated tests.
19. Run tests.
20. Run applications.
21. Inspect the application visually where browser/computer tools exist.
22. Fix errors.
23. Repeat until all release gates pass.
24. Produce deployment infrastructure.
25. Produce deployment/runbooks.
26. Leave the repository ready for real API credentials and deployment.

Do not stop after creating scaffolding.

Do not stop after creating screens.

Do not stop after generating TODO comments.

Continue working through the entire product backlog until the full
defined release is implemented or an unavoidable external dependency
requires credentials/account approval from the owner.

If an external provider credential is unavailable, implement the complete
provider abstraction, test adapter and configuration path, document exactly
what credential must be supplied, and continue all work that does not
depend on the credential.

Do not replace difficult functionality with fake data simply to make a
screen look finished.

============================================================
0. NON-NEGOTIABLE ENGINEERING RULES
============================================================

This is a production application.

NEVER create:
- fake authentication
- fake payment success
- fake business visits
- fake wallet balances
- hard-coded logged-in users
- hard-coded business analytics presented as real
- buttons that do nothing
- placeholder API endpoints represented as finished
- frontend-only security controls
- client-authoritative rewards
- client-authoritative currency
- client-authoritative collectibles
- client-authoritative location verification

Development seed data is allowed only in an explicitly isolated
development environment and must never be confused with production data.

Every user-facing button must:
- navigate somewhere,
- open a functional action/modal,
- invoke an API,
- update state,
- or deliberately be disabled with a visible reason.

Every feature must include:
- database/schema impact
- migration
- backend/domain logic
- API contract
- authorization
- frontend workflow
- loading state
- empty state
- error state
- offline/retry behaviour where appropriate
- analytics events
- audit events where appropriate
- unit tests
- integration tests
- relevant E2E tests

Use server-authoritative security for all sensitive operations.

Never expose secrets to frontend bundles.

Never expose another user's precise real GPS position.

Never trust a browser-provided currency balance.

Never trust a browser-provided collectible result.

Never trust a browser-provided business-visit result.

Never trust payment success reported only by the browser.

Use idempotency for financial/reward-sensitive operations.

============================================================
1. PRODUCT DEFINITION
============================================================

PULSEWORLD is a location-aware multiplayer open-world social and commerce
platform based on real cities.

Users enter a 3D representation of real places.

Users can:
- create avatars
- explore cities
- walk
- run
- cycle
- use scooters
- drive vehicles
- later use virtual buses
- use trains between cities
- use virtual flights between countries
- teleport where entitlement allows
- see nearby virtual users
- wave
- follow
- become friends
- chat
- use realtime voice
- use LiveFace
- form groups/Crews
- join events
- collect fruits
- collect gems
- hunt treasure
- complete missions
- earn XP
- earn Pulse Credits
- receive merchant Pulse Perks
- discover businesses
- inspect products/services
- visit virtual shops
- visit real businesses
- verify physical visits
- earn rewards
- redeem merchant offers
- compete on leaderboards
- compete city-versus-city
- invite friends
- earn referral rewards
- collect city passport stamps
- travel together
- receive daily rewards
- customise avatars
- customise vehicles

Businesses can:
- register
- verify themselves
- claim locations
- create virtual stores
- add products
- add services
- publish offers
- fund Pulse Credits
- launch sponsored fruit drops
- launch sponsored gem drops
- create treasure hunts
- create Visit & Earn campaigns
- create booking campaigns
- create lead campaigns
- create events
- create flash offers
- sponsor missions
- sponsor zones
- sponsor City Battles
- display advertising in appropriate virtual surfaces
- view measurable campaign analytics
- measure virtual visits
- measure eligible physical visits
- measure redemptions
- measure attributable conversions where data is reliable

PULSEWORLD monetises through:
- Pulse+ subscriptions
- Pulse Credit packs
- business subscriptions
- merchant campaign spend
- sponsored missions
- sponsored gems
- sponsored fruit
- sponsored events
- sponsored city zones
- promoted businesses
- enterprise brand activations
- event commissions
- booking/referral commissions where appropriate
- cosmetics
- vehicle cosmetics
- virtual travel
- premium experiences

============================================================
2. LAUNCH MARKET
============================================================

Initial country:
United Kingdom.

Initial enabled cities:
- London
- Birmingham
- Milton Keynes

Architecture must support arbitrary:
- countries
- regions
- cities
- zones
- cells
- points of interest

without code forks.

Initial London hotspots:
- Soho
- Covent Garden
- Camden
- South Bank
- Oxford Street
- Hyde Park

Initial Birmingham hotspots:
- Bullring
- New Street
- Brindleyplace
- Broad Street
- Jewellery Quarter

Initial Milton Keynes hotspots:
- Centre:MK
- Xscape
- The Hub
- Campbell Park
- Stadium MK
- MK Central

Support future:
- Manchester
- Liverpool
- Leeds
- Bristol
- Edinburgh
- Glasgow

International architecture must already support future cities such as:
- Dubai
- Abu Dhabi
- Riyadh
- Paris
- Amsterdam
- Kochi
- Bengaluru
- New York

but do not hard-code assumptions around the UK.

============================================================
3. USER AGE AND SAFETY MODEL
============================================================

Initial public release is 18+.

Implement:
- age confirmation during onboarding
- configurable age-policy rules
- terms acceptance
- privacy acceptance
- community guidelines acceptance
- consent records
- timestamp/version of accepted documents

Do not attempt a child-oriented product in initial release.

============================================================
4. CORE USER JOURNEY
============================================================

Primary consumer flow:

Landing
→ Register/Login
→ Age Confirmation
→ Select City
→ Select Interests
→ Create Avatar
→ Configure Privacy
→ Receive Welcome Pack
→ Tutorial
→ Enter City
→ Explore World
→ See Other Users
→ Collect Fruit/Gems
→ Meet Users
→ Wave
→ Chat
→ Voice
→ LiveFace
→ Missions
→ Earn XP/Credits
→ Discover Business
→ Visit Virtual Business
→ View Offer
→ "Visit For Real"
→ Verify Business Visit
→ Earn Credits/Perk
→ Redeem Offer
→ Join Crew
→ Invite Friend
→ Travel
→ Join Event
→ Return For Daily Drop

The first-time experience must be understandable without documentation.

Target onboarding should be completable in approximately 60 seconds
excluding external verification latency.

============================================================
5. MAIN CONSUMER NAVIGATION
============================================================

Keep primary navigation simple.

WORLD
PEOPLE
EARN
LIVE
WALLET

Secondary features can be reached contextually.

WORLD:
- live country/city map
- open-world experience
- city activity
- hotspots
- businesses
- missions
- transport

PEOPLE:
- friends
- following
- nearby virtual users
- recent encounters
- Crews
- requests

EARN:
- daily rewards
- fruits
- gems
- treasure
- missions
- merchant campaigns
- referrals
- events
- sponsored opportunities

LIVE:
- live events
- flash events
- City Battles
- trending zones
- sponsored experiences

WALLET:
- Pulse Credits
- XP
- Pulse Perks
- transaction ledger
- entitlements
- subscriptions
- purchases

============================================================
6. HOME / LIVE CITY EXPERIENCE
============================================================

Create a highly attractive live home screen.

Example concepts:

"YOUR CITY IS ALIVE"

Show:
- current supported-city populations
- City Pulse scores
- live events
- trending districts
- reward opportunities
- friend activity
- sponsored drops
- active missions
- City Battles
- business offers

Do not falsely represent real-world population.

"Online" numbers mean actual PULSEWORLD presence.

Create City Pulse metric from configurable weighted signals:
- current active users
- active sessions
- interactions
- events
- missions
- business visits
- collectible activity
- merchant campaigns

============================================================
7. OPEN-WORLD 3D ENGINE
============================================================

Build a browser-first 3D open-world experience.

Preferred visual stack:
- CesiumJS
- Three.js / React Three Fiber where appropriate
- WebGL
- progressive WebGPU support where safely usable

Create provider abstractions for map/3D tiles.

Support:
- Google Photorealistic 3D Tiles through official supported APIs when
  valid credentials/licensing are provided
- alternative compatible Cesium/OSM-based visual sources where appropriate

Do NOT scrape map imagery.

Do NOT derive restricted datasets from map-provider imagery.

Keep gameplay/navigation data independent from imagery provider.

Use OpenStreetMap/openly licensed geospatial datasets or another licensed
routing source for gameplay paths where appropriate.

Implement:
- world loader
- city loader
- zone loader
- spatial cells
- avatar spawn
- third-person camera
- optional first-person view if performant
- orbit camera
- collision/navigation layer
- ground detection
- POI overlays
- business overlays
- mission overlays
- event overlays
- collectible overlays
- dynamic world objects
- interaction radius
- contextual interaction prompt
- LOD
- frustum culling
- entity pooling
- adaptive render distance
- client performance monitor
- quality presets
- low-performance fallback

Target:
- usable on modern desktop browsers
- usable on modern mobile browsers
- responsive PWA
- progressive quality based on device capability

Do not attempt unrealistic GTA-level physics.

Use constrained, production-feasible world movement.

============================================================
8. WORLD HIERARCHY
============================================================

Use:

World
→ Country
→ Region
→ City
→ Zone
→ Cell

Each cell can contain:
- users
- businesses
- POIs
- fruits
- gems
- treasure
- vehicles
- events
- missions
- campaign objects

Use PostGIS geometry types where appropriate.

============================================================
9. MULTIPLAYER REALTIME PRESENCE
============================================================

Create server-authoritative realtime presence.

Technology:
- WebSockets
- Redis for ephemeral/presence state
- backend authoritative validation

Presence includes:
- virtual world position
- orientation
- animation/movement state
- current city
- current zone
- current cell
- current vehicle
- availability state
- voice availability
- LiveFace availability
- optional public profile state

Do NOT transmit private precise GPS to other players.

Implement spatial interest management.

Example:
close entities → high update frequency
medium distance → reduced update frequency
far entities → very low frequency or aggregate only

Do not broadcast every London player to every London client.

Implement:
- reconnect
- heartbeat
- stale presence removal
- state reconciliation
- movement sanity validation
- rate limiting
- concurrency testing
- graceful degradation

============================================================
10. REAL LOCATION VS VIRTUAL LOCATION
============================================================

Treat these as entirely separate domains.

REAL DEVICE LOCATION:
May be used with explicit consent for:
- verifying city eligibility
- optional "near me" experiences
- physical merchant visit verification
- campaign eligibility

VIRTUAL LOCATION:
Used for:
- avatar placement
- multiplayer visibility
- social interaction
- game mechanics

Other users must never receive the user's precise real-world coordinates.

Privacy settings:
- City Mode
- Zone Mode
- Friends Only
- Event Mode
- Ghost Mode

Implement consent and revocation.

Do not store precise location longer than necessary for its purpose.

Use configurable retention.

============================================================
11. AVATAR SYSTEM
============================================================

Implement configurable avatars.

V1:
- body presets
- face presets
- hairstyles
- skin tones
- tops
- bottoms
- shoes
- accessories
- animation states
- emotes

Store avatar configuration data rather than unique meshes where practical.

Support future:
- premium cosmetics
- branded cosmetics
- Founder cosmetics
- earned cosmetics

Animations:
- idle
- walk
- run
- wave
- celebrate
- collect
- talk
- drive
- sit
- event emotes

============================================================
12. USER PROFILE
============================================================

Profile includes:
- username
- display name
- avatar
- city
- optional public bio
- interests
- level
- XP
- badges
- City Passport
- Crew membership
- public activity preferences
- relationship controls
- trust state (private/internal aspects not exposed)
- Founder/early adopter badge if configured

Actions:
- Wave
- Follow
- Friend Request
- Chat
- Request Voice
- Request LiveFace
- Invite To Crew
- Travel Together
- Block
- Report

============================================================
13. SOCIAL GRAPH
============================================================

Implement:
- follows
- friendships
- friend requests
- blocks
- mutes
- recent encounters
- Crews/groups
- Crew roles
- invitations

Block must override:
- chat
- voice
- LiveFace
- discovery where appropriate
- direct invitations

============================================================
14. MESSAGING
============================================================

Implement real messaging.

Features:
- one-to-one
- group conversations
- Crew chat
- event chat
- typing indicator
- delivered/read state
- attachments if enabled safely
- emoji
- rate limiting
- mute conversation
- block/report
- moderation hooks

WebSocket realtime delivery with persistent storage.

Secure media uploads.

============================================================
15. VOICE
============================================================

Use WebRTC through LiveKit-compatible architecture.

Implement:
- request voice
- accept/reject
- mute
- unmute
- leave
- reconnect
- device selection
- permission denial handling
- mobile behaviour
- group rooms
- event voice rooms

Support spatial voice as an optional/zone capability.

Do not expose microphone without explicit user action/permissions.

============================================================
16. LIVEFACE
============================================================

LIVEFACE is a key differentiating feature.

Do NOT present it primarily as a conventional video-call page.

Flow:
User A approaches/interacts with User B
→ User A requests LiveFace
→ User B receives consent request
→ User B accepts
→ WebRTC/LiveKit video session begins
→ Small live video surface appears floating above/beside avatar
→ both avatars remain in the 3D world
→ both users can continue walking/exploring
→ optional expansion to medium/fullscreen

Modes:
- Mini LiveFace
- Floating LiveFace
- Full Screen
- Voice Only
- Avatar Only
- Group LiveFace

LiveFace MUST require mutual consent.

Credits may unlock usage capacity.
Credits must NEVER buy access to somebody else's camera.

Implement:
- free daily minutes configurable by admin
- subscription allowances
- additional paid Credit usage
- session metering
- robust reconnect
- camera disabled
- browser permission errors
- background mobile behaviour
- abuse/report control
- immediate terminate/block

============================================================
17. ECONOMY
============================================================

Implement THREE separate systems.

A. XP
- non-purchasable
- non-transferable
- no cash-out
- progression/reputation
- spendable for car/bike/e-bike rental and bus tickets (targeted 2026-10-01 requirement; configured prices retained)

B. PULSE CREDITS
- can be earned
- can be purchased
- used inside application
- no standard user cash-out
- no arbitrary peer-to-peer money-like transfer

C. PULSE PERKS
- merchant-funded real-world offers/rewards
- vouchers, discounts, experiences etc.
- controlled redemption

Do NOT combine these currencies.

============================================================
18. WALLET LEDGER
============================================================

Currency accounting must be server authoritative.

Use immutable/append-only ledger records.

Do NOT only store:
user.balance += amount

Create:
wallets
wallet_transactions
transaction metadata
source entities
idempotency keys

Transaction record should include:
- transaction UUID
- wallet
- user
- currency
- amount
- direction
- type
- source_type
- source_id
- previous balance snapshot
- resulting balance snapshot/cache
- idempotency key
- timestamp
- fraud status
- metadata
- audit information

Use database transactions and row locking or equivalent safe concurrency.

Test:
- duplicate requests
- concurrent rewards
- rollback
- repeated Stripe webhooks
- referral duplication
- mission reward duplication

============================================================
19. XP / LEVEL SYSTEM
============================================================

Create configurable progression.

Example levels:
Explorer
Adventurer
Local
Connector
Guide
Ambassador
City Legend

Do not hard-code thresholds throughout application.

Store configurable level rules.

XP can be earned for meaningful activity.

Avoid incentivising spam.

============================================================
20. DAILY DROP AND STREAKS
============================================================

Implement Daily Drop.

Example configurable schedule:
Day 1 → 10 Credits
Day 2 → 15
Day 3 → 20
Day 4 → 25
Day 5 → 30
Day 6 → cosmetic/mystery predetermined reward pool
Day 7 → 75

Admin configurable.

Implement:
- timezone rules
- claim eligibility
- streak reset
- missed days
- sponsored daily drops
- fraud controls
- transaction ledger entry
- push/in-app reminder

============================================================
21. WELCOME PACK
============================================================

Configurable first-time welcome pack may include:
- Pulse Credits
- XP
- free LiveFace minutes
- free bicycle uses
- free vehicle trial
- one travel ticket
- event ticket
- Founder perks when applicable

Do not use fixed values throughout code.

Entitlements should be server stored.

============================================================
22. REFERRAL SYSTEM
============================================================

Create unique referral code + referral link.

Share targets:
- WhatsApp
- SMS
- Copy Link
- standard Web Share API
- other platform-safe share links

Referral rewards must be progressive.

Example configurable milestones:
- verified registration
- avatar completed
- first mission
- next-day return
- first verified merchant visit
- first subscription if campaign allows

Do NOT pay all rewards immediately on signup.

Implement:
- referral attribution
- referral milestones
- reward history
- self-referral prevention
- device abuse detection
- velocity controls
- suspicious referral rings
- manual review
- admin configuration

============================================================
23. CREWS
============================================================

Users can create/join Crews.

Features:
- name
- logo
- description
- city
- owner
- moderators
- members
- invitations
- public/private
- XP
- leaderboard
- challenges
- Crew chat

Crew challenges:
- collect fruits
- collect gems
- complete missions
- attend events
- merchant visits
- city participation

============================================================
24. FRUIT COLLECTION — PULSE HARVEST
============================================================

Create "PULSE HARVEST."

Fruit objects:
- Apple
- Orange
- Banana
- Strawberry
- Mango
- other admin-defined fruit

Fruit appears:
- streets
- parks
- landmarks
- business zones
- events
- safe virtual paths

Never encourage users to physically trespass or stand in unsafe road areas.

Use fruit primarily as progression toward missions rather than direct
unlimited currency.

Example:
10 Apples + 5 Oranges + 3 Strawberries
→ Daily Fruit Basket completed
→ Credits/XP reward.

Fruit configuration:
- id
- type
- rarity
- world/city/zone/cell
- virtual coordinate
- start/end availability
- spawn rule
- respawn
- max claims
- per-user cap
- campaign
- mission
- sponsor
- visual asset
- reward relationship

============================================================
25. GEM COLLECTION
============================================================

Gems are rarer and more valuable game collectibles.

Types:
- common
- rare
- epic
- legendary
- city-specific
- sponsored
- Founder gem

Example London:
- Royal Ruby
- Thames Sapphire
- Soho Diamond
- Camden Emerald
- London Crown Gem

Example Birmingham:
- Bullring Ruby
- Brindley Sapphire
- Jewellery Quarter Diamond

Example Milton Keynes:
- MK Crystal
- Xscape Ruby
- Stadium Diamond

Implement:
- city collection albums
- progress indicators
- collection achievements
- XP rewards
- mission completion
- cosmetic unlocks
- optional limited Credit rewards

No paid randomized loot-box gambling mechanic.

============================================================
26. TREASURE HUNTS
============================================================

Implement:
- clue-based treasure hunts
- multi-stage routes
- city treasure hunts
- brand-sponsored treasure hunts
- business/store treasure hunts
- event treasure hunts

Possible rewards:
- XP
- Credits
- cosmetic
- Pulse Perk
- event ticket
- vehicle cosmetic

All rewards server validated.

============================================================
27. COLLECTIBLE SPAWN ENGINE
============================================================

Create server-authoritative spawn engine.

Support:
- scheduled spawn
- recurring spawn
- event spawn
- campaign spawn
- city spawn
- zone spawn
- sponsored spawn
- limited quantity
- per-user collection
- global depletion where configured
- respawn policy

Client receives available objects from server.

Client sends collection request.

Server validates:
- object exists
- object active
- user eligible
- correct world/cell
- virtual proximity plausible
- not previously claimed if prohibited
- cap not exceeded
- mission eligibility
- account status
- anti-cheat state

Server then writes collection + reward atomically.

============================================================
28. MISSIONS
============================================================

Mission framework must be generic.

Mission examples:
- collect X fruit
- collect specific gems
- visit locations
- enter virtual business
- verify physical merchant visit
- attend event
- travel by bike
- travel by car
- visit city zones
- complete treasure hunt
- join Crew activity
- complete sponsored experience

Mission fields:
- title
- description
- sponsor
- eligibility
- city/zone
- start/end
- steps
- rewards
- repeatability
- daily/weekly/event
- caps
- verification rules

Implement mission engine rather than hard-coding mission behaviour.

============================================================
29. CITY PASSPORT
============================================================

Implement digital PULSE PASSPORT.

Each city can issue:
- visited stamp
- mission-completion stamp
- Founder stamp
- event stamps
- seasonal stamps

Create:
- passport UI
- progression
- country/city collections
- achievements
- rewards

============================================================
30. LEADERBOARDS
============================================================

Create:
- user leaderboard
- Crew leaderboard
- city leaderboard
- collection leaderboard
- event leaderboard
- business engagement leaderboard where appropriate

Time windows:
- daily
- weekly
- monthly
- season
- all time

Use efficient server-side aggregation/caching.

Prevent leaderboard abuse.

============================================================
31. CITY BATTLES
============================================================

Implement configurable City Battles.

Example:
London vs Birmingham.

City score can include configurable weights:
- mission completions
- gems
- fruit
- events
- verified merchant visits
- social activity
- referrals

Campaigns can sponsor City Battles.

Show:
- live score
- remaining time
- contributing actions
- qualifying participants
- rewards

============================================================
32. EVENTS
============================================================

Implement event engine.

Event types:
- music
- DJ
- comedy
- quiz
- startup networking
- gaming
- university
- treasure hunt
- city festival
- car meet
- brand activation
- business event

Features:
- host
- title
- location
- virtual zone
- optional physical location
- date/time
- capacity
- RSVP
- ticket
- chat
- voice
- LiveFace
- mission
- collectible drops
- sponsor
- moderation
- event analytics

============================================================
33. TRANSPORT
============================================================

Create extensible transport engine.

V1 supported:
- walking
- bike
- scooter
- car

Later-capable but implement if feasible within release:
- bus
- train
- flight
- teleport

Do NOT attempt full GTA physics.

Use practical route-constrained world movement.

============================================================
34. WALKING
============================================================

Controls:
Desktop:
- WASD
- mouse camera
- optional click-to-move

Mobile:
- virtual joystick
- swipe camera
- tap destination where appropriate

Use walkable navigation paths.

============================================================
35. BIKES / SCOOTERS
============================================================

Implement:
- rental
- ownership where configured
- speed
- routes
- Credit pricing
- free entitlements
- mission integration
- customisation

============================================================
36. CARS
============================================================

Implement road-constrained car experience.

Features:
- vehicle catalogue
- owned vehicles
- rented vehicles
- basic steering
- acceleration/braking
- route/path constraints
- visual customisation
- number plate cosmetic
- skins
- wheels
- branded vehicles
- missions

Do not require full real-world traffic simulation for first release.

============================================================
37. BUS
============================================================

If included in first release:
- scheduled virtual routes
- boarding
- seating
- passengers
- social voice/chat
- stops
- arrival
- mission hooks

Otherwise fully prepare domain model and feature flag.

============================================================
38. TRAIN
============================================================

City travel concept:
London → Birmingham
London → Milton Keynes etc.

Virtual journey time may be gamified and shorter than reality.

Features:
- station
- ticket
- waiting
- boarding
- carriage
- other players
- social interaction
- arrival
- City Passport update

============================================================
39. FLIGHTS
============================================================

Architecture should support virtual international flights.

This is a social/game experience, NOT a flight simulator.

Flow:
airport
→ check-in experience
→ lounge
→ boarding
→ aircraft social scene
→ arrival city world

Feature-flag if not ready for initial UK release.

============================================================
40. TELEPORT
============================================================

Allow configurable teleport:
- entitlement based
- premium benefit
- Credit cost
- event teleport
- friend teleport
- admin configurable

============================================================
41. TRAVEL TOGETHER
============================================================

Allow friend/party travel.

Invite:
"Travel Together"

Accept:
party shares virtual route/transport where feasible.

============================================================
42. BUSINESS PLATFORM
============================================================

Create completely functional BUSINESS PORTAL.

Recommended domain:
business.pulseworld...

Navigation:
Dashboard
Store
Products & Services
Offers
Get Customers
Campaigns
Missions
Fruit & Gem Drops
Visit & Earn
Rewards
Events
Customers
Analytics
Billing
Team
Settings

============================================================
43. BUSINESS ONBOARDING
============================================================

Flow:
Business Sign Up
→ Business Details
→ Search/Add Location
→ Claim Business
→ Ownership Verification
→ Select Plan
→ Create Store
→ Products/Services
→ First Offer
→ First Campaign
→ Publish

Create verification states:
pending
verified
rejected
needs_information
suspended

Do not let unverified merchants perform sensitive campaign actions if
policy prohibits it.

============================================================
44. BUSINESS TEAMS
============================================================

Roles:
Business Owner
Business Admin
Marketing Manager
Store Manager
Analyst
Staff

Use RBAC on backend.

Support multiple locations.

============================================================
45. VIRTUAL BUSINESS STORE
============================================================

Business page/world interaction:

- logo
- imagery
- description
- opening times
- products
- services
- menus where relevant
- offers
- missions
- events
- Visit For Real
- directions
- booking
- website
- chat/contact where enabled
- follow business
- AI assistant
- reward opportunities

Provide a virtual storefront/interactive marker inside world.

============================================================
46. PRODUCTS AND SERVICES
============================================================

Business can create:
- product
- service
- category
- title
- description
- media
- price
- availability
- external purchase URL where allowed
- booking URL
- promotion
- reward relationship

Do not build fake checkout for merchant products unless direct commerce
is explicitly implemented.

============================================================
47. BUSINESS AI ASSISTANT
============================================================

Create optional merchant AI assistant framework.

Use provider abstraction.

Assistant can answer only from:
- merchant-approved data
- merchant content
- approved FAQs
- configured policies

Examples:
- opening times
- products
- services
- menu
- availability information
- campaign details
- booking instructions

Do not hallucinate business facts.

If answer not grounded:
"I don't have that information."

============================================================
48. GET CUSTOMERS
============================================================

Use merchant-friendly terminology.

Campaign wizard:

STEP 1 GOAL
- physical visits
- bookings
- leads
- sales/conversions
- awareness
- event attendance
- virtual store visits

STEP 2 AUDIENCE
- geographic eligibility
- interests
- legal age constraints
- time windows

STEP 3 INCENTIVE
- Pulse Credits
- Pulse Perk
- discount
- item/reward

STEP 4 BUDGET
- total
- daily
- per-result limits

STEP 5 VERIFICATION
- geofence
- PulsePoint QR
- merchant confirmation
- booking
- POS integration future

STEP 6 PREVIEW

STEP 7 PAYMENT

STEP 8 LAUNCH

============================================================
49. VISIT & EARN
============================================================

FLAGSHIP BUSINESS FEATURE.

Consumer sees:
"Visit Joe's Coffee today → +30 Credits + 10% off"

Flow:
campaign discovery
→ user selects campaign
→ "Visit For Real"
→ optional external navigation
→ user enters valid geofence
→ app confirms eligibility
→ user scans PulsePoint dynamic QR
→ backend verifies everything
→ business visit recorded
→ reward transaction generated
→ perk generated where applicable
→ business analytics updated

Never reward GPS alone for high-value campaigns unless specifically
configured and fraud risk is accepted.

============================================================
50. PULSEPOINT
============================================================

Build merchant verification system called PULSEPOINT.

Support:
- rotating signed QR
- future NFC
- future beacon
- future POS integration

QR MUST NOT simply contain static business_id.

Create short-lived signed token containing appropriate claims such as:
- location/business
- campaign
- expiry
- nonce

Server validates:
- signature
- expiry
- replay
- merchant state
- campaign state
- user eligibility
- location eligibility where required
- per-user caps
- device/account risk
- previous redemption

Store verification event.

============================================================
51. BUSINESS FRUIT/GEM CAMPAIGNS
============================================================

Businesses can sponsor:
- virtual fruit
- virtual gems
- store gems
- route gems
- event gems
- treasure hunts

Examples:
"Find 5 gems in our virtual store"
"Visit store and collect Golden Gem"
"Fresh Fruit Week"
"30 Gems available between 3–5 PM"

Campaigns need:
- budget
- reward pool
- max claims
- schedule
- audience
- geography
- sponsor assets
- mission configuration
- analytics

============================================================
52. FLASH OFFERS
============================================================

Business can quickly launch:
- offer
- Credits
- limited quantity
- radius
- start/end
- redemption condition

Example:
"40 customer drop, 3 PM–5 PM."

Send relevant opt-in notifications.

Do not spam.

============================================================
53. BUSINESS ANALYTICS
============================================================

Track actual event funnel.

Examples:
CAMPAIGN_IMPRESSION
BUSINESS_OPEN
VIRTUAL_STORE_ENTER
OFFER_OPEN
OFFER_CLAIM
JOURNEY_START
GEOFENCE_ARRIVAL
PULSEPOINT_SCAN
VERIFIED_VISIT
REWARD_ISSUED
REDEMPTION
BOOKING
PURCHASE_ATTRIBUTED

Do not fabricate revenue.

Only show attributable sales when integration/data supports the claim.

Dashboard:
- impressions
- unique users
- virtual visits
- offer claims
- journey starts
- verified visits
- redemptions
- bookings
- attributed revenue where available
- campaign cost
- CPA/CPV where applicable
- repeat visits
- followers
- trends

============================================================
54. BUSINESS PRICING / ENTITLEMENT ENGINE
============================================================

Plans must be admin configurable.

Initial illustrative tiers:
Basic
Starter
Growth
Pro
Enterprise

Do not hard-code prices into business logic.

Store:
- plan
- price
- currency
- billing interval
- entitlements
- limits
- effective dates

============================================================
55. CONSUMER SUBSCRIPTION
============================================================

Create Pulse+.

Entitlements configurable:
- monthly Credits
- increased LiveFace allowance
- travel discounts
- cosmetics
- special missions
- badge
- premium experiences

Do not make core social access pay-to-win.

============================================================
56. PAYMENTS
============================================================

Use Stripe-compatible production architecture.

Consumers:
- Pulse+
- Credit packs
- eligible event tickets
- eligible premium content

Businesses:
- subscriptions
- campaign budgets
- upgrades

Implement:
- Stripe Checkout where appropriate
- Customer Portal
- webhook endpoint
- webhook signature verification
- idempotent event processing
- subscriptions
- invoices
- failed payments
- cancellations
- refunds where supported
- entitlement updates

Frontend payment-success page must never be source of truth.

Webhook/backend verification is source of truth.

Use Stripe test mode for development.

============================================================
57. CREDIT PACKS
============================================================

Admin configurable packages.

Do not hard-code final commercial pricing.

Create product catalogue and entitlement.

============================================================
58. PULSE PERKS / REDEMPTION
============================================================

Merchant Perks:
- percent discount
- fixed discount
- free item
- upgrade
- free trial
- appointment promotion
- experience

Implement:
claim
→ eligibility
→ one-time/rotating QR or secure code
→ merchant validation
→ redemption
→ status
→ analytics

Prevent screenshots/replay where possible.

============================================================
59. SPONSORED ADVERTISING
============================================================

Do not make intrusive banner ads the core model.

Support native virtual-world advertising:

- sponsored zones
- sponsored missions
- sponsored gem drops
- sponsored fruit drops
- sponsored Daily Drop
- sponsored City Battle
- virtual billboards
- branded vehicles
- sponsored transport
- brand events
- promoted stores
- branded collectibles

Clearly label sponsored content where required.

============================================================
60. NOTIFICATIONS
============================================================

Build:
- in-app notifications
- email where appropriate
- push architecture where PWA/browser supports
- preference controls

Examples:
Daily Drop
friend request
Crew invite
LiveFace request
voice request
event reminder
campaign reward
merchant offer
City Battle
referral milestone

Users control marketing notifications separately from essential service
notifications.

============================================================
61. MODERATION
============================================================

Create moderation platform.

User controls:
- block
- mute
- report
- leave
- disable LiveFace
- disable voice
- Ghost Mode

Report categories:
- harassment
- hate
- sexual content
- impersonation
- fraud
- spam
- threatening behaviour
- inappropriate video
- unsafe business
- other

Admin/moderator:
- moderation queue
- evidence
- history
- actions
- warning
- temporary restriction
- feature restriction
- suspension
- ban
- appeal state
- audit log

============================================================
62. TRUST AND ABUSE
============================================================

Create private trust/risk system.

Signals may include:
- account age
- verified state
- spam velocity
- reports
- confirmed abuse
- blocks
- suspicious referral behaviour
- device anomalies
- location anomalies
- payment chargeback
- QR abuse

Do not expose internal fraud score to normal users.

============================================================
63. ANTI-FRAUD
============================================================

Protect:
- referrals
- wallets
- collectibles
- business visits
- PulsePoint
- rewards
- campaigns
- payments
- leaderboards

Implement:
- rate limits
- idempotency
- duplicate-claim prevention
- impossible movement detection
- device/account correlation hooks
- suspicious velocity
- QR replay detection
- signed tokens
- per-campaign caps
- per-user caps
- merchant abuse signals
- manual review queue

Do not claim to perfectly detect GPS spoofing.
Create layered detection architecture.

============================================================
64. ADMIN PORTAL
============================================================

Create a complete platform admin portal.

Navigation:
Dashboard
Users
Businesses
Business Verification
Countries
Cities
Zones
Cells
POIs
World Objects
Fruit
Gems
Spawn Rules
Treasure Hunts
Missions
Campaigns
Visit & Earn
PulsePoints
Wallets
Transactions
XP
Rewards
Perks
Referrals
Crews
Events
Vehicles
Transport
Subscriptions
Payments
Sponsors
Moderation
Fraud
Notifications
Analytics
Feature Flags
Configuration
Audit Logs
System Health

Roles:
Moderator
Finance Admin
City Manager
Business Ops
Support
Platform Admin
Super Admin

Backend RBAC mandatory.

============================================================
65. CITY OPERATIONS
============================================================

City manager dashboard:
- online users
- zones
- world health
- events
- missions
- businesses
- collectible activity
- City Pulse
- City Battle
- moderation incidents
- campaign activity
- infrastructure health

============================================================
66. FEATURE FLAGS
============================================================

Implement server-controlled feature flags.

Examples:
liveface_enabled
vehicles_enabled
trains_enabled
flights_enabled
city_battles_enabled
physical_visit_enabled
ai_assistant_enabled
specific_city_enabled

Support staged rollout.

============================================================
67. CONFIGURATION SYSTEM
============================================================

Do not scatter commercial constants through source code.

Create configuration for:
- Daily Drop values
- XP rules
- referral rewards
- LiveFace free minutes
- LiveFace pricing
- vehicle pricing
- travel pricing
- mission rewards
- collectible limits
- Credit packages
- city availability
- subscription entitlements
- business entitlements
- campaign rules
- fraud thresholds

Use versioned/effective-dated config where appropriate.

============================================================
68. ANALYTICS
============================================================

Implement analytics abstraction.

Track:
app_opened
registration_started
registration_completed
onboarding_completed
city_selected
city_entered
world_loaded
zone_entered
avatar_seen
wave_sent
friend_requested
conversation_started
message_sent
voice_requested
voice_started
liveface_requested
liveface_started
fruit_seen
fruit_collected
gem_seen
gem_collected
mission_started
mission_completed
daily_reward_claimed
referral_shared
referral_milestone
crew_joined
event_joined
business_viewed
virtual_store_entered
offer_claimed
journey_started
merchant_visit_verified
perk_redeemed
credits_earned
credits_spent
subscription_started
subscription_cancelled
payment_failed

Respect privacy/consent requirements.

============================================================
69. KEY PRODUCT METRICS
============================================================

Prepare dashboards/data for:
DAU
WAU
MAU
DAU/MAU
D1 retention
D7 retention
D30 retention
sessions/user
average session duration
interactions/user
new friends/user
missions/user
fruits/user
gems/user
referral rate
viral coefficient inputs
Credits earned/spent
LiveFace sessions
verified business visits
redemptions
merchant retention
consumer ARPU
merchant ARPU
campaign performance

Create internal metric:
CITY LIQUIDITY

Definition:
Probability that an active user entering a supported zone discovers a
meaningful interaction/opportunity within five minutes.

Create:
PULSE-ATTRIBUTED FOOTFALL

Verified qualifying merchant visits generated through PULSEWORLD.

============================================================
70. AI PLATFORM
============================================================

Create provider-independent AI gateway.

Do not tightly couple business logic to one LLM vendor.

AI use cases:
- city guide
- event discovery
- business assistant
- opt-in interest discovery
- support assistance
- moderation triage
- future translation

AI must not reveal private location.

People discovery must respect explicit discovery/privacy settings.

Business assistant must be grounded in merchant content.

Create logging/cost controls.

============================================================
71. SEARCH
============================================================

Support search:
- people where privacy allows
- cities
- zones
- businesses
- products
- services
- missions
- events
- Crews

Use PostgreSQL initially if sufficient.
Prepare abstraction for OpenSearch/other scale system later.

============================================================
72. DATABASE
============================================================

Use PostgreSQL + PostGIS.

Design full normalized production schema.

Expected domains/tables include at minimum:

users
profiles
user_devices
user_sessions
user_consents
avatars
avatar_items
user_avatar_items

countries
regions
cities
zones
world_cells
points_of_interest

user_presence
location_consents
location_verifications

follows
friendships
friend_requests
blocks
mutes

crews
crew_members
crew_invites
crew_challenges

conversations
conversation_members
messages

voice_sessions
liveface_sessions
media_sessions

wallets
wallet_transactions
wallet_idempotency

xp_events
levels
badges
user_badges

daily_reward_rules
daily_reward_claims

referrals
referral_events
referral_rewards

collectible_types
collectible_spawns
collectible_instances
collectible_claims
collection_sets
collection_progress

missions
mission_steps
mission_rewards
mission_progress

businesses
business_locations
business_users
business_verifications

products
services
offers

campaigns
campaign_targets
campaign_budgets
campaign_events

pulsepoints
pulsepoint_tokens
visit_verifications
business_visits

perks
perk_claims
redemptions

events
event_attendees
event_tickets

vehicles
vehicle_types
user_vehicles
vehicle_rentals
journeys

passport_stamps
user_passport_stamps

leaderboards
leaderboard_entries
city_battles
city_battle_scores

subscriptions
subscription_entitlements
payments
payment_events
invoices

notifications
notification_preferences

reports
moderation_cases
moderation_actions

risk_signals
fraud_cases

feature_flags
configuration_versions

audit_logs
analytics_events

Design additional tables when required.

Create:
- primary keys
- foreign keys
- unique constraints
- check constraints
- indexes
- PostGIS spatial indexes
- timestamps
- soft-delete only where appropriate
- proper hard-delete/anonymisation flows where legally needed

Use Alembic migrations.

============================================================
73. BACKEND ARCHITECTURE
============================================================

Use Python FastAPI.

Start as MODULAR MONOLITH.

Suggested modules:
auth
users
profiles
world
geo
presence
social
messaging
media
economy
rewards
referrals
collectibles
missions
businesses
campaigns
visits
perks
events
transport
payments
subscriptions
moderation
fraud
notifications
analytics
ai
admin
configuration

Create strong internal boundaries.

Do not prematurely split everything into microservices.

Create service/repository patterns pragmatically, not over-engineered.

Use:
- Pydantic
- SQLAlchemy
- Alembic
- async where justified
- dependency injection patterns suitable for FastAPI
- OpenAPI

============================================================
74. FRONTEND ARCHITECTURE
============================================================

Use monorepo.

Recommended:

pulseworld/
  apps/
    consumer-web/
    business-portal/
    admin-portal/
  backend/
    api/
  packages/
    ui/
    types/
    api-client/
    config/
    analytics/
  infrastructure/
  docs/

Use:
- Next.js
- React
- TypeScript
- Tailwind CSS
- accessible reusable UI components
- TanStack Query
- Zustand or equivalent for appropriate client state
- Zod
- generated/typed API client where practical

Do not duplicate business rules on frontend.

============================================================
75. DESIGN SYSTEM
============================================================

Visual direction:

Premium, immersive, futuristic but not childish.

Dark immersive world UI with translucent HUD surfaces.

Use:
- strong typography
- clear hierarchy
- subtle glow/activity indicators
- responsive panels
- city pulse visualisation
- game-quality microinteractions
- accessible contrast
- reduced-motion preference
- keyboard accessibility outside 3D movement context

Avoid:
- generic SaaS dashboard look in consumer world
- excessive gradients
- clutter
- inaccessible neon-on-black text
- gimmicky animation that harms performance

Create component library.

============================================================
76. RESPONSIVE / PWA
============================================================

Consumer app:
- desktop
- tablet
- mobile browser
- installable PWA

Implement:
- manifest
- icons placeholders/documented assets
- service worker strategy
- offline shell
- reconnect behaviour
- safe update strategy

Business/Admin:
desktop-first but responsive.

============================================================
77. AUTHENTICATION
============================================================

Implement production authentication architecture.

Support:
- email
- optional mobile OTP provider abstraction
- Google OAuth
- Apple OAuth where configured

Use secure sessions/tokens.

Implement:
- registration
- login
- logout
- refresh/session management
- device sessions
- logout all
- password reset if passwords used
- email verification
- account deletion
- suspension
- RBAC

Do not invent OAuth credentials.

Provide configuration instructions.

============================================================
78. API SECURITY
============================================================

All endpoints:
- validated
- authenticated where needed
- authorized on backend
- rate-limited where appropriate
- return structured errors
- audited where privileged
- use least privilege

Protect against:
- IDOR/BOLA
- injection
- XSS
- CSRF where applicable
- SSRF
- insecure uploads
- privilege escalation
- mass assignment
- sensitive data exposure
- broken object authorization

============================================================
79. FILE/MEDIA UPLOADS
============================================================

Use S3-compatible object storage.

Implement:
- signed uploads
- file type validation
- size limits
- malware scanning integration hook
- image processing where required
- private/public access rules
- media deletion lifecycle

============================================================
80. CACHE / REDIS
============================================================

Use Redis for:
- presence
- realtime ephemeral state
- rate limits
- cached leaderboards
- distributed locks where appropriate
- short-lived tokens
- queues only where appropriate

Persistent source of truth remains PostgreSQL for durable business data.

============================================================
81. BACKGROUND JOBS
============================================================

Use appropriate background processing for:
- notifications
- analytics aggregation
- campaign calculations
- leaderboard generation
- image processing
- expired object cleanup
- scheduled collectible spawns
- event reminders
- email

Select pragmatic technology compatible with Python/Redis.

============================================================
82. INFRASTRUCTURE
============================================================

Create production infrastructure code.

Preferred AWS deployment:

CloudFront
→ frontend hosting / Next.js deployment architecture

Application:
ECS/Fargate or another justified managed compute option

Data:
RDS PostgreSQL/PostGIS
ElastiCache Redis
S3
Secrets Manager / Parameter Store
CloudWatch/OpenTelemetry-compatible observability

Create Terraform.

Do not require Kubernetes for initial launch unless a compelling technical
reason exists.

Prepare autoscaling.

============================================================
83. ENVIRONMENTS
============================================================

Create:
local
test
staging
production

Use separate:
- database
- Redis
- object storage
- Stripe keys
- LiveKit keys
- map keys
- OAuth credentials

Never reuse production credentials locally.

Create .env.example without secrets.

============================================================
84. DOCKER
============================================================

Create:
- Dockerfiles
- docker-compose for local dependencies
- health checks
- production builds
- non-root containers where practical
- minimal images

============================================================
85. CI/CD
============================================================

Use GitHub Actions.

PR gates:
- formatting
- lint
- TypeScript typecheck
- Python typecheck
- unit tests
- integration tests
- migration validation
- dependency vulnerability scan
- secret scan
- build
- critical E2E

Branches:
feature
development
main

Support preview/staging deployments where deployment credentials exist.

Production requires explicit approval.

============================================================
86. TESTING
============================================================

Create comprehensive test pyramid.

UNIT:
business logic
economy
mission rules
referrals
collectibles
campaign rules

INTEGRATION:
database
API
Redis
Stripe webhook test mode
wallet concurrency
PulsePoint

E2E with Playwright:
registration
onboarding
enter city
collect fruit
collect gem
complete mission
claim Daily Drop
invite/referral flow where feasible
business registration
create campaign
consumer business discovery
Visit & Earn simulated/staging flow
perk redemption
Pulse+ checkout test flow
block/report

REALTIME TESTS:
presence
chat
reconnect
concurrent movement
voice room token authorization

============================================================
87. LOAD TESTING
============================================================

Create load-test scripts.

Test:
100
500
1,000
5,000
10,000 simulated relevant sessions where environment allows.

Measure:
API p50/p95/p99
WebSocket latency
connection count
Redis load
DB connection usage
CPU
memory
network
error rate

Document actual results from available environment.

Do not claim untested capacity.

============================================================
88. CLIENT PERFORMANCE
============================================================

Measure:
FPS
frame time
memory
JS bundle
3D asset load
network bandwidth
tile usage
entity count

Create quality levels:
Low
Medium
High
Auto

Reduce:
render radius
avatar complexity
effects
shadow quality
entity detail

on weak devices.

============================================================
89. OBSERVABILITY
============================================================

Implement:
- structured JSON logs
- correlation/request ID
- metrics
- tracing hooks
- error monitoring integration
- health endpoint
- readiness endpoint
- dependency status
- background job metrics
- payment webhook metrics
- WebSocket metrics

Never log:
passwords
raw payment details
access tokens
unnecessary precise GPS
sensitive private message content by default

============================================================
90. BACKUPS / RECOVERY
============================================================

Document and configure:
- RDS backups
- point-in-time recovery
- object storage versioning where appropriate
- restore procedure
- migration rollback philosophy
- disaster recovery runbook

============================================================
91. PRIVACY
============================================================

Build privacy by design.

Support:
- user data export
- account deletion/anonymisation
- privacy preferences
- consent records
- location consent
- marketing consent
- analytics preferences where required
- retention configuration

Prepare documentation for legal review.

Do not claim legal compliance has been certified merely because code exists.

============================================================
92. SECURITY REVIEW
============================================================

Before release perform internal adversarial review.

Specifically test:
- authentication bypass
- authorization bypass
- IDOR/BOLA
- admin privilege escalation
- business cross-tenant data leakage
- XSS
- SQL injection
- CSRF
- SSRF
- insecure redirects
- insecure uploads
- token leakage
- wallet duplication
- race conditions
- referral abuse
- PulsePoint replay
- payment webhook spoofing
- location privacy leakage
- WebSocket auth
- message enumeration
- leaderboard manipulation
- collectible farming
- secrets leakage

For every confirmed bug:
1. reproduce
2. create regression test
3. fix
4. rerun test

============================================================
93. BUSINESS TENANCY
============================================================

A business must never see another business's private data.

Enforce tenant boundaries in backend queries/services.

Test cross-business ID attacks.

============================================================
94. AUDIT LOGGING
============================================================

Audit important operations:
- admin changes
- wallet adjustments
- business verification
- campaign approval
- moderation actions
- refund
- subscription changes
- feature flag changes
- pricing/reward configuration
- manual visit/reward overrides

Audit logs should be append-oriented and protected.

============================================================
95. SEED / DEMO ENVIRONMENT
============================================================

Create useful seed data ONLY for local/staging development.

Example:
London test zones
Milton Keynes test zones
Birmingham test zones
sample merchant
sample missions
sample fruit/gems

Clearly mark demo data.

Production deployment starts without fake analytics/users.

============================================================
96. FIRST-TIME TUTORIAL
============================================================

Create interactive tutorial:

1. Move avatar
2. Rotate camera
3. Collect fruit
4. Collect gem
5. Wave to user/NPC tutorial element
6. Open EARN
7. View merchant
8. Understand Credits
9. Invite friend

Reward tutorial completion if configured.

============================================================
97. EMPTY WORLD PROBLEM
============================================================

Design for low initial density.

If few players are nearby:
- show missions
- collectibles
- events
- merchants
- trending destinations
- guided experiences

Do NOT populate fake human users pretending to be real.

NPC guides can exist but must clearly be NPC/AI.

============================================================
98. CITY UNLOCK SYSTEM
============================================================

Support future unavailable cities.

Example:
Manchester
8,421 / 10,000 interested

Users can:
- join waiting list
- invite people
- be notified when city opens

Do not fabricate counts.

============================================================
99. FOUNDERS / CROWDFUNDING SUPPORT
============================================================

Create optional Founder entitlement system suitable for legitimate
crowdfunding backers.

Possible:
- Founding Citizen badge
- Founder number
- Founder avatar cosmetic
- Founder vehicle skin
- Founder City Passport stamp
- defined Pulse+ entitlement
- defined Credit grant

Do not create investment/equity claims in application.

Admin can import legitimate entitlements.

============================================================
100. LANDING / MARKETING WEBSITE
============================================================

Create public marketing experience.

Pages:
Home
How It Works
Explore
For Businesses
Rewards
Safety
Pricing
Cities
Founders/Waitlist if enabled
About
Contact
Terms
Privacy
Community Guidelines

Hero:
"YOUR CITY. ALIVE."

Secondary:
"Meet people. Explore. Play. Earn rewards."

Business:
"Turn Attention Into Footfall."

Include live metrics only when backed by actual API data.

============================================================
101. SEO
============================================================

Create:
- metadata
- structured page titles
- sitemap
- robots
- social share cards
- accessible semantic content
- city landing-page architecture

Do not expose private world/user data to search engines.

============================================================
102. DOCUMENTATION
============================================================

Create and maintain:

/docs/PRODUCT.md
/docs/ARCHITECTURE.md
/docs/DATABASE.md
/docs/API.md
/docs/WORLD_ENGINE.md
/docs/REALTIME.md
/docs/LIVEFACE.md
/docs/ECONOMY.md
/docs/COLLECTIBLES.md
/docs/BUSINESS.md
/docs/CAMPAIGNS.md
/docs/VISIT_AND_EARN.md
/docs/PULSEPOINT.md
/docs/PAYMENTS.md
/docs/SECURITY.md
/docs/PRIVACY.md
/docs/FRAUD.md
/docs/MODERATION.md
/docs/ANALYTICS.md
/docs/TESTING.md
/docs/LOAD_TESTING.md
/docs/DEPLOYMENT.md
/docs/OPERATIONS.md
/docs/DR.md
/docs/ROADMAP.md
/docs/RELEASE_CHECKLIST.md
/docs/ADR/

Create Mermaid diagrams where useful.

============================================================
103. AGENTS.MD
============================================================

Create root AGENTS.md.

It must tell future agents to:
- read architecture/docs before modifying code
- never bypass tests
- never introduce fake production data
- preserve wallet invariants
- preserve location privacy
- use backend authorization
- update documentation
- run affected tests
- record architectural decisions
- avoid destructive migrations without explicit plan

Create scoped AGENTS.md files only where materially useful.

============================================================
104. ARCHITECTURE DECISION RECORDS
============================================================

Create ADRs for major decisions such as:
- modular monolith
- PostGIS
- Redis presence
- Cesium/3D provider abstraction
- LiveKit/WebRTC
- wallet ledger
- map data separation
- business tenancy
- deployment strategy
- analytics architecture

============================================================
105. AUTONOMOUS EXECUTION PROCESS
============================================================

DO NOT ask the owner dozens of low-value implementation questions.

For reversible routine decisions:
make a sound engineering choice and document it.

For consequential irreversible decisions:
document the issue and choose a safe default that preserves flexibility,
unless user input is truly required.

Work through implementation in epics internally.

Suggested sequence:

EPIC 00 Repository & Documentation
EPIC 01 Infrastructure/Foundation
EPIC 02 Authentication
EPIC 03 Consumer Onboarding
EPIC 04 Profiles/Avatar
EPIC 05 Geo/World Foundation
EPIC 06 3D World
EPIC 07 Realtime Presence
EPIC 08 Social Graph
EPIC 09 Messaging
EPIC 10 Voice
EPIC 11 LiveFace
EPIC 12 Wallet/Economy
EPIC 13 XP/Daily Drop
EPIC 14 Referrals
EPIC 15 Pulse Harvest/Fruit
EPIC 16 Gems/Treasure
EPIC 17 Missions
EPIC 18 Crews/Leaderboards
EPIC 19 City Battles
EPIC 20 Events
EPIC 21 Business Platform
EPIC 22 Virtual Stores
EPIC 23 Campaign Engine
EPIC 24 Visit & Earn/PulsePoint
EPIC 25 Perks/Redemption
EPIC 26 Payments/Subscriptions
EPIC 27 Transport
EPIC 28 Admin
EPIC 29 Moderation/Fraud
EPIC 30 Analytics/Observability
EPIC 31 Security Hardening
EPIC 32 Performance/Load
EPIC 33 Deployment
EPIC 34 Release Validation

You may parallelise independent work using subagents/worktrees.

Never allow parallel agents to make conflicting migrations without
coordination.

============================================================
106. COMPLETION LOOP FOR EVERY EPIC
============================================================

For every epic:

1. Read relevant docs.
2. Inspect current code.
3. Define acceptance criteria.
4. Identify architecture impact.
5. Identify data model changes.
6. Create migration.
7. Implement backend.
8. Implement frontend.
9. Implement authorization.
10. Implement analytics.
11. Implement errors/empty/loading states.
12. Add unit tests.
13. Add integration tests.
14. Add E2E tests.
15. Run formatter.
16. Run lint.
17. Run typecheck.
18. Run tests.
19. Build.
20. Start required services.
21. Exercise functionality.
22. Use browser/computer tools to visually inspect where available.
23. Fix visual/functional bugs.
24. Update documentation.
25. Commit logically.
26. Continue to next epic.

Do not declare an epic complete with failing tests.

============================================================
107. USER EXPERIENCE QUALITY
============================================================

The final application must feel like a polished consumer game/social
network, not an admin template.

Pay special attention to:
- transitions into world
- map-to-city animation
- avatar movement feel
- collectible feedback
- reward animations
- LiveFace positioning
- wallet feedback
- mission progress
- social interactions
- mobile controls
- latency masking
- loading experience
- skeleton states
- reconnect experience
- audio controls

Use tasteful audio hooks architecture, but do not include copyrighted
audio without proper assets/licensing.

============================================================
108. ACCESSIBILITY
============================================================

Outside pure game movement:
- keyboard navigation
- focus states
- labels
- screen-reader support
- accessible forms
- captions/indicators where applicable
- contrast
- reduced motion

Provide alternate non-3D ways to access critical account/business
functions.

============================================================
109. ERROR HANDLING
============================================================

Create consistent error system.

Examples:
- world load failure
- map provider unavailable
- WebSocket disconnected
- Redis degraded
- camera permission denied
- microphone permission denied
- payment failed
- location permission denied
- reward ineligible
- QR expired
- campaign ended
- business unavailable

Always provide understandable recovery action.

============================================================
110. RELEASE MODES
============================================================

Support:
local
internal alpha
closed beta
public beta
production

Use feature flags.

Closed beta can restrict access to invited users.

============================================================
111. RELEASE ACCEPTANCE GATES
============================================================

Do NOT call the product "release-ready" until all applicable gates pass.

GATE A BUILD
- all applications build
- no TypeScript errors
- no Python type errors deemed release blocking
- migrations apply cleanly

GATE B TESTS
- unit tests pass
- integration tests pass
- E2E critical journeys pass

GATE C SECURITY
- security checklist completed
- no known critical/high unresolved vulnerabilities
- wallet/payment/authorization regressions covered

GATE D ECONOMY
- no duplicate reward under repeated requests
- idempotent payment/reward flows
- ledger reconciles

GATE E PRIVACY
- precise GPS not exposed to players
- consent flows work
- account deletion/export documented/implemented

GATE F REALTIME
- reconnect works
- stale users removed
- auth enforced
- acceptable measured latency in test environment

GATE G GAME
- user can enter world
- move
- see another real test user
- collect fruit
- collect gem
- complete mission
- receive XP/Credits

GATE H SOCIAL
- friend
- chat
- voice token flow
- LiveFace consent/session flow

GATE I BUSINESS
- business can onboard
- create store
- create offer
- create campaign
- consumer discovers it
- Visit & Earn test flow succeeds
- PulsePoint replay protection tested
- analytics records result

GATE J PAYMENT
- Stripe test checkout succeeds
- webhook drives entitlement
- duplicate webhook safe
- failed payment state handled

GATE K ADMIN
- moderation
- merchant verification
- configuration
- financial/audit visibility work

GATE L PERFORMANCE
- client performance measured
- backend load test documented
- no unsupported scalability claims

GATE M DEPLOYMENT
- staging deploy documented
- production infrastructure generated
- health/readiness checks pass

============================================================
112. EXTERNAL DEPENDENCY REGISTER
============================================================

Create /docs/EXTERNAL_SERVICES.md.

List required production accounts/credentials:

- mapping/3D provider
- routing provider if external
- LiveKit
- Stripe
- AWS
- OAuth providers
- email provider
- SMS/OTP provider
- analytics/error monitoring where external
- AI provider

For each:
- purpose
- environment variables
- dashboard setup
- test mode
- production activation
- expected risks/cost areas

Never embed secrets.

============================================================
113. COST CONTROLS
============================================================

Build usage observability for expensive external services.

Track:
- map tile usage
- 3D session usage
- LiveKit bandwidth/minutes
- AI tokens
- storage
- CDN traffic
- database
- Redis
- email/SMS
- payment fees where available

Create configurable limits and alerts architecture.

============================================================
114. LEGAL / POLICY PREPARATION
============================================================

Generate clearly labelled DRAFTS for professional review:
- Terms of Service
- Privacy Policy
- Community Guidelines
- Merchant Terms
- Reward Terms
- Acceptable Use Policy
- Location Use Notice

Do not state that these drafts constitute certified legal advice.

============================================================
115. CRITICAL FIRST RELEASE USER TEST
============================================================

The application must successfully support this exact end-to-end scenario:

A new adult user:
1. visits PULSEWORLD
2. registers
3. confirms age
4. selects London
5. selects interests
6. creates avatar
7. accepts privacy choices
8. receives Welcome Pack
9. enters Soho world
10. walks through virtual world
11. sees available fruit
12. collects fruit
13. sees available gem
14. collects gem
15. mission progress updates
16. sees another logged-in test user
17. waves
18. starts chat
19. starts accepted voice session
20. requests LiveFace
21. second user consents
22. LiveFace appears as floating mini camera while both stay in world
23. first user completes collection mission
24. receives XP and Pulse Credits
25. opens EARN
26. discovers merchant campaign
27. visits merchant virtual store
28. views product/service/offer
29. selects Visit For Real
30. completes staging geofence/PulsePoint verification
31. receives merchant-funded Credits/Perk
32. wallet ledger updates
33. business analytics records verified visit
34. user redeems staging Perk
35. user invites a friend
36. referral attribution is recorded
37. user joins/creates Crew
38. user views leaderboard
39. user uses bike/car entitlement
40. user exits and returns
41. claims Daily Drop when eligible

This complete journey must have automated E2E coverage wherever technical
constraints make automation reasonable.

============================================================
116. CRITICAL BUSINESS RELEASE TEST
============================================================

A business owner:
1. registers
2. creates/claims business
3. completes verification workflow
4. selects plan
5. creates virtual storefront
6. adds product
7. adds service
8. creates offer
9. creates Fruit/Gem campaign
10. creates Visit & Earn campaign
11. selects budget/reward
12. pays in Stripe test mode
13. publishes campaign
14. views live campaign
15. consumer discovers campaign
16. consumer interacts
17. verified test visit occurs
18. business dashboard updates
19. redemption occurs
20. campaign analytics updates
21. business exports/views useful performance data

============================================================
117. FINAL DELIVERY
============================================================

When implementation is genuinely complete, provide:

A. Final repository tree
B. Architecture summary
C. Database/ERD summary
D. Running instructions
E. Local setup instructions
F. Staging deployment instructions
G. Production deployment instructions
H. Environment variable inventory
I. External account checklist
J. Test results
K. E2E results
L. Security review results
M. Load-test results
N. Known limitations
O. Remaining production/legal/account dependencies
P. Release checklist
Q. Release notes
R. Rollback instructions
S. Admin first-login instructions
T. Business first-login instructions
U. Consumer first-login instructions

============================================================
118. DEFINITION OF DONE
============================================================

"Done" does NOT mean:
- files generated
- code written
- UI created
- test plan written

"Done" means:
- implementation exists
- required services run
- database migrations work
- relevant tests pass
- build passes
- flows have been exercised
- errors discovered were fixed
- documentation matches actual implementation

If you find a bug, fix it.

If a test fails, investigate it.

If architecture conflicts with a later requirement, refactor it cleanly.

If the app does not run, do not declare completion.

============================================================
119. START NOW
============================================================

Begin by:

1. Inspecting the repository.
2. Creating AGENTS.md.
3. Creating docs/PRODUCT.md from this specification.
4. Creating architecture.
5. Creating ADRs.
6. Creating full implementation roadmap with acceptance criteria.
7. Creating the monorepo.
8. Creating local infrastructure.
9. Running the initial build.
10. Continuing autonomously through all epics.

Do not respond merely with an implementation proposal.

USE THE REPOSITORY AND TOOLS AVAILABLE TO YOU.

WRITE THE CODE.

RUN THE CODE.

RUN THE TESTS.

INSPECT THE APPLICATION.

FIX FAILURES.

CONTINUE THROUGH THE RELEASE PLAN.

Do not stop after the first milestone unless an external credential,
legal decision or account approval makes further progress technically
impossible.

The goal is a deployable PULSEWORLD closed-beta/public-beta product,
not a visual prototype.

START THE BUILD.
