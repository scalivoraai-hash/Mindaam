# Whitehouse character development pipeline

This is an **offline, unintegrated development asset**, not a staging release.
The current runtime avatar remains unchanged. No source program from MakeHuman
is imported, executed or copied; only its explicitly CC0 asset data is converted.

## Sources and rights

- Core mesh, rig, weights and eyes: MakeHuman Community,
  <https://github.com/makehumancommunity/makehuman>.
- Asset licence: <https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md>.
- Outfit, shoes, short hair and skin: official CC0 system asset pack,
  <https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html>.
- Original asset headers identify Data Collection AB, Joel Palmius and Jonas
  Hauquier among the copyright holders at the September 2020 CC0 release.
- Licence: CC0 1.0, <https://creativecommons.org/publicdomain/zero/1.0/>.

`whitehouse-character-sources.json` pins the exact reviewed garment, material,
eye and texture bytes. `prepare-whitehouse-character.py` separately pins the
core OBJ, rig and weights. An upstream replacement is rejected, even if its
licence header is unchanged. These permissions apply to asset data, not the
MakeHuman application's AGPL source code or arbitrary third-party assets.

## Reproduce locally

Place the core `base.obj`, `default.mhskel`, `default_weights.mhw` and
`brown_eye.png` in a private working source directory. Extract the selected CC0
pack paths listed by the manifest under `selected/`, together with the core
`eyes/low-poly` OBJ and MHCLO under `selected/eyes/low-poly/`.
Validate downloaded ZIP entries against their archive CRCs before conversion.

From the repository root, with its existing Node dependencies and Pillow:

```bash
python3 scripts/assets/prepare-whitehouse-character.py --source "$ASSET_SOURCE" --output /tmp/whitehouse-character.json
node scripts/assets/export-whitehouse-character.mjs /tmp/whitehouse-character.json /tmp/whitehouse-character.glb
python3 scripts/assets/texture-whitehouse-character.py --source "$ASSET_SOURCE" --input /tmp/whitehouse-character.glb --output /tmp/whitehouse-character-textured.glb
python3 scripts/assets/test_whitehouse_character.py
node --test apps/consumer-web/components/CinematicCharacterPose.test.mjs
node scripts/tests/whitehouse-character.cjs /tmp/whitehouse-character-textured.glb
```

The browser fixture uses Playwright from `CODEX_PRIMARY_RUNTIME_NODE_MODULES`,
optional `QA_CHROMIUM`, and `QA_OUTPUT` for its captures/results. It is not a
gameplay test and its render counts must not be presented as full-world FPS.

## Current adaptations and remaining admission gates

The converter retains 22 bones with four normalized influences per vertex,
removes covered skin faces using the source garment masks, separates the outfit
at its waist for independent shirt/trouser material control, and removes shoe
upper faces concealed by the trouser cuffs. Textures are capped at 1024 pixels,
shared where possible, and embedded with the OBJ/glTF vertical-origin conversion.

The pose adapter uses the existing distance-driven Locomotion implementation and
does not change the owning player's position, heading, scale or server movement.
It has no World import or runtime activation yet.

Before runtime admission: preserve all appearance options, add wardrobe variety,
verify every animation transition/foot placement, implement bounded LOD and
resource ownership, compare full-world/mobile budgets, and pass staging gameplay
and visual acceptance. No production release is authorised by these artifacts.
