# PulsePoint

A merchant-bound short-lived signed challenge supports physical visit verification. PULSEPOINT_SECRET must be generated and stored securely outside local/test. Nonce/challenge consumption and reward issuance must be transactional.

Test altered signatures, wrong campaign, expiration, replay across users, concurrent consumption and key rotation. Define an explicit rotation window with old-key retirement; rotation support is not implied by a configurable secret. Do not display an unrestricted reusable reward QR as safe.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
