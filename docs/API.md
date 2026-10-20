# API contracts

FastAPI exposes OpenAPI at /openapi.json and interactive /docs when the API is running. All domain endpoints use /api; /health and /ready are operational endpoints. Inspect runtime OpenAPI for exact fields and validation instead of treating examples as a frozen contract. Authentication uses opaque Bearer session tokens.

Consumer routes cover /auth/register, /auth/login, /me, /onboarding, /wallet, /rewards/daily, world, collectibles, missions, social, messages, crews, events and privacy. Merchant routes cover /businesses, /business/mine, catalogue, offers, campaigns, /visits/verify, /perks and /payments. POST /api/payments/webhook is provider-signed rather than end-user authenticated. GET/POST /api/admin routes require admin authorization. Frontend must display server rejection and retry safely; never invent payment/reward success.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
