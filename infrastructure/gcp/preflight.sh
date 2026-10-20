#!/usr/bin/env bash
# Read-only: never infers a project or modifies the original deployment.
set -euo pipefail
: "${MINDAAM_PROJECT_ID:?Set the verified dedicated Mindaam project ID}"
command -v gcloud >/dev/null || { echo 'Google Cloud CLI is unavailable.' >&2; exit 1; }
account=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')
[[ "$account" == sain@scalivora.com ]] || { echo 'Use the authorized sain@scalivora.com Google Cloud account.' >&2; exit 1; }
label=$(gcloud projects describe "$MINDAAM_PROJECT_ID" --format='value(labels.application)')
[[ "$label" == mindaam ]] || { echo 'Confirm this dedicated project and label it application=mindaam before provisioning.' >&2; exit 1; }
gcloud billing projects describe "$MINDAAM_PROJECT_ID" --format='table(projectId,billingEnabled)'
gcloud run services list --project "$MINDAAM_PROJECT_ID" --format='table(metadata.name,status.url)'
gcloud compute instances list --project "$MINDAAM_PROJECT_ID" --format='table(name,zone,machineType,status)'
