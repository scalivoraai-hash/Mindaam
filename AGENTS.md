# PULSEWORLD engineering
Read docs/PRODUCT.md, docs/ARCHITECTURE.md and docs/STATUS.md before edits. The supplied specification is the target, not a statement of implemented functionality.
Use backend authorization for every mutation and tenant query. No fake production users, activity, payments or rewards. Development data must be explicitly labelled and prohibited outside local/test.
Preserve immutable wallet ledger, nonnegative balances, database transactional idempotency and separate XP/Credits/Perks. Never expose precise device GPS to players.
Do not bypass tests. Run affected tests, update docs and record architecture decisions. No destructive migrations without an explicit plan. Coordinate schema edits. No credentials in source. Do not claim release readiness without evidence for all gates.
