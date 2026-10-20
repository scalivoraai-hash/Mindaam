# Mindaam: resumable GCP deployment

**Repository automation prepared. GCP NOT DEPLOYED.** No staging URL, production URL, IP, DNS verification, actual bill or media capacity has been invented. Existing application, media and snapshot work is preserved. Only `scalivoraai-hash/Mindaam` is a deployment source. Never use the old GitHub repository, Railway project, database, variables or domains as targets or migration sources.

## Resume point

Account: `sain@scalivora.com`. Dedicated project display name: **Mindaam Production**; proposed ID: `mindaam-production` (or an available `mindaam-*` equivalent). Region: London `europe-west2`, zone `europe-west2-b`. Domain: `mindaam.com`.

When the owner says **“GCP access/setup completed — continue deployment”**:

1. Read this file and `docs/STATUS.md`; inspect the current branch and existing `gs://PROJECT-releases/foundation.json` / `releases/SHA/` records. Never restart the application project or repeat completed source development.
2. Confirm the dedicated project ID and whether bootstrap completed. No Console retries from the known inaccessible agent browser.
3. GitHub → Mindaam → Actions → **Mindaam GCP deployment** → Run workflow → `foundation`, main. This is the first paid-resource operation. It outputs actual media/turn DNS targets. Ask the owner for DNS actions only after those actual records exist.
4. Once media/turn DNS resolve, run `staging`. It reuses successful application CI only when source/tests match, validates deployment guards, builds the existing unified application, pushes its immutable digest, creates the migration job, deploys staging, checks its real HTTPS URL, runs real browser/media tests (including forced TURN/TLS), measures bounded HTTP load and records Cloud Monitoring data. Use `verify` with its full release SHA to retry acceptance without rebuilding or reprovisioning.
5. Complete the actual cost review from the produced inventory and measurements using `review.py` (operator task, not account-owner code writing). Itemize idle/light usage in USD before credits. Record rate URLs/date, session hours, concurrent sockets, media sender/receiver hours and egress; Redis compute is already in the VM and must not be counted twice. The generated review packet has **null** prices until verified. Prefer <$100, warn at $125; the promotion gate refuses >$150. Owner authorization must cover the measured proposal. Do not claim 500/1000-user capacity from a three-browser startup test.
6. Configure apex DNS to the already reserved media VM IP, with the owner, then run `production` with the exact tested SHA and private `releases/SHA/release-review.json` object. No rebuild occurs. A pre-release SQL backup is created; migrations run once in a job; production has separate database/credentials. Caddy obtains apex TLS and forwards HTTPS/WebSockets to its actual Cloud Run origin. If DNS/cert propagation is pending, resume the same operation; do not mark PASS.
7. The workflow reports real staging/production `run.app` URLs, `https://mindaam.com`, and `wss://media.mindaam.com`. Verify the apex interactively with the owner's real account. Synthetic staging media is real network/WebRTC evidence, not a physical-device claim. Production smoke evidence alone is not a full end-user acceptance certification.

## Minimum owner setup — present one action per conversation turn

1. Google Cloud → project selector → New Project → Project name **Mindaam Production** → project ID **mindaam-production** if available → Create. If that dedicated project already exists, select it instead. Use `sain@scalivora.com`. Never repurpose another project.
2. Only if billing is not linked: Google Cloud → select Mindaam Production → Billing → Link a billing account → select the intended account with startup credit → Set account. The owner chooses/accepts billing; automation cannot accept financial account terms for them.
3. Google Cloud → Activate Cloud Shell → Authorize. The operator supplies one reviewed command block after the non-secret project ID is known. It signs into GitHub through the browser/device flow (`gh auth login --hostname github.com --git-protocol https --web`), clones the **private Mindaam repository**, and runs `python3 infrastructure/gcp/bootstrap.py --project ACTUAL_ID`. Do not request passwords, API keys or authorization codes in ChatGPT. If Cloud Shell lacks `gh`, install the official CLI there first as part of the prepared command, not application code.
4. Bootstrap automates API enablement, identities, IAM, GitHub OIDC federation and non-secret repository variables. It creates project-scoped $50/$75/$100/$125 notifications excluding credits; alerts go to the billing account's default IAM recipients. If the billing account is not USD, the budget API rejects a USD amount. Resume bootstrap with a reviewed local-currency equivalent using `--budget-amount`; never silently omit alerts or guess an exchange rate. Verify the billing account owner receives notices. No GitHub secret or downloaded service-account key is required.
5. After foundation returns an actual IP, the domain owner adds **DNS-only A records** for `media` and `turn` at the current DNS provider. Add apex `@` only at the production stage. Remove conflicting A/AAAA records only for these Mindaam names after checking ownership; never modify Railway/old domains. There is no automatic nameserver transfer or unrelated zone edit.

Everything else listed in the request—APIs, WIF, service accounts, minimum required permissions, repository variables, database/Redis/LiveKit credentials, registry, storage, Cloud Run, VM and budgets—is repository automation. Optional external provider credentials (SMTP, Stripe, Google login) must be supplied directly to the corresponding Secret Manager containers, never in chat. They are not copied from Railway. Unconfigured providers remain unavailable; do not claim payments/mail PASS without their own provider tests.

## Startup architecture and limits

