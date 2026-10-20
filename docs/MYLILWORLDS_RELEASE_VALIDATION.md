# MyLilWorlds release validation — 2026-09-22

## Evidence scope
114 backend tests PASS; 13 frontend unit tests PASS; 40 camera-relative movement checks PASS; Next production build/type checking PASS. Tests use isolated test databases, not fabricated production users. Migration chain tested.

Live deployment evidence is recorded below after publishing. Full real-device/multi-user release certification is not established by unit tests. A missing live test is marked NOT VERIFIED, never PASS.

| Required check | Automated evidence | Live evidence |
|---|---|---|
| Avatar attached LiveFace and follows movement | Identity anchors and smoothing implemented | NOT VERIFIED with real cameras |
| Voice-only tile / speaking | Fallback and speaking state implemented | NOT VERIFIED with real microphones |
| Split screen / remote primary / local PiP / interactive world | Production build PASS | NOT VERIFIED with media |
| Fullscreen and return | Existing flow preserved, build PASS | NOT VERIFIED with media |
| Proximity warning / independent leave / cleanup | Group/proximity tests PASS | NOT VERIFIED with multiple users |
| Join approval / duplicates / capacity / blocking | Backend tests PASS | NOT VERIFIED with multiple users |
| Original moderators / remove / cooldown | Backend tests PASS | NOT VERIFIED with multiple users |
| Group text / voice / video | Text and media authorization tests PASS | NOT VERIFIED with multiple users |
| Human avatar proportions / animations / LOD | Avatar animation and LOD tests PASS | GPU/mobile performance NOT VERIFIED |
| Waiting clears / late pending response cannot restore | State regression tests PASS | Multi-user acceptance NOT VERIFIED |
| Empty mini panel removed / responsive layouts | Content-sized CSS and build PASS | Mobile/tablet devices NOT VERIFIED |
| Echo prevention / device controls | Local-audio rejection/dedup tests PASS | Real-device acoustic echo NOT VERIFIED |
| Hosted events / private approvals / stage permission | Event API tests PASS | Live event flow pending |
| Counts / city transfer / expired sessions excluded | API tests PASS | Live UI pending |
| All 17 district spawns / running collisions | 17 parameterized geography checks PASS | Live world pending |
| Running faster / diagonal and time limits | 13 vs 6 m/s, movement tests PASS | Live control pending |
| Registration and navigation touch | Input isolation, cancellation and touch targets implemented | Real iOS/Android taps NOT VERIFIED |
| Auth / economics / missions regression | Full backend suite PASS | Full production user journey NOT VERIFIED |

## Whitehouse source audit
Fresh OpenStreetMap extract: 1,245 → 1,247 building footprints. Two additional school footprints; zero additional houses/apartments supported by this extract. Existing outer coverage retained. ODbL attribution retained; address tags omitted. New cities cover bounded districts, not whole cities.

## Live evidence
To be appended with exact commit/deployment identifiers and observed results.
