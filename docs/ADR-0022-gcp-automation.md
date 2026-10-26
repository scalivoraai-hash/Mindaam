# ADR 0022: isolated, resumable startup deployment to Google Cloud

Date: 2026-10-20. Status: repository preparation; cloud execution and live acceptance pending.

Continue from Mindaam commit 87ec2fb1c022abdf79fe6c975fedc69a1cf6bb18 and successful 16-job Validation run 39431534357. Do not repeat the completed application, rebrand, media or snapshot work. Google Cloud Console is inaccessible from the agent browser before authentication.

Use the dedicated Mindaam Production project and GitHub manual deployment workflow, authenticated by OIDC restricted to numeric repository/owner identities, main and the exact workflow. Owner bootstrap enables APIs and configures identities, WIF, non-secret GitHub variables and project-scoped budget alerts. Explicit gcloud commands reject unrelated resources and retain existing secrets on resume.

Startup resources: Cloud Run min0/max2 production and max1 staging; one small Cloud SQL instance with separate databases/runtime roles; bounded Redis on a single e2-small LiveKit OSS/Caddy VM. Preserve transient revision caching and every existing media limit. Private GCS stores release evidence and prepares larger assets; current small assets retain app caching. Caddy shares the VM for apex HTTPS because native Cloud Run domain mapping is preview and not suitable for this London deployment. This is a single failure point, accepted for startup cost; no paid load balancer/CDN/GKE/NAT is added.

The workflow validates infrastructure, reuses CI only with identical application/test bytes, builds/pushes GCP packaging, migrates in a single job, deploys staging, runs actual browser/media/forced-TURN checks and records metrics. Production uses the exact accepted digest, requires fresh cost/evidence, takes a SQL backup and verifies real URLs. Null prices, missing metrics or absent URLs cannot PASS. Resource limits constrain cost but cannot guarantee a dollar ceiling; $125 warnings and a >$150 estimate gate supplement them.

Existing application CI job definitions remain byte-identical. Deployment/docs-only changes route to separate validation. Rollback restores traffic only; database restore is separately reviewed and has not been tested. Old GitHub/Railway/database/domains/variables are untouched. Operator and one-at-a-time owner instructions: infrastructure/gcp/README.md.


## 2026-10-26: accept the existing dedicated project

The owner confirmed project ID `mindaam`, display name `Mindaam`, number `157480611225`, and enabled billing. Accept this exact ID alongside the existing `mindaam-*` pattern in the shared Cloud validator. Permit display name `Mindaam` only for that exact ID; retain the existing `Mindaam Production` check for prefixed projects. Active lifecycle, billing, post-bootstrap ownership labels, resource ownership, and release gates remain unchanged.

Reviewed all GCP scripts, workflows and deployment configuration: remaining `mindaam-production` values are service names or test fixtures, not fixed deployment project IDs. Bootstrap supplies the chosen project and derived identities to the workflow through repository variables. Added isolated mocked regressions for identity, safeguards, `95GBP`, and that variable wiring; all 16 deployment unit tests pass. No GCP deployment was performed.
