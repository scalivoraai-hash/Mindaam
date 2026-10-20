# Railway preview deployment

The root Dockerfile builds Next.js and FastAPI into one origin. `railway.json` selects it and checks `/api/config`. This configuration has not yet been deployed or Docker-tested.

1. Push this source to a GitHub repository you control and connect that repository to Railway.
2. Create a Railway project with a PostGIS-capable PostgreSQL service and persistent Redis. The migration requires the PostGIS extension; a plain PostgreSQL image without that extension is insufficient.
3. Deploy the repository root using the included Dockerfile. Set APP_ENV=staging, DATABASE_URL to a SQLAlchemy-compatible PostgreSQL URL, REDIS_URL to the private Redis URL, and PULSEPOINT_SECRET to a generated secret. Keep one replica for this preview.
4. Generate a Railway public domain. Set PUBLIC_ORIGIN and PUBLIC_APP_URL to that exact HTTPS origin. Set PORT to the service port (3000 by default). API_INTERNAL_URL is intentionally the container's private localhost:8000.
5. Review build/runtime logs and readiness. The launcher applies migrations before startup. Do not run development seed commands in staging or production. Author genuine collectible and campaign content through the admin tools.
6. Visit `/explore` for the public simulated city preview, `/` for consumer registration, `/business` for merchant flows and `/admin` for an explicitly provisioned administrator. There are no default admin credentials.
7. Configure SMTP, encrypted mail outbox delivery and its worker before relying on verification/reset mail. Configure Stripe/LiveKit and their documented webhooks only when ready for provider testing. Never place secrets in Git.

A passing hosting healthcheck means the process is serving requests; it does not certify the outstanding release gates or guarantee no bugs. Test with non-production accounts until RELEASE_CHECKLIST.md is complete.
