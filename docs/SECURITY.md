# Security review

Threat boundaries: untrusted browser, API/session, database transactions, tenant isolation, provider webhooks/media and privileged operators. Sessions are opaque and stored hashed at rest. Current browser token storage requires XSS review and an explicit production session-hardening decision.

Required review: credential recovery/verification, MFA for privileged users, brute-force and distributed rate limits, CSRF/CORS policy, CSP, upload scanning, dependency audit, websocket auth, least-privilege DB/IAM, secrets rotation, tenant enumeration and financial races. This is a review checklist, not a certification. No security scan or penetration test is claimed solely from CI configuration.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
