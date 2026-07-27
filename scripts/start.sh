#!/usr/bin/env bash
# Start OpenAGI + bridge. Optional --bridge-only / --dry-run.
set -euo pipefail

BRIDGE_ONLY=0
DRY_RUN_FLAG=0
for arg in "$@"; do
  case "$arg" in
    --bridge-only) BRIDGE_ONLY=1 ;;
    --dry-run) DRY_RUN_FLAG=1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS="$ROOT/deps"

if [[ -f "$DEPS/path.sh" ]]; then
  # shellcheck disable=SC1091
  source "$DEPS/path.sh"
else
  echo "WARN: deps/path.sh missing — run ./scripts/install.sh first"
  export OPENAGI_PATH="${OPENAGI_PATH:-$DEPS/openAGI}"
  export ZEROCLAW_PATH="${ZEROCLAW_PATH:-$DEPS/zeroclaw}"
  export BUZZ_PATH="${BUZZ_PATH:-$DEPS/buzz}"
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

[[ "$DRY_RUN_FLAG" -eq 1 ]] && export DRY_RUN=1
export OPENAGI_URL="${OPENAGI_URL:-http://127.0.0.1:43210}"
export BRIDGE_STATE_DIR="${BRIDGE_STATE_DIR:-$ROOT/.bridge-state}"

if [[ -z "${ZEROCLAW_ACP_CMD:-}" ]]; then
  if [[ -x "$ZEROCLAW_PATH/target/release/zeroclaw" ]]; then
    export ZEROCLAW_ACP_CMD="$ZEROCLAW_PATH/target/release/zeroclaw acp"
  else
    export ZEROCLAW_ACP_CMD="zeroclaw acp"
  fi
fi

OA_PID=""
cleanup() {
  if [[ -n "$OA_PID" ]] && kill -0 "$OA_PID" 2>/dev/null; then
    echo "Stopping OpenAGI pid=$OA_PID"
    kill "$OA_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "=== BuzzClawAGI start ==="
echo "OPENAGI_URL=$OPENAGI_URL DRY_RUN=${DRY_RUN:-0}"

if [[ "$BRIDGE_ONLY" -eq 0 ]]; then
  if [[ ! -d "$OPENAGI_PATH" ]]; then
    echo "OpenAGI missing at $OPENAGI_PATH — run ./scripts/install.sh"
    exit 1
  fi
  ENTRY="$OPENAGI_PATH/examples/hosted-server.js"
  LOGDIR="${BRIDGE_STATE_DIR:-$ROOT/.bridge-state}"
  mkdir -p "$LOGDIR"
  echo "Starting OpenAGI via node $ENTRY ..."
  if [[ -f "$ENTRY" ]]; then
    (cd "$OPENAGI_PATH" && node "$ENTRY" >"$LOGDIR/openagi.stdout.log" 2>"$LOGDIR/openagi.stderr.log") &
  else
    (cd "$OPENAGI_PATH" && npm run serve >"$LOGDIR/openagi.stdout.log" 2>"$LOGDIR/openagi.stderr.log") &
  fi
  OA_PID=$!
  echo "OpenAGI pid=$OA_PID — waiting for /health"
  ok=0
  for i in $(seq 1 60); do
    if curl -sf "${OPENAGI_URL}/health" >/dev/null 2>&1; then
      echo "OpenAGI is up"
      ok=1
      break
    fi
    if ! kill -0 "$OA_PID" 2>/dev/null; then
      echo "OpenAGI exited early — see $LOGDIR/openagi.stderr.log"
      tail -n 40 "$LOGDIR/openagi.stderr.log" 2>/dev/null || true
      exit 1
    fi
    sleep 1
  done
  if [[ "$ok" -ne 1 ]]; then
    echo "OpenAGI did not become healthy — aborting (see $LOGDIR/openagi.stderr.log)"
    exit 1
  fi
fi

echo "Starting bridge..."
cd "$ROOT/bridge"
export BRIDGE_STATE_DIR="${BRIDGE_STATE_DIR:-$ROOT/.bridge-state}"
python3 openagi_to_zeroclaw.py
