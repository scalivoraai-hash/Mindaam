# Unified Railway/VPS image: Next.js and FastAPI share one public origin.
FROM node:22-bookworm-slim AS web-build
WORKDIR /source
COPY package.json package-lock.json ./
COPY apps/consumer-web/package.json apps/consumer-web/package.json
RUN npm ci --ignore-scripts
COPY apps/consumer-web apps/consumer-web
COPY shared shared
ENV API_INTERNAL_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1
RUN node --experimental-strip-types --test apps/consumer-web/lib/autoPickup.test.mjs && npm run build
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd --uid 10001 --create-home pulse
COPY backend backend
COPY shared shared
RUN APP_ENV=test DATABASE_URL=sqlite:////tmp/pulse-build-tests.db python -m pytest backend/tests -q
COPY scripts/start-deployment.py scripts/start-deployment.py
COPY --from=web-build /source/apps/consumer-web/.next/standalone web
COPY --from=web-build /source/apps/consumer-web/.next/static web/apps/consumer-web/.next/static
COPY --from=web-build /source/apps/consumer-web/public web/apps/consumer-web/public
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PYTHONUNBUFFERED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN chown -R pulse:pulse /app
USER pulse
EXPOSE 3000
CMD ["python", "scripts/start-deployment.py"]
