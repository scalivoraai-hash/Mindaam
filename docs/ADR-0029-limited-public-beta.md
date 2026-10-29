# Limited public beta — owner-authorised payment deferral

Continue from f5bc3875a9d5266ad70acc96448802f475c87ba6. No monetary implementation, table, ledger or entitlement is removed. Runtime-owned MINDAAM_PAYMENT_ACTIONS_ENABLED=false gates new Stripe checkout, subscription checkout/portal, paid tickets and Grand Arena booking. Webhooks and existing receipts/refunds remain intact. Production defaults closed; production cannot offer test-mode Checkout.

The expiring limited-public-beta-v1 profile records payment checks as DEFERRED — NOT VERIFIED. Free standard events and a free auditorium exercise the unchanged media assertions/time limits, plus exit/re-entry, wallet reads and admin role denial. The full paid reservation test remains separate and intact. No fake purchased Credits are required by the beta journey.

Beta evidence uses staging-beta-verified.json; it never substitutes for full staging-verified.json. Promotion requires exact SHA/image, direct and forced-TURN evidence, server payment flag, metrics/cost review, private exact-release security review, owner approval and an unexpired policy. The existing backup-before-migration and traffic rollback remain. The review workflow only produces a draft; owner_approved remains false. It does not grant deployment approval.

Existing bootstrap, Railway, databases and production DNS are unchanged. New runtime gating requires a newly built and staged image. Owner login and backup restoration must be actually verified before the security review can pass.

A failed resource gate may still produce a read-only cost-review draft from its actual staged image, recorded measurements and current inventory. Such drafts explicitly report BLOCKED and unverified staging acceptance, retain owner_approved=false, and cannot be saved as release approval without the original verified evidence. Resource thresholds and promotion requirements are unchanged.
