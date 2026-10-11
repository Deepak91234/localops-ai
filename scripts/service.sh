#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
UNIT=localops-ai.service
URL=http://127.0.0.1:8000
ACTION="${1:-status}"

case "$ACTION" in
  start|stop|restart|status|logs) ;;
  -h|--help)
    printf 'Usage: ./scripts/service.sh {start|stop|restart|status|logs}\n'
    printf 'Runs LocalOps in the current systemd user session at %s.\n' "$URL"
    printf 'Survives terminal/chat closure; does not enable startup after reboot.\n'
    exit 0 ;;
  *) printf 'Unknown action: %s\n' "$ACTION" >&2; exit 2 ;;
esac

for tool in systemctl systemd-run curl journalctl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Required command is missing: %s. Use ./scripts/start.sh for foreground startup.\n' "$tool" >&2
    exit 1
  fi
done

if ! LOAD_STATE="$(systemctl --user show "$UNIT" --property=LoadState --value 2>/dev/null)"; then
  printf 'The systemd user session is unavailable. Use ./scripts/start.sh in a terminal.\n' >&2
  exit 1
fi

verify_owner() {
  if [[ "$LOAD_STATE" == not-found ]]; then
    return
  fi
  local directory canonical
  directory="$(systemctl --user show "$UNIT" --property=WorkingDirectory --value)"
  canonical="$(cd -- "$directory" 2>/dev/null && pwd -P)" || canonical=''
  if [[ -z "$directory" || "$canonical" != "$PROJECT_ROOT" ]]; then
    printf 'Refusing to change or inspect %s: its WorkingDirectory belongs to a different project.\n' "$UNIT" >&2
    printf 'Expected: %s\nObserved: %s\n' "$PROJECT_ROOT" "${directory:-unavailable}" >&2
    exit 1
  fi
}

show_logs() {
  journalctl --user-unit="$UNIT" --no-pager -n 50
}

wait_ready() {
  local deadline=$((SECONDS + 10))
  while (( SECONDS < deadline )); do
    if systemctl --user is-active --quiet "$UNIT" && curl --fail --silent --max-time 1 "$URL/api/agents" >/dev/null; then
      printf 'LocalOps AI is ready at %s\n' "$URL"
      printf 'Service: %s; remains running in the current user session.\n' "$UNIT"
      return
    fi
    sleep 0.2
  done
  printf 'LocalOps did not become ready within 10 seconds. Recent service logs:\n' >&2
  show_logs >&2
  return 1
}

start_service() {
  verify_owner
  if [[ "$LOAD_STATE" != not-found ]]; then
    if ! systemctl --user is-active --quiet "$UNIT"; then
      systemctl --user start "$UNIT"
    fi
    wait_ready
    return
  fi
  if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" || ! -f "$PROJECT_ROOT/apps/web/dist/index.html" ]]; then
    printf 'Project dependencies/build are missing. Run ./scripts/bootstrap.sh first.\n' >&2
    exit 1
  fi
  if curl --fail --silent --max-time 1 "$URL/api/agents" >/dev/null; then
    printf 'Port 8000 already serves an application outside this service. Inspect or stop that foreground instance before starting the service.\n' >&2
    exit 1
  fi
  local -a environment=()
  local key
  for key in LLM_BASE_URL MODEL_NAME LLM_API_KEY LLM_TIMEOUT_SECONDS LLM_MAX_TOKENS LOCALOPS_DB_PATH; do
    if [[ -v "$key" ]]; then
      # Names alone let systemd-run obtain values without exposing secrets in argv.
      environment+=("--setenv=$key")
    fi
  done
  systemd-run --user --unit=localops-ai --description='LocalOps AI local private workforce' \
    --collect --property="WorkingDirectory=$PROJECT_ROOT" --property=Type=exec \
    --property=Restart=on-failure --property=RestartSec=2 --property=TimeoutStopSec=10 \
    "${environment[@]}" -- "$PROJECT_ROOT/scripts/start.sh"
  LOAD_STATE=loaded
  wait_ready
}

case "$ACTION" in
  start) start_service ;;
  stop)
    verify_owner
    if [[ "$LOAD_STATE" == not-found ]]; then
      printf 'LocalOps service is already stopped.\n'
    else
      systemctl --user stop "$UNIT"
      printf 'LocalOps service stopped.\n'
    fi ;;
  restart)
    verify_owner
    if [[ "$LOAD_STATE" == not-found ]]; then
      start_service
    else
      systemctl --user restart "$UNIT"
      wait_ready
    fi ;;
  status)
    verify_owner
    if [[ "$LOAD_STATE" == not-found ]]; then
      printf 'LocalOps service is not running. Start it with ./scripts/service.sh start\n'
      exit 3
    fi
    systemctl --user status "$UNIT" --no-pager
    if curl --fail --silent --max-time 1 "$URL/api/agents" >/dev/null; then
      printf '\nAPI is responding at %s\n' "$URL"
    fi ;;
  logs) verify_owner; show_logs ;;
esac
