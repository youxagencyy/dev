#!/bin/sh
# Restart python3 -m newsbot if it exits. Refuse a second copy.
# Secrets stay in the env file; this script does not print them.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
LOCK="${NEWSBOT_LOCK:-/tmp/newsbot-poll.lock}"
ENV_FILE="${NEWSBOT_ENV:-$ROOT/.env}"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "newsbot already running" >&2
  exit 1
fi

cd "$ROOT"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi
export PYTHONPATH="${PYTHONPATH:-$ROOT/src}"
export CONFIG_PATH="${CONFIG_PATH:-$ROOT/config.yaml}"
export DATABASE_PATH="${DATABASE_PATH:-$ROOT/data/newsbot.sqlite}"

while true; do
  python3 -m newsbot || true
  sleep 2
done
