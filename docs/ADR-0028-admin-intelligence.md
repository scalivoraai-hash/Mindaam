# ADR 0028 — Extend existing operator read models

The private `/eluvathingal` Control Centre keeps its existing authentication, role gate, mutation endpoints and audit mechanisms. Changes are restricted to operator presentation and supporting read models/indexes. Public application behaviour and financial rules are unchanged.

Overview and finance day aggregations reuse a single labelled SQL expression. Independently constructed bound divisors in SELECT and GROUP BY are rejected by PostgreSQL even when their values match; SQLite did not expose this defect. A PostgreSQL CI regression executes the original failing expression, then the corrected Overview and finance reads. Live exception-log correlation requires GCP log access and is not inferred from the local reproduction.

Read models use validated allowlists, stable ordering, bounded page sizes and SQL totals. Directory balances/presence and event attendance/tickets are batched per page. Time-window indexes are additive. Migration checks account for older migrations that create tables from current model metadata on a fresh database. No ledger, claim, payment or user records are rewritten.

Cash aggregates sum unique verified Payment records, not webhook events or virtual currency. Payment reporting is by checkout-created cohort; settlement, fees and subscription cash amounts remain unavailable. Lifetime stocks, current presence and period flows are labelled separately. Recorded consented visits do not imply all visits. Missing chart history is not fabricated. Active histories use distinct user activity days; NPCs never enter user metrics. Existing venue-mode compatibility is retained for historical bookings.

Only live operations polls (15 seconds). Historical/financial dashboards refresh explicitly or on filter changes. Charts include keyboard-readable values and tabular alternatives. Responsive styles are scoped to `.ops-enterprise`, preserving the consumer theme. Local browser fixtures are restricted to disposable local SQLite and do not provision real owners or stage funds.
