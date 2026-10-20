# External dependency register

Blank credentials must result in an unavailable feature, never simulated production success. Settings labelled planned are integration work, not existing capabilities. Use isolated provider projects per environment, secret managers, scoped credentials and billing limits.

| Service | Purpose and configuration | Setup/test/production evidence | Risks and cost controls |
|---|---|---|---|
| AWS | ECS/RDS/Redis/S3/ALB; Terraform variables | Dedicated account, IAM, VPC, ACM, secrets; review staging plan before deployment | NAT, Multi-AZ, logs, egress; budgets/alerts still required |
| PostgreSQL | `DATABASE_URL` | Apply migrations and verify PostGIS; test app role and TLS | Backups, connection pool, least privilege |
| Redis | `REDIS_URL` | Local Redis; staging TLS endpoint; exercise disconnect and replica behaviour | Memory, failover, stale presence; auth hardening pending |
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Separate test account; register implemented webhook URL from OpenAPI; test success, failure, duplicates and refunds before live activation | Provider fees, disputes, credit liability; no browser-authoritative fulfilment |
| LiveKit | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | Separate staging project; test token consent, room isolation, revoke/end and TURN on mobile before live use | Bandwidth/minutes; metering and quota gates pending |
| PulsePoint | `PULSEPOINT_SECRET` | Generate strong server-only signing secret; test expiry, replay, merchant binding, rotation | Fraud and reward budget liability; not proof of physical presence alone |
| Map/3D tiles | Planned provider configuration | Obtain official licensed Google/Cesium credentials; implementation/provider acceptance pending | Tile usage/licence restrictions; local procedural scene is not real map coverage |
| Routing | Planned adapter | Choose licensed OSM-compatible graph/provider; validate navigation dataset and attribution | Requests, licence and unsafe routing |
| OAuth | Planned provider credentials | Create authorised callback URLs only after provider flow is implemented | Account takeover and consent scope |
| Email | Planned provider credentials | Verified sending domain, SPF/DKIM/DMARC, sandbox; reset/verification delivery tests required | Abuse, delivery cost, account recovery |
| SMS/OTP | Planned provider credentials | Sender approval, test numbers and rate limits; implementation pending | OTP abuse and per-message spend |
| Analytics/errors | Planned external sink | Scrub identifiers/coordinates; consent and retention validation before enablement | PII leakage, sampling and event spend |
| AI | Planned provider | No AI provider needed for current deterministic mechanics; enable only with specified use case and evaluated safety | Tokens, prompt injection, uploaded data policy |

Application environment variables: `APP_ENV=local|test|staging|production`, `PUBLIC_ORIGIN`, and build-time web `API_INTERNAL_URL`. `.env.example` contains local defaults. Direct Python startup requires exporting configuration; Compose loads `.env`. Never expose provider secrets through `NEXT_PUBLIC_*`.
