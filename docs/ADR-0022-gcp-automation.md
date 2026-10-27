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

## 2026-10-26: first Foundation resource discovery

Recognize the Storage CLI `not found: 404` response only for explicit missing-resource discovery. Bare 404 and unknown errors still fail. Authentication, permission and transport failure indicators take precedence, including mixed missing/error messages. Resource ownership, description checks and creation configuration are unchanged.

Reviewed buckets, Artifact Registry, VPC, subnet, firewall rules, reserved media IP, Secret Manager, Cloud SQL and media VM discovery: each already uses the shared opt-in adapter. Added mocked regressions for missing/error classification, bucket create versus abort, and ownership refusal. All 22 GCP unit tests, Python compilation and browser-script syntax pass locally. Application CI reuse is checked against successful run 39431534357 (16 successful jobs); application/test files and CI job definitions remain unchanged. No cloud operation was executed.

## 2026-10-26: distinguish identity context from actual failures

The Artifact Registry NOT_FOUND includes harmless authenticated identity and credential context. Replace generic failure nouns with explicit status/phrase matching, retaining inspection of the entire stderr so errors before or after identity context remain fatal. This also avoids treating Compute network resource paths as transport failures. Missing handling remains opt-in; project, ownership, IAM and adoption checks are unchanged.

Regression coverage includes the exact reported Artifact Registry response, all Foundation discovery resource types, mixed real failures before/after identity context, and a fully mocked first Foundation pass through buckets, registry, network, subnet, both firewalls, reserved IP, all generated/optional secrets, SQL instance/databases, absent VM bundle metadata and media VM. All 26 deployment unit tests, Python compilation and browser-script syntax checks pass. No real cloud resources or workflow dispatches were performed.

## 2026-10-26: Artifact Registry cleanup policy input schema

Inspected both complete job logs for Foundation run 40418741343. The adapter captures subprocess output, so the log exposes only the final error, not individual gcloud argv. Traced the exact diagnostic to Google SDK 550.0.0 `command_lib/artifacts/cleanup_policy_util.py:ParseCleanupPolicy`: the CLI input requires `name`, then converts it to API `id`. Foundation passed API-style `id` keys to `gcloud artifacts repositories set-cleanup-policies mindaam --location=europe-west2 --policy=<temporary JSON> --no-dry-run --project=mindaam --quiet --format=json` (deploy.py:184), before network/secret/IAM provisioning. Executing the official parser offline with the old payload reproduced `Key "name" not found in policy.`; the corrected payload parsed successfully. The logs do not identify the installed SDK patch version.

Only the two cleanup-policy input keys change from `id` to `name`. Delete-untagged after seven days and keep-five-recent behaviour are unchanged. Reviewed remaining policy operations: IAM bindings use member/role/condition flags, not this cleanup JSON parser. No IAM, conditional storage access, private storage, ownership, sizing or identity configuration changes. Reference: https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy .

The full mocked Foundation test now checks the actual temporary policy JSON and both IAM command shapes, then resumes a second time and rejects resource recreation or secret regeneration. Added refusal of unowned/unlabelled registries before any policy update. All 27 GCP unit tests, Python compilation and browser-script syntax pass. No Foundation or other cloud operation was executed.

## 2026-10-27: aggregate equivalent firewall allowed entries

The owner supplied the actual describe representation for `mindaam-media-public`: separate TCP entries for 80/443/7881 and UDP entries for 3478/50000-50200, INGRESS, enabled, source 0.0.0.0/0, the Mindaam media service account, the dedicated Mindaam network, and the managed description. The old dictionary comprehension overwrote repeated protocols, leaving only the last entry for each. The Redis-private rule is confirmed absent because Foundation stopped earlier.

Normalize by unioning effective port sets per TCP/UDP protocol (including equivalent numeric protocol identifiers and split ranges). Compare exact access, source, target, direction and enabled status for both rules. Validate the full dedicated network URL and managed description; reject extra source/target selectors, unrestricted ports and unsupported protocols. Creation settings, approved ports, private Redis source, SQL settings and all unrelated infrastructure remain unchanged. Existing equivalent firewalls are read only; mismatches still fail closed rather than being silently modified.

All 32 GCP unit tests pass, including owner-evidence-shaped firewall cases, negative security cases, full first Foundation, full resume, and partial resume with an existing split-entry media firewall and missing Redis-private firewall. Tests prohibit recreation/modification of existing firewalls and regeneration of existing secrets. Python compilation and browser-script syntax pass. No live provisioning or workflow dispatch performed.

## 2026-10-27: Cloud SQL HTTPError missing discovery and current-state resume

Read the deploy job log for run 40424672367 (commit 188642ca76154e9801a185c8b5e2c4c3a776ad8e): database discovery returns `HTTPError 404: Not Found.` followed by the authenticated identity and credential-file context. The existing opt-in classifier did not recognize this status/reason pair. Accept the explicit HTTP/HTTPError 404 plus Not Found reason only when missing handling was requested; bare codes, unrelated HTTP errors and unknown errors remain fatal. Explicit non-404 HTTP failures, quota/resource-exhaustion and invalid/malformed request errors take precedence even in mixed missing messages. Existing permission/authentication/transport protections remain intact.

Reviewed every Foundation discovery call: buckets, registry, network/subnet, both firewalls, reserved IP, generated/optional secrets, SQL instance/databases, VM bundle metadata and media VM all use the shared opt-in adapter. The regression matrix exercises the supported provider response forms across those calls; the exact Cloud SQL log payload is retained as a fixture. It does not assert that every service emits every variant.

The full mocked first deployment and current SQL-stage partial resume reach completion, then repeat without recreating resources or regenerating secrets. The partial fixture preloads both buckets, registry, VPC/subnet/firewalls, static IP, all secrets and the SQL instance; only databases and media VM may be created. Tests verify SQL password reconciliation uses the existing secret, VM startup/private networking/static-IP arguments, bundle metadata, Foundation inventory generation, and rejection of unowned SQL/secrets. Fatal database discovery errors never create a database. No provisioning, ownership, IAM, sizing or application code changed.

All 36 GCP deployment tests, Python compilation and browser-script syntax checks pass locally. No real GCP operation or workflow dispatch performed.

## 2026-10-27: Storage optional-state missing-object diagnostic

Confirmed run 40427760551 reports `ERROR: (gcloud.storage.cat) The following URLs matched no objects or files:` followed by `gs://mindaam-releases/vm/current.json`. Recognize this exact diagnostic header only through the existing explicit missing-resource opt-in; do not match the phrase embedded in an object URL. Fatal permission/authentication/HTTP/quota/transport/request indicators still take precedence. Add explicit invalid-request and invalid/malformed path/URL/URI rejection for mixed diagnostic output.

Reviewed all optional state reads in common.py, deploy.py, workflow.py, review.py and evidence.py: Foundation inventory, VM metadata, release states, prior states, verification, review and metrics share Cloud.get_json. Tests cover that adapter with each state key, existing JSON, malformed JSON, the exact missing response, opt-in refusal and real/mixed failure responses. Caller release gates, ownership checks and write paths are unchanged.

All 40 GCP tests pass, including fully mocked empty Foundation and partial resume with existing buckets, registry, network/firewalls, static IP, secrets, SQL instance and both databases but absent VM metadata and VM. The mock uses the real Storage diagnostic and reaches Foundation completion, then repeats without recreating resources or regenerating secrets. Python compilation and browser-script syntax pass. No real provisioning, storage writes or workflow dispatch performed.
