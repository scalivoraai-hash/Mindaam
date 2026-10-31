# Separate process liveness from dependency readiness

Read-only production evidence from GitHub run 41151451414 confirms PostgreSQL
connection timeouts and Cloud Run instance-connection 503 errors on revision
mindaam-production-00002-z5r. The deployed launcher monitored /ready after startup,
and Cloud Run's liveness probe called /api/health; both routes require database
and Redis connectivity. This makes a dependency outage trigger process restarts
and repeats startup work, amplifying temporary unavailability.

/api/live is an asynchronous process-only endpoint. The launcher monitors it after
initial readiness and Cloud Run uses it for liveness. Initial startup, /ready,
/api/health, deployment health and release acceptance still require working
dependencies. No timeout, capacity, payment gate or readiness gate is relaxed.
The existing liveness period and failure threshold remain unchanged. This prevents
restart amplification; it does not claim that the underlying database timeouts
are resolved without post-deployment observation.
