# Existing staging owner recovery without SMTP

This is an owner-operated recovery for `mindaam_owner` / `sain@scalivora.com` only.
It is not an HTTP endpoint, GitHub Actions operation, identity transfer or new admin.
The operator must authenticate Google Cloud as that same verified email and retain
existing permission to execute the staging migration job and read its execution log.
No IAM permissions, job configuration, database schema or application image change.

In your private Google Cloud Shell, from the existing Mindaam checkout:

```bash
set +x
umask 077
git pull --ff-only origin main
gcloud auth login sain@scalivora.com
python3 -m venv /tmp/mindaam-owner-recovery-env
/tmp/mindaam-owner-recovery-env/bin/pip install 'cryptography==50.0.1'
/tmp/mindaam-owner-recovery-env/bin/python infrastructure/gcp/owner_recover.py --release-sha 669553d68d6c501b179460a1be485b5d27a1e47b --confirm-owner-recovery
```

The SHA must equal the actual current staging release; the tool fails on drift.
Open `~/mindaam-staging-owner-reset.txt` privately in the Cloud Shell editor and
open its link in your own browser within ten minutes. Never paste the link into
chat or an issue. Set a new permanent password of at least 12 characters, then
delete that file. Sign in at `/eluvathingal/login` with `mindaam_owner`.

Google's authenticated userinfo response verifies the caller's email. Existing
Google IAM authorizes execution. The job verifies its actual staging database
and restricted runtime role, locks the sole verified matching owner, invalidates
previous reset tokens, and audits issuance with the Cloud Run execution ID.
GCP Audit Logs independently identify the executing principal. The reset token
is stored only as a hash in the existing identity table; only RSA-OAEP encrypted
ciphertext appears in job logs. The private key stays in Cloud Shell memory.
No bearer token or password is printed. Only a newly created mode-0600 file gets
the reset link. A lost link expires; do not repeatedly issue replacements.

Issuance does not change the password, create an account or grant a role. The
existing single-use reset handler applies the owner's chosen password, revokes
all sessions, consumes reset tokens and writes its existing password-reset audit.
Actual owner login and dashboard access must still be verified; passing local
tests or issuing a link does not establish successful owner access. No MFA claim.
Production recovery is deliberately unsupported by this staging-only tool.
