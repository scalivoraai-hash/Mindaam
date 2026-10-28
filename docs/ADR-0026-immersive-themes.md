# ADR 0026 — Immersive visual themes

The existing frontend uses one semantic theme in `app/theme.css`, with Immersive Dark and Premium Light variants. A small pre-hydration head script resolves a saved `mindaam-theme` preference, otherwise the system preference (dark fallback). The client follows system changes until an explicit choice is stored and synchronizes other tabs. The switch does not reload or remount the world.

Shared surface, card, button, field, border, focus and state tokens replace the previous light-only brand rules. World/media glass remains explicitly dark for contrast over changing scene content. Profile-specific appearance choices remain independent. Modal scroll regions and the main drawer keyboard focus are presentational only. There is no backend, schema, authorization, wallet, event, media or renderer change.

`public/art/mindaam-horizon.webp` is original generated decorative login artwork (236,620 bytes), not an image of the playable city. Original SVG skyline illustrations decorate destination cards without claiming geographic accuracy or changing access/counts. The actual world retains its existing mapped Three.js scene. No decorative animation loop or new dependency is added. Reduced-motion preferences disable decorative transitions.

Artwork prompt: original cinematic nightfall city garden and reflective river, curved promenade, cyan path lighting, lush trees, distant electric blue/violet towers and observation wheel, coral horizon; calm left-side space for text; no text, logo, interface or watermark. Generated with the built-in image tool and encoded as WebP for the application.

Validation uses `scripts/tests/immersive-ui.cjs` against a disposable local database and a production build. It checks both themes, persistence, responsive layout, keyboard focus, rendered text contrast, consumer/admin views and existing operations. The existing CI acceptance assertions and timeouts remain unchanged. Local fixtures are not evidence of funded staging reservations or Stripe payments. Full staging release acceptance still requires the existing dedicated QA host, explicit reservation budget and provider prerequisites.
