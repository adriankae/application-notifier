#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
VENV_DIR="$REPO_DIR/.venv"
HOST_ENV_FILE="${HOST_ENV_FILE:-/etc/application-notifier/application-notifier.env}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
OPENCLAW_CONTAINER_NAME="${OPENCLAW_CONTAINER_NAME:-}"
NOTIFIER_DEPLOY_PATH_IN_CONTAINER="${NOTIFIER_DEPLOY_PATH_IN_CONTAINER:-/app/application-notifier}"
LOCK_PATH="${APPLICATION_NOTIFIER_LOCK_PATH:-/tmp/application-notifier.lock}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

need_cmd docker
need_cmd python3

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "warning: this does not look like a git checkout, continuing anyway" >&2
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/python" -m pip install -e "$REPO_DIR" >/dev/null

if [[ -z "$OPENCLAW_CONTAINER_NAME" ]]; then
  if docker ps --format '{{.Names}}' | grep -qx 'openclaw'; then
    OPENCLAW_CONTAINER_NAME="openclaw"
  else
    echo "set OPENCLAW_CONTAINER_NAME to the running OpenClaw container name" >&2
    exit 1
  fi
fi

if ! docker inspect "$OPENCLAW_CONTAINER_NAME" >/dev/null 2>&1; then
  echo "target OpenClaw container not found: $OPENCLAW_CONTAINER_NAME" >&2
  exit 1
fi

echo "syncing notifier code into container: $OPENCLAW_CONTAINER_NAME"
docker exec "$OPENCLAW_CONTAINER_NAME" mkdir -p "$NOTIFIER_DEPLOY_PATH_IN_CONTAINER"
tar \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  -C "$REPO_DIR" -cf - . | docker exec -i "$OPENCLAW_CONTAINER_NAME" tar -C "$NOTIFIER_DEPLOY_PATH_IN_CONTAINER" -xf -

detected_czm_config=""
for candidate in \
  "${CZM_CONFIG_PATH:-}" \
  "/root/.config/czm/config.toml" \
  "/home/openclaw/.config/czm/config.toml" \
  "/home/ha-assistant/.config/czm/config.toml" \
  "/srv/ha-assistant/.config/czm/config.toml"
do
  if [[ -n "$candidate" ]] && docker exec "$OPENCLAW_CONTAINER_NAME" sh -lc "test -f '$candidate'"; then
    detected_czm_config="$candidate"
    break
  fi
done

if [[ -z "$detected_czm_config" ]]; then
  detected_czm_config="${CZM_CONFIG_PATH:-/root/.config/czm/config.toml}"
fi

export CZM_BASE_URL="${CZM_BASE_URL:-}"
export CZM_API_KEY="${CZM_API_KEY:-}"
export CZM_TIMEZONE="${CZM_TIMEZONE:-Europe/Berlin}"
export CZM_CONFIG_PATH="$detected_czm_config"
export OPENCLAW_BRIDGE_MODE="${OPENCLAW_BRIDGE_MODE:-command}"
export OPENCLAW_BRIDGE_COMMAND="${OPENCLAW_BRIDGE_COMMAND:-}"
export OPENCLAW_BRIDGE_FALLBACK_COMMAND="${OPENCLAW_BRIDGE_FALLBACK_COMMAND:-}"
export OPENCLAW_BRIDGE_TARGET="${OPENCLAW_BRIDGE_TARGET:-}"
export OPENCLAW_BRIDGE_TIMEOUT_SECONDS="${OPENCLAW_BRIDGE_TIMEOUT_SECONDS:-120}"
export OPENCLAW_CONTAINER_NAME
export NOTIFIER_DEPLOY_PATH_IN_CONTAINER
export APPLICATION_NOTIFIER_LOCK_PATH="$LOCK_PATH"

if [[ -z "${OPENCLAW_BRIDGE_COMMAND:-}" ]]; then
  echo "warning: OPENCLAW_BRIDGE_COMMAND is not set; the notifier will dry-run until you point it at a real OpenClaw send path" >&2
fi

if [[ $EUID -eq 0 ]]; then
  install -d -m 0755 "$(dirname "$HOST_ENV_FILE")"
  cat >"$HOST_ENV_FILE" <<EOF
CZM_BASE_URL=${CZM_BASE_URL:-}
CZM_API_KEY=${CZM_API_KEY:-}
CZM_TIMEZONE=${CZM_TIMEZONE:-Europe/Berlin}
CZM_CONFIG_PATH=${detected_czm_config}
OPENCLAW_BRIDGE_MODE=${OPENCLAW_BRIDGE_MODE:-command}
OPENCLAW_BRIDGE_COMMAND=${OPENCLAW_BRIDGE_COMMAND:-}
OPENCLAW_BRIDGE_FALLBACK_COMMAND=${OPENCLAW_BRIDGE_FALLBACK_COMMAND:-}
OPENCLAW_BRIDGE_TARGET=${OPENCLAW_BRIDGE_TARGET:-}
OPENCLAW_BRIDGE_TIMEOUT_SECONDS=${OPENCLAW_BRIDGE_TIMEOUT_SECONDS:-120}
OPENCLAW_CONTAINER_NAME=${OPENCLAW_CONTAINER_NAME}
NOTIFIER_DEPLOY_PATH_IN_CONTAINER=${NOTIFIER_DEPLOY_PATH_IN_CONTAINER}
APPLICATION_NOTIFIER_LOCK_PATH=${LOCK_PATH}
EOF
  chmod 0644 "$HOST_ENV_FILE"
