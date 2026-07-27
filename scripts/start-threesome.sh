#!/usr/bin/env bash
# One-command launcher for the three systems + bridge
set -e

ROOT=$(pwd)
PARENTS=$(dirname "$ROOT")

echo "=== BuzzClawAGI launcher ==="

# 1. Buzz
if [ -d "$PARENTS/buzz" ]; then
  echo "Starting Buzz relay..."
  (cd "$PARENTS/buzz" && just relay &) || echo "Buzz start failed — start manually"
else
  echo "Missing ../buzz fork"
fi

# 2. ZeroClaw
if [ -d "$PARENTS/zeroclaw" ]; then
  echo "Starting ZeroClaw (ACP mode)..."
  (cd "$PARENTS/zeroclaw" && zeroclaw agent --acp &) || echo "ZeroClaw start failed — start manually"
else
  echo "Missing ../zeroclaw fork"
fi

# 3. OpenAGI
if [ -d "$PARENTS/openAGI" ]; then
  echo "Starting OpenAGI daemon..."
  (cd "$PARENTS/openAGI" && npm run serve &) || echo "OpenAGI start failed — start manually"
else
  echo "Missing ../openAGI fork"
fi

sleep 4

# 4. Bridge
echo "Starting bridge..."
cd "$ROOT/bridge"
python openagi_to_zeroclaw.py
