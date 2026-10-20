# Release acceptance gates

**Not release-ready. All gates pending consolidated evidence.** Partial local tests may pass while a release gate remains pending. Record command, commit, environment, timestamp, result and evidence path per gate; do not replace a pending gate with a claim based on code inspection.

| Gate | Required evidence | Status |
|---|---|---|
| A Build | All apps typecheck/build; clean migration applies. | Pending |
| B Tests | Unit, integration and critical consumer/business E2E pass. | Pending |
| C Security | Review completed; no unresolved high/critical vulnerabilities; authorization/economy regressions. | Pending |
| D Economy | Duplicate/concurrent requests safe; provider/reward idempotency; ledger reconciles. | Pending |
| E Privacy | No precise GPS in public responses; consent/revocation/export/deletion tested. | Pending |
| F Realtime | Authenticated reconnect/stale cleanup and measured latency. | Pending |
| G Game | Two users enter/move/see each other; fruit, gem and mission reward journey. | Pending |
| H Social | Friend/chat plus actual consent-based voice/LiveFace flow. | Pending |
| I Business | Onboard/store/offer/funded campaign/visit/PulsePoint replay/analytics. | Pending |
| J Payment | Stripe sandbox checkout plus verified duplicate/failure webhook handling. | Pending |
| K Admin | Moderation, merchant verification, config, audit and financial visibility. | Pending |
| L Performance | Measured browser performance and backend concurrency, with limitations. | Pending |
| M Deployment | Staging deploy, generated production infrastructure and health/readiness validated. | Pending |

External credentials, provider end-to-end tests, legal approval, staging deployment, load testing and operational ownership remain explicit release dependencies. See PRODUCT.md sections 115–116 for the 41-step consumer and 21-step merchant journeys; neither is certified complete here.
