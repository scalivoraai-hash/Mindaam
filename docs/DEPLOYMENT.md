# Deployment

Status: Compose and AWS definitions are supplied for review. They have not been run against Docker or an AWS account in the creation environment. No staging or production deployment is claimed.

## Local
Follow README. `.env` is supplied to containers; the Python process does not automatically load it when launched manually. Export required settings in your shell. Run `python -m backend.api.cli seed` only in local mode if you want clearly labelled development content. The seed command must never run on staging/production.

## Staging preparation
1. Supply a dedicated AWS account/environment, existing VPC, two public and two private subnets across AZs. Private subnets need controlled NAT egress or VPC endpoints for ECR, logs and secrets, plus provider connectivity.
2. Create ECR repositories and push API/web images tagged by immutable commit and preferably referenced by digest. Build using the Dockerfiles. Web uses same-origin `/api` requests; ALB sends these directly to API. Compose uses a build-time Next rewrite to its API service.
3. Supply a validated ACM certificate for your hostname in the chosen region. Configure DNS to the ALB after plan review. HTTPS only; no HTTP listener exists.
4. Set encrypted remote Terraform state and restricted access before apply. State, plans and DB secret ARNs are sensitive operational data. Do not commit tfvars or plan files.
5. Run `terraform -chdir=infrastructure/terraform init`, `validate`, then `plan -out=reviewed.plan`. Review network, spend, backup and IAM settings. This scaffold has not been provider-validated locally.
6. Bootstrap with `desired_count=0`. RDS creates its master password in Secrets Manager. Use a controlled migration identity to enable `CREATE EXTENSION IF NOT EXISTS postgis`; create a least-privilege application DB role and put its complete `postgresql+psycopg://...` URL (including TLS parameters) in a separate Secrets Manager secret. Use a migration-specific elevated credential only for DDL. Supply the application URL secret ARN to Terraform. No master password is put in source.
7. Run a one-off ECS API task with command override `alembic -c backend/alembic.ini upgrade head`, using the same private network and task security group. Confirm exit code zero. Migration is intentionally not run concurrently by every web worker.
8. Configure provider secrets, PUBLIC_ORIGIN, PulsePoint signing key, and any invite-only access enforcement. Start a single API replica until distributed presence and concurrency tests establish safe scaling. Set desired count, apply the reviewed plan, and wait for target health.
9. Exercise `/health`, `/ready`, registration, authorization, merchant isolation, ledger reconciliation, provider sandbox and two-user consent flows. Record versioned evidence in RELEASE_CHECKLIST. Launch gates remain pending until these tests actually pass.

## Production differences
Do not promote this scaffold simply by changing a name. Implement and validate environment-specific settings, deletion/retention, private beta access, backup restoration, alerts, WAF/rate limits, secret rotation, least-privilege provider access, regional capacity, egress controls, domain policy pages and support procedures. Cost budgets and autoscaling are not configured here. S3 is provisioned privately but media upload workflow/IAM grants are not thereby implemented. Redis is network isolated and TLS encrypted; Redis user authentication is a remaining hardening task.

## Rollback
Record image digests, task-definition revisions and Alembic revision before release. Deploy additive backwards-compatible schema changes first. ECS circuit breaker rolls back unhealthy service deployments; it does not roll back DB changes. Restore the previous API/web task definition only if compatible with the migrated schema. Do not run blind Alembic downgrades on wallet/payment data. If incompatible, stop mutations and restore a tested DB snapshot/PITR to a separate instance, reconcile provider events and ledger before controlled traffic cutover. Preserve old DB and audit evidence.

Browser cookie sessions require PUBLIC_ORIGIN to exactly match the HTTPS frontend origin. Configure Google credentials on the app service runtime as GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET; callback is PUBLIC_APP_URL + /api/oauth/google/callback. Provider APIs return availability booleans only. Reset/verification delivery requires SMTP_HOST, SMTP_FROM, MAIL_ENCRYPTION_KEY plus SMTP_USER (SMTP_USERNAME alias supported) / SMTP_PASSWORD as required by the provider. Do not place secrets in NEXT_PUBLIC variables. The Railway healthcheck now uses /api/health, which verifies database/migrations, PostGIS and Redis rather than only frontend routing.

The existing API process drains the committed encrypted mail outbox every ten seconds when SMTP and MAIL_ENCRYPTION_KEY are configured. Delivery runs in a thread pool, uses row locking and bounded batches, and retains the existing retry/backoff policy. No additional service is required.
