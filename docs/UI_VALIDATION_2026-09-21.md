# Targeted UI verification — 2026-09-21

Scope: Pasted text(2).txt and supplied LiveFace screenshot. Existing repository and Railway app only. No gameplay, scoring, world-coordinate or media-provider backend rewrite.

## Defect evidence
The supplied screenshot shows a half-viewport navy panel, a short cropped video strip and a clipped chat footer. Source inspection reproduced the causal CSS conflict: fullscreen retained translateX(-50%) after setting inset:0; mini simultaneously inherited top and bottom constraints. Existing video height stayed fixed at 130px. The replacement uses explicit mini/expanded/fullscreen geometry and flexible tiles. This is source/screenshot evidence, not a performed live call reproduction.

## Automated checks
- PASS: full backend suite, 84 tests including migration application, profile visibility in people/presence/invitations, all six identity choices, avatar independence, strict input validation and existing domain regressions.
- PASS: 3 pickup tests, 3 building-fascia tests, 40 camera-relative movement checks.
- PASS: production frontend build and TypeScript validation.
- Scoreboard footprint placement sampled across the board width in all five existing districts; Birmingham board moved to the clear side of the spawn. World data and player coordinates unchanged.

## Required acceptance matrix
FAIL — unverified means implementation exists but the specified visual/live gate has not been executed successfully. It does not mean a test demonstrated a remaining defect.

| Area | Gate | Result | Evidence / remaining verification |
|---|---|---|---|
| LiveFace | Mini | FAIL — unverified | Compact card implemented; live camera layout not exercised |
| LiveFace | Expanded | FAIL — unverified | Centered overlay at 78vw / 75dvh; no live visual check |
| LiveFace | Fullscreen | FAIL — unverified | Fixed inset:0, transform:none, 100dvh; no live visual check |
| LiveFace | Persistent controls | FAIL — unverified | Wrapped footer implemented; physical device check required |
| LiveFace | Blank-space bug | FAIL — unverified | Conflicting CSS replaced; actual media regression remains |
| LiveFace | Two/one/no camera, reconnect, end | FAIL — unverified | Presentation implemented; two-account/device test remains |
| Chat | Footer, Block, responsive | FAIL — unverified | Scrollable message body and wrapping action groups build |
| Social | Say Hi / Can We Talk? | FAIL — unverified | Both nearby surfaces updated; live authenticated check remains |
| Social | Waiting removal / connected copy | FAIL — unverified | Pending sourced from session state; notice expires after 2.8s |
| Profile | Gender field | PASS — automated only | Six values accepted; private defaults verified |
| Profile | Avatar suggestion | FAIL — unverified visually | Optional suggestions implemented; choice independence tested |
| Profile | Display location / privacy | PASS — API | Owner update and public opt-in/revocation verified through three response surfaces |
| World | Whitehouse label | PASS — API | Existing milton-keynes ID returns Milton Keynes - Whitehouse |
| World | Whitehouse scoreboard | FAIL — unverified | Reusable component and configuration; GPU check remains |
| World | London scoreboard | FAIL — unverified | Same component/ranking source; GPU check remains |
| World | Birmingham scoreboard | FAIL — unverified | Same component/ranking source; GPU check remains |
| Responsive | Desktop: 1440 / 1024 | FAIL — unverified | Browser layout fixture blocked by URL policy |
| Responsive | Tablet portrait / landscape | FAIL — unverified | CSS implemented; device validation remains |
| Responsive | Mobile: 430 / 390 / 360 portrait | FAIL — unverified | Safe areas, wrapping, keyboard viewport handling implemented |
| Responsive | Mobile landscape | FAIL — unverified | Side-by-side media and compact controls implemented |
| Regression | Existing functions preserved | PASS — automated only | All backend, pickup, movement and build checks pass; live journey not certified |

## Browser limitation
The connected cloud browser has a signed-out live entry screen. It advertises no viewport/device configuration capability. A local-only fixture using the real server-rendered components was generated for isolated layout checks, but the browser URL policy rejected data: navigation. No policy workaround was attempted; no visual PASS is inferred from fixture generation. Required live two-user verification still needs legitimate signed-in sessions, cameras/microphones and supported GPU/device access.

Deployment evidence will be appended after the existing-service deployment completes. This report is not final production acceptance.


## Subsequent live verification and superseding scope
The same existing Railway service deployed a7363e925afa3565a6e15ed835401cc8993aebd1 successfully (deployment 7bab6b11-fc66-4b16-a27f-5224b361cac7). Secure sign-in subsequently succeeded as rocky. At 1363×936 the active developersdddd chat had all eleven input/button controls inside its bounds and viewport. The Whitehouse label and six-choice private profile editor were inspected live without changing profile values. Screenshot: evidence/chat-desktop-20260921.jpg. The cloud browser uses the GPU-unavailable map fallback. The matrix above records the earlier pre-deployment state, not these later observations.

The user's new communication specification supersedes the centered expanded overlay with an interactive split-screen and adds proximity/group/avatar work. See COMMUNICATION_VALIDATION_2026-09-21.md for that release's evidence and outstanding real-device gates.
