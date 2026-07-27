#!/usr/bin/env bash
# Launch OpenAGI + bridge (and optionally document Buzz / ZeroClaw).
# Real room membership is: buzz-acp + `zeroclaw acp` (see configs/buzz-acp.env.example).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENTS="$(dirname "$ROOT")"
BUZZ_DIR="${BUZZ_PATH:-$PARENTS/buzz}"
ZC_DIR="${ZEROCLAW_PATH:-$PARENTS/zeroclaw}"
OA_DIR="${OPENAGI_PATH:-$PARENTS/openAGI}"

echo "=== BuzzClawAGI launcher ==="
echo "root=$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$ROOT/.env"; set +a
  echo "loaded .env"
fi

# 1. Buzz relay (best-effort)
if [[ -d "$BUZZ_DIR" ]]; then
  echo "Buzz fork found at $BUZZ_DIR"
  if command -v just >/dev/null 2>&1; then
    echo "Starting Buzz relay (just relay) in background..."
    (cd "$BUZZ_DIR" && just relay) &
  else
    echo "Install just + follow buzz docs to start relay (ws://localhost:3000)"
  fi
else
  echo "Missing Buzz fork at $BUZZ_DIR (set BUZZ_PATH)"
fi

# 2. OpenAGI
if [[ -d "$OA_DIR" ]]; then
  echo "Starting OpenAGI daemon..."
  (cd "$OA_DIR" && npm run serve) &
else
  echo "Missing OpenAGI fork at $OA_DIR (set OPENAGI_PATH)"
fi

sleep 3

# 3. Bridge
echo "Starting bridge (OpenAGI → ZeroClaw ACP → Buzz)..."
cd "$ROOT/bridge"
python -m pip install -q -r requirements.txt
export OPENAGI_URL="${OPENAGI_URL:-http://127.0.0.1:43210}"
export ZEROCLAW_ACP_CMD="${ZEROCLAW_ACP_CMD:-zeroclaw acp}"
python openagi_to_zeroclaw.py

# Note: for ZeroClaw to appear as a channel member, run separately:
#   export $(grep -v '^#' configs/buzz-acp.env.example | xargs)  # with real secrets
#   buzz-acp