else
  cat >"$REPO_DIR/deploy/systemd/application-notifier.env.generated" <<EOF
CZM_BASE_URL=${CZM_BASE_URL:-}
CZM_API_KEY=${CZM_API_KEY:-}
CZM_TIMEZONE=${CZM_TIMEZONE:-Europe/Berlin}
CZM_CONFIG_PATH=${detected_czm_config}
OPENCLAW_BRIDGE_MODE=${OPENCLAW_BRIDGE_MODE:-command}
OPENCLAW_BRIDGE_COMMAND=${OPENCLAW_BRIDGE_COMMAND:-}
OPENCLAW_BRIDGE_FALLBACK_COMMAND=${OPENCLAW_BRIDGE_FALLBACK_COMMAND:-}
OPENCLAW_BRIDGE_TARGET=${OPENCLAW_BRIDGE_TARGET:-}
OPENCLAW_BRIDGE_TIMEOUT_SECONDS=${OPENCLAW_BRIDGE_TIMEOUT_SECONDS:-120}
OPENCLAW_CONTAINER_NAME=${OPENCLAW_CONTAINER_NAME}
NOTIFIER_DEPLOY_PATH_IN_CONTAINER=${NOTIFIER_DEPLOY_PATH_IN_CONTAINER}
APPLICATION_NOTIFIER_LOCK_PATH=${LOCK_PATH}
EOF
fi

install_unit() {
  local src="$1"
  local dst="$SYSTEMD_DIR/$(basename "$src")"
  if [[ $EUID -eq 0 ]]; then
    install -m 0644 "$REPO_DIR/$src" "$dst"
  else
    echo "sudo install -m 0644 '$REPO_DIR/$src' '$dst'"
  fi
}

install_unit "deploy/systemd/application-notifier-morning.service"
install_unit "deploy/systemd/application-notifier-morning.timer"
install_unit "deploy/systemd/application-notifier-evening.service"
install_unit "deploy/systemd/application-notifier-evening.timer"

if [[ $EUID -eq 0 ]]; then
  systemctl daemon-reload
  systemctl enable --now application-notifier-morning.timer application-notifier-evening.timer
else
  echo "sudo install -m 0644 '$REPO_DIR/deploy/systemd/application-notifier.env.generated' '$HOST_ENV_FILE'"
  echo "sudo systemctl daemon-reload"
  echo "sudo systemctl enable --now application-notifier-morning.timer application-notifier-evening.timer"
fi

echo "dry-run test:"
docker exec \
  -e "CZM_BASE_URL=$CZM_BASE_URL" \
  -e "CZM_API_KEY=$CZM_API_KEY" \
  -e "CZM_TIMEZONE=$CZM_TIMEZONE" \
  -e "CZM_CONFIG_PATH=$CZM_CONFIG_PATH" \
  -e "OPENCLAW_BRIDGE_MODE=$OPENCLAW_BRIDGE_MODE" \
  -e "OPENCLAW_BRIDGE_COMMAND=$OPENCLAW_BRIDGE_COMMAND" \
  -e "OPENCLAW_BRIDGE_FALLBACK_COMMAND=$OPENCLAW_BRIDGE_FALLBACK_COMMAND" \
  -e "OPENCLAW_BRIDGE_TARGET=$OPENCLAW_BRIDGE_TARGET" \
  -e "OPENCLAW_BRIDGE_TIMEOUT_SECONDS=$OPENCLAW_BRIDGE_TIMEOUT_SECONDS" \
  -e "APPLICATION_NOTIFIER_LOCK_PATH=$APPLICATION_NOTIFIER_LOCK_PATH" \
  "$OPENCLAW_CONTAINER_NAME" \
  python "$NOTIFIER_DEPLOY_PATH_IN_CONTAINER/run_reminder.py" --slot morning --dry-run

cat <<EOF

Next steps:
- set OPENCLAW_BRIDGE_COMMAND to the real OpenClaw send wrapper if it is not already configured
- review $HOST_ENV_FILE
- check timer status with:
  systemctl status application-notifier-morning.timer
  systemctl status application-notifier-evening.timer
- inspect logs with:
  journalctl -u application-notifier-morning.service -n 100 --no-pager
  journalctl -u application-notifier-evening.service -n 100 --no-pager
EOF
