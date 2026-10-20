# Load testing plan

No supported concurrency or latency capacity claim has been established. Run only against an isolated staging environment with provider budgets and authorised synthetic accounts. Local unit tests are not load tests.

Measure baseline at 1/10/50 concurrent sessions, then increase cautiously. Mix world reads/moves, nearby presence, chat and server claims. Measure p50/p95/p99 response and delivery latency, errors, CPU/memory, DB locks/connections, Redis bandwidth and browser FPS. Confirm no duplicate rewards or privacy leakage under load. Record hardware, replicas, dataset, test length, bottleneck and recovery. Define product SLOs before a pass/fail decision.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
