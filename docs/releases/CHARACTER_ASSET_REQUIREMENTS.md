# Optional future rigged character asset handoff

External rigs are deferred under the owner’s latest procedural-avatar scope; this is a future asset specification, not a release blocker.

Visual target: the recovered five-character reference. Build original characters; do not copy its characters, clothing logos or proprietary designs. The reference image is not a model or a licence to redistribute models.

Provide a commercially usable rigged GLB package, or make the configured Game Development Studio/Blender pipeline available. Never send provider credentials in chat.

Required package:
- Source/licence record explicitly covering commercial deployment and delivery of assets to browser clients. Include author, source URL, licence text and attribution requirements.
- glTF 2.0/GLB in metres, consistent forward/up orientation, bind pose and humanoid bone names. Root translation must stay separate from server-authoritative movement.
- Original adult human proportions, expressive face/eyes, hair, articulated hands and interchangeable clothing. Skin/body customisation must not require biometric information.
- Shared compatible rigs, material slots and appearance IDs, with a mapping for current saved appearances.
- Idle, walk, run, turn/start/stop, sit/stand, wave, point, clap, talk, dance, driving, cycling, passenger and audience/host poses; support existing jumping if applicable. Blendable clips with no baked gameplay movement.
- Blink, smile and restrained speaking expression shapes. Do not claim phoneme lip sync.
- Three distance-detail variants, shared/reusable PBR textures and optional compressed textures. Initial engineering budgets: <=30k/12k/3k triangles per near/medium/far character, <=96 bones, <=4 influences per vertex, <=2K textures. These are budgets to validate, not evidence of device performance.
- Preview renders, mesh/texture/animation inventory and hashes. No external executable scripts, credential material or unlicensed embedded assets.

Acceptance after receipt: validate bytes/rig/licence, integrate one shared renderer across world/profile/studio/arena/vehicles, migrate appearance mappings without resets, test remote appearance updates and grounded animation, then measure desktop/mobile performance and repeated city-transition resources. A successful asset download alone does not meet these gates.
