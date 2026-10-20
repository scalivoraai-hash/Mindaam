# PULSEWORLD

A browser-first city exploration, social and merchant-rewards application. The source specification in [docs/PRODUCT.md](docs/PRODUCT.md) is the target scope, **not a list of shipped capabilities**. This repository is an implementation under validation. Do not advertise it as production-ready; consult [docs/STATUS.md](docs/STATUS.md) and the [release gates](docs/RELEASE_CHECKLIST.md).

## Local development

Requires Python 3.12+, Node 22, and optionally Docker Compose for PostGIS/Redis.

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.api.cli seed
python -m uvicorn backend.api.main:app --reload --port 8000
```

In a second terminal:

```bash
npm ci --ignore-scripts
npm run dev
```

Open http://localhost:3000. API documentation is at http://localhost:8000/docs. Register your own adult test account; there are no default credentials. Local geometric city scenes and local reward data must be explicitly distinguished from licensed real-city imagery and real merchant campaigns.

## Docker environment

Set a local database password in `.env` first. Do not use this local environment as a public deployment.

```bash
docker compose --env-file .env -f infrastructure/compose.yaml up --build
```

Compose runs a database migration before API startup. Postgres and Redis are private to the Compose network. API/web ports bind only to loopback. `docker compose ... down` retains data; **do not use `down -v` unless deleting local data is intended**.

## Validation

```bash
python -m pytest backend/tests -q
cd apps/consumer-web
npm run build
```

CI contains database migration and isolation checks, dependency audits and frontend build checks. A workflow file is not evidence those checks passed. Docker and AWS Terraform execution may require tools/accounts not available in the creation environment; see [deployment](docs/DEPLOYMENT.md).

[Architecture](docs/ARCHITECTURE.md) · [API](docs/API.md) · [External services](docs/EXTERNAL_SERVICES.md) · [Operations](docs/OPERATIONS.md) · [Roadmap](docs/ROADMAP.md)

## Railway preview

See [the Railway deployment steps](docs/RAILWAY.md). A GitHub repository connected to Railway is required. The public preview route is `/explore`; it displays simulated geometry and never awards unauthenticated rewards.
