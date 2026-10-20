
## GCP startup deployment automation (2026-10-20)

ADR 0022 and `infrastructure/gcp/README.md` define the parallel Mindaam-only deployment. GitHub OIDC bootstrap, bounded Cloud Run/Cloud SQL, one LiveKit OSS/Caddy/Redis VM, private registry/storage/secrets, job-based migrations and actual-URL acceptance are automated without changing application/media/snapshot architecture. Production promotion requires the exact staging digest and actual cost/metrics evidence. GCP is not yet provisioned or verified; old Railway remains untouched.
