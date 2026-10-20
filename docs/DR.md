# Disaster recovery

RDS scaffold retains seven days of backups and protects deletion. S3 versioning is enabled. This is not a tested recovery guarantee. RPO and RTO must be agreed with the business and measured in a restore exercise.

1. Freeze financial mutations and record the last known good app/database revision and provider event watermark.
2. Restore RDS PITR/snapshot to a separate private instance. Verify schema and nonnegative wallet balances; reconcile immutable ledger totals against balances and Stripe events.
3. Restore required S3 object versions subject to deletion/retention rules. Redis presence is ephemeral: expire old sessions and let clients reconnect, do not replay stale user locations.
4. Rotate compromised credentials, update Secrets Manager, deploy compatible task revisions and validate readiness and critical journeys.
5. Switch traffic deliberately; monitor duplicate webhook/reward handling and document data loss/time to recovery.

Never erase the incident database before evidence preservation and reconciliation. Schedule quarterly restore drills before production and store measured outcomes in release evidence.
