# LiveFace and voice

Media sessions require a target request and explicit acceptance. Provider tokens must be bound to accepted session participants; payment or credits never buy camera access. LiveKit credentials are server-only. Missing credentials must fail closed.

An issued JWT is not proof of working audio/video. Validate actual browser media permissions, mutual consent, block/end revocation, expiry, room isolation, reconnect, mobile backgrounding and floating avatar video while moving. Metering, subscription allowances, spatial audio and production TURN behaviour require explicit acceptance evidence.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