| Resource | Initial configuration |
|---|---|
| Production Cloud Run | min 0, max **2** at service and revision level, 1 CPU / 1 GiB, concurrency 40 |
| Staging Cloud Run | min 0, max **1**, same image, separate database/secrets |
| PostgreSQL | one Cloud SQL PostgreSQL 16 `db-f1-micro`, single zone, PostGIS; 10 GiB SSD, growth bounded at 20 GiB; daily 7 backups / 7-day PITR; deletion protection |
| SQL connections | 3+2 per app instance; at most 15 across initial services, plus migration/admin allowance; runtime role limit 12 per environment |
| Media VM | one `e2-small`, 20 GiB standard disk, deletion protection, immutable LiveKit OSS/Caddy/Redis image digests |
| Redis | same VM, 128 MiB maxmemory/noeviction, password and private subnet firewall; transient revisions and distributed rate limiting only |
| Storage | private versioned release/evidence bucket and private asset bucket; obsolete object versions expire; registry cleanup keeps 5 recent images |
| Networking | one VPC/subnet, Direct VPC egress; no NAT gateway, connector, GKE or paid external load balancer |
| Media ingress | TCP 80/443/7881; UDP 3478/50000–50200. Caddy multiplexes `media` and `turn` on TLS 443. No public 5349, 7880, 6379 or SSH |
| Custom domain | same Caddy VM proxies apex HTTPS to Cloud Run; shared VM is an acknowledged single failure point |

The Cloud SQL public IP has **no authorized networks**; application/job connections use authenticated Cloud SQL sockets. Migration credentials can administer the target database; runtime accounts get DML, not superuser/role/database creation. The VM identity reads only media/Redis secrets and objects under `vm/`. CI is scoped to the dedicated project; no Owner/Editor/project-IAM-admin or key-admin role. WIF checks numeric repository/owner IDs, main, manual dispatch and exact workflow path.

These are resource ceilings, **not a guarantee of a $150 bill cap**. Cloud Run can temporarily exceed configured instance maxima during exceptional behavior; network egress, active WebSockets, logging and storage remain usage billed. Scaling/size increases require a reviewed policy change. The small shared-core VM/database have limited capacity and no HA guarantee. Credit does not reduce the underlying burn rate. Inspect actual monitoring and billing before increasing audience limits.

Current bundled public assets are about 1.2 MiB and compressed geography about 5.2 MiB. Existing cache behavior is retained. The private GCS asset bucket is prepared for larger assets; no broad public bucket or paid CDN/load balancer is enabled without measured benefit. There is no app asset-loader rewrite in this infrastructure change.

## Preserved application behavior

No application source changes: LiveKit OSS only, selective subscriptions, adaptive stream, dynacast, 360p avatar / 720p fullscreen, 1080p disabled, camera off, auditorium audience camera/mic off, host+3 guest publishers and one screen share. Ordinary presence/walking/friends/text chat/vehicles/businesses/collectibles do not create LiveKit sessions. Redis is required to preserve the completed revision/cache optimization; no per-client 500 ms SQL polling has been added. The prior approximately 90% idle two-user SQL reduction remains the existing evidence, not a new GCP performance result.

## Operator commands and evidence

- Local checks: `python3 -m unittest discover -s infrastructure/gcp/tests -v`; `python3 -m compileall -q infrastructure/gcp`; `node --check infrastructure/gcp/browser.cjs`.
- The **GCP deployment validation** workflow additionally validates real pinned Caddy/LiveKit containers and builds the GCP packaging. Application CI jobs are unchanged; deployment/docs-only changes do not rerun the completed full suite.
- Bootstrap: `python3 infrastructure/gcp/bootstrap.py --project ACTUAL_ID` (owner account only, no paid VM/SQL provisioning).
- Review packet: `python3 infrastructure/gcp/review.py --project ACTUAL_ID --sha TESTED_SHA`. Save actual reviewed JSON outside source, then `--input /path/to/review.json` validates it and stores the private release gate object. This is evidence data, not application code or secrets.
- The generated owner initial password is a specific Secret Manager value, accessible directly by the owner; never put it in an artifact/chat/log. Existing account behavior requires changing the initial password. Secrets are generated once and retained on resume.
- VM configuration is fetched via its identity, validated by archive digest and written root-only under `/run/mindaam`. No credentials are placed in startup metadata. Ordinary app releases don't restart media. Changing keys/configuration is a controlled maintenance action; new secret versions require publishing a new VM bundle to reconcile.
- `rollback` restores the previously recorded 100% Cloud Run revision only. It never downgrades a database or overwrites secrets. Application migrations must remain backward-compatible. The workflow refuses split-traffic ambiguity.
- Backups/PITR are enabled before promotion; production takes an additional on-demand backup. A destructive restore is **never automatic**. Disaster recovery: verify backup/time and target, restore into a separately approved isolated instance, test PostGIS/schema/data and app health, then plan cutover. No restore drill has yet run and none is reported PASS.

The older `cloud-run.yaml`, `media-compose.yaml`, `livekit.yaml`, `Caddyfile`, `redis.conf`, `budget.json` and `preflight.sh` remain historical staging templates. **Do not apply them**; executable configuration is `settings.json` + `render.py` + `deploy.py`. There is no Terraform state or credential file in this repository.

Official implementation references, checked 2026-10-20: [GitHub/GCP WIF](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines), [Cloud Run maximum instances](https://docs.cloud.google.com/run/docs/configuring/max-instances), [Direct VPC](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc), [Cloud SQL creation flags](https://docs.cloud.google.com/sdk/gcloud/reference/sql/instances/create), [LiveKit VM](https://docs.livekit.io/transport/self-hosting/vm/), [LiveKit ports](https://docs.livekit.io/transport/self-hosting/ports-firewall/), [budget CLI](https://docs.cloud.google.com/sdk/gcloud/reference/billing/budgets/create). Cloud Run's native domain mapping is currently preview and not suitable for this London production plan; Caddy handles the custom domain.
