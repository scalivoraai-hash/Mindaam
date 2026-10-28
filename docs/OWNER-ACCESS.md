# Owner-controlled staging access

Portal: https://mindaam-staging-qfrofqn4pq-nw.a.run.app/eluvathingal/login
Requested identity: scalivoraai@gmail.com. Do not assume it is the database owner.

The release workflow inspects the actual database read-only using the existing migration job. Review `owner-inspection-result.json` in its artifact. If logging ingestion has not completed, the GCP owner can run:

```bash
gcloud run jobs execute mindaam-migrate-staging --project=mindaam --region=europe-west2 --args=-m,backend.api.owner_access --wait
```

Read the execution's `MINDAAM_OWNER_INSPECTION` log in Cloud Run Jobs. This operation cannot provision or elevate accounts. Authenticate Google Cloud as the authorised project owner; never paste passwords into chat, CI, commands or logs.

## Existing matching Super Admin

If the inspection confirms exactly one matching, unsuspended owner, use **Forgot password?** on the dedicated login page. Delivery uses the existing encrypted email outbox and single-use, expiring reset link to the account mailbox. Mail delivery must be configured. Setting a permanent password via this ownership-proof link revokes old sessions and records an audit event. The reset does not grant or change roles.

If `requested_identity_requires_password_change` is true, the GCP owner may retrieve the initial credential from the existing `mindaam-staging-owner-password` secret in **Google Cloud Console → Secret Manager → secret → enabled version → View secret value**, after checking `mindaam-staging-owner-email` matches the database and requested identity. Only the owner views it. Enter it at the dedicated login and set a different permanent password of at least 12 characters; all sessions are revoked and sign-in is required again. A stale bootstrap secret will not work after a password change; use email recovery instead. Do not rotate a bootstrap secret expecting it to reset an existing user's password.

## No Super Admin and no existing requested identity

Only after the read-only inspection confirms both conditions, the authenticated GCP project owner may bootstrap the account using the existing secrets. In a private owner-controlled Cloud Shell (disable terminal recording), run:

```bash
set +x
umask 077
owner_secret_file=$(mktemp)
trap 'rm -f "$owner_secret_file"' EXIT
python3 -c 'import secrets,sys;sys.stdout.write(secrets.token_urlsafe(48))' > "$owner_secret_file"
printf '%s' 'scalivoraai@gmail.com' | gcloud secrets versions add mindaam-staging-owner-email --project=mindaam --data-file=-
printf '%s' 'mindaam_owner' | gcloud secrets versions add mindaam-staging-owner-username --project=mindaam --data-file=-
gcloud secrets versions add mindaam-staging-owner-password --project=mindaam --data-file="$owner_secret_file"
rm -f "$owner_secret_file"
gcloud run services update mindaam-staging --project=mindaam --region=europe-west2 --update-secrets=SUPER_ADMIN_EMAIL=mindaam-staging-owner-email:latest,SUPER_ADMIN_USERNAME=mindaam-staging-owner-username:latest,SUPER_ADMIN_INITIAL_PASSWORD=mindaam-staging-owner-password:latest
```

This generates a fresh 384-bit temporary secret without printing it. Retrieve it privately in Secret Manager as above. Bootstrap refuses existing identities and additional owners, records `owner.bootstrap`, and requires a password change before admin operations. Verify the resulting database identity and actual login; command execution alone is not proof of successful access.

## Existing different owner or ordinary requested account

STOP. Do not run the bootstrap commands, overwrite email identities, grant roles through SQL, or create another owner. The existing owner must first authenticate/recover their account and establish control of the requested mailbox. An explicit audited identity-transfer procedure is required after verifying both identities; this release does not perform an unverified transfer. Report this as an external owner-access blocker.

MFA is not currently integrated. No MFA enrollment is claimed. Owner access is not verified until the actual owner's login, permanent-password change, subsequent login and dashboard access succeed.
