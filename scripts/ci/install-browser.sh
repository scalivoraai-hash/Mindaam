#!/usr/bin/env bash
set -euo pipefail

# Hosted Ubuntu's Azure mirror repeatedly stalls on Playwright's font packages.
# Keep apt's signed Noble repositories, package versions and full browser deps.
mirrors=/etc/apt/apt-mirrors.txt
if [[ "${GITHUB_ACTIONS:-}" == true && -f "$mirrors" ]] && grep -Fq 'http://azure.archive.ubuntu.com/ubuntu' "$mirrors"; then
  sudo sed -i 's|http://azure.archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' "$mirrors"
fi
exec "$1" install --with-deps "$2"
