#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
MODE="${1:-production}"
case "$MODE" in
  production|--dev) ;;
  -h|--help)
    printf 'Usage: ./scripts/start.sh [--dev]\nDefault: built app at http://127.0.0.1:8000\nDev: Vite at http://127.0.0.1:5173 plus API at :8000\n'
    exit 0 ;;
  *) printf 'Unknown option: %s\n' "$MODE" >&2; exit 2 ;;
esac

# Read known configuration as literal values. Never execute a .env file as shell code.
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    if [[ "$line" =~ ^[[:space:]]*(LLM_BASE_URL|MODEL_NAME|LLM_API_KEY|LLM_TIMEOUT_SECONDS|LLM_MAX_TOKENS|LOCALOPS_DB_PATH)[[:space:]]*=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      value="${value#"${value%%[![:space:]]*}"}"
      value="${value%"${value##*[![:space:]]}"}"
      if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then
        value="${value:1:${#value}-2}"
      fi
      if [[ ! -v "$key" ]]; then
        export "$key=$value"
      fi
    fi
  done < .env
fi

if [[ ! -x .venv/bin/python ]]; then
  printf 'Project dependencies are missing. Run ./scripts/bootstrap.sh first.\n' >&2
  exit 1
fi
if [[ "$MODE" == production ]]; then
  if [[ ! -f apps/web/dist/index.html ]]; then
    if [[ ! -d apps/web/node_modules ]]; then
      printf 'Browser dependencies are missing. Run ./scripts/bootstrap.sh first.\n' >&2
      exit 1
    fi
    npm --prefix apps/web run build
  fi
  printf 'LocalOps AI: http://127.0.0.1:8000\nAPI reference: http://127.0.0.1:8000/docs\n'
  exec .venv/bin/python -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 5
fi

API_PID=''
WEB_PID=''
cleanup() {
  [[ -z "$API_PID" ]] || kill "$API_PID" 2>/dev/null || true
  [[ -z "$WEB_PID" ]] || kill "$WEB_PID" 2>/dev/null || true
  [[ -z "$API_PID" ]] || wait "$API_PID" 2>/dev/null || true
  [[ -z "$WEB_PID" ]] || wait "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM
.venv/bin/python -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 5 &
API_PID=$!
npm --prefix apps/web run dev -- --host 127.0.0.1 --port 5173 --strictPort &
WEB_PID=$!
printf 'Development app: http://127.0.0.1:5173\nPress Ctrl+C to stop both project processes.\n'
wait -n "$API_PID" "$WEB_PID"
