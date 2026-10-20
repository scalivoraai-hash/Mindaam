# City discovery and share-to-unlock validation

Date: 2026-09-24. Scope: growth/discovery/world access only.

## Automated evidence
121 backend tests passed, including 7 targeted growth tests. Production frontend build and type checking passed. The existing regression suite remains in place; legacy gameplay tests explicitly choose their test destinations before entry. Migration test populates a real pre-gate schema and confirms all 17 former access rights survive. SQLite concurrency tests and PostgreSQL row-lock implementation are distinct evidence; no claim that local concurrency ran on PostgreSQL.

| Requirement | Test status |
|---|---|
| All enabled worlds, flat list, three independent MK destinations | PASS — backend catalog + dynamic frontend |
| Real counts, transfer, stale-session/NPC exclusion | PASS — backend tests; LIVE pending |
| Prominent online counts and zero-state copy | Implemented; live visual QA pending |
| Four user-selected worlds / 1–4 state / no preview consumption | PASS — API tests |
| Final confirmation / duplicate selection / competing fourth choice | PASS — API tests |
| Permanent access / fifth destination blocked / direct travel denied | PASS — API tests |
| Locked world remains visible with activity | PASS — catalog access state |
| WhatsApp / Facebook / X / Email / SMS composer URLs | PASS — encoded-link tests; external LIVE pending |
| Native / Instagram fallback / cancellation | Implemented; device LIVE pending |
| Copy link | Implemented; browser LIVE pending |
| Share UUID idempotency / cooldown / fifth-share race | PASS — API tests |
| Separate destination progress / permanent fifth-share unlock | PASS — API tests |
| Logout/login persistence | PASS — API auth lifecycle test; LIVE pending |
| Opaque public invite excludes private identity | PASS — API test |
| Social preview | SVG/PNG inspected; server-rendered metadata built |
| Existing user migration | PASS — populated migration preserves 17 worlds |
| Desktop / tablet / mobile layout | Responsive CSS implemented; live device QA pending |
| Existing modules preserved | Backend regression PASS; full live journey not certified |

## Honest share semantics
One valid explicit composer-open, email/SMS handoff, successful copy or completed native share action counts. No claim of recipient delivery, successful external post, acquired user or referral verification. Closing a native share sheet counts zero. Copy Link copies the safe URL; Instagram fallback copies invitation text/link and tells the user to paste it. No automatic external publication.

## Deployment and live evidence
Growth commit e209e356df731d885cbe7b47b0f1d0bbde88ee26 deployed successfully to the existing Railway service on 2026-09-24 (deployment edbd3d3c-1b9a-4410-a7ed-434c9d21b8ca). Runtime health and readiness endpoints returned 200. The live public preview displays all 17 destinations, with the three Milton Keynes destinations independently listed. Registration/sign-in switching works in the desktop browser. No account was created or terms accepted by automation.

Authenticated new-account acceptance, actual external share composers, native device sharing and mobile/tablet touch checks remain NOT VERIFIED. Browser authentication instructions require manual new-account creation; no live PASS is claimed for these gates. The available cloud browser renders the map fallback and does not establish WebGL/mobile performance.

Live invalid-invite fallback PASS: branded landing, friendly unavailable message, normal entry CTA and no private identity. Live OpenGraph DOM PASS: title, description and absolute social-card URL present. This does not certify a third-party social crawler preview or a valid authenticated invite.
