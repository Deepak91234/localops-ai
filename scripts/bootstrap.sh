#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

for tool in python3 node npm; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Required command is missing: %s\n' "$tool" >&2
    exit 1
  fi
done
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"'
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
API_REQUIREMENTS=services/api/requirements.txt
if [[ -f services/api/requirements.lock.txt ]]; then
  API_REQUIREMENTS=services/api/requirements.lock.txt
fi
.venv/bin/python -m pip install -r "$API_REQUIREMENTS"
npm --prefix apps/web ci --no-audit --no-fund
npm --prefix apps/web run build
printf '\nDependencies and browser build ready. Run ./scripts/start.sh\n'
printf 'This setup uses the existing local model; it does not download weights or change system services.\n'
