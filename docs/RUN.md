# How to run BuzzClawAGI

## Prerequisites

Sibling forks (or override paths with `BUZZ_PATH`, `ZEROCLAW_PATH`, `OPENAGI_PATH`):

- https://github.com/Questing-VR/buzz  
- https://github.com/Questing-VR/zeroclaw  
- https://github.com/Questing-VR/openAGI  

Also: Python 3.10+, Node 22+ (OpenAGI), Rust toolchains for Buzz/ZeroClaw if building from source.

Copy env template:

```bash
cp .env.example .env
# fill BUZZ_* and OPENAGI_AUTH_TOKEN as needed
```

## Path A — Proactive bridge (OpenAGI → ZeroClaw → Buzz)

### 1. OpenAGI daemon

```bash
cd ../openAGI
npm install
npm run serve
# http://127.0.0.1:43210  — GET /health
```

### 2. ZeroClaw ACP binary on PATH

```bash
cd ../zeroclaw
cargo build --release
# ensure `zeroclaw` is on PATH; bridge runs: zeroclaw acp
```

### 3. Buzz CLI (optional but needed for real posts)

```bash
cd ../buzz
cargo build --release -p buzz-cli
export PATH="$PWD/target/release:$PATH"
# see scripts/setup-agent-identity.md
```

### 4. Bridge

```bash
cd bridge
pip install -r requirements.txt
# dry run first (no ZeroClaw required):
DRY_RUN=1 python openagi_to_zeroclaw.py
# live:
export OPENAGI_URL=http://127.0.0.1:43210
export ZEROCLAW_ACP_CMD="zeroclaw acp"
export BUZZ_CHANNEL_ID=...
export BUZZ_PRIVATE_KEY=...
python openagi_to_zeroclaw.py
```

Windows:

```powershell
.\scripts\start-threesome.ps1
```

## Path B — ZeroClaw as Buzz channel member

```bash
# after building buzz-acp + zeroclaw
export BUZZ_PRIVATE_KEY=nsec1...
export BUZZ_RELAY_URL=ws://localhost:3000
export BUZZ_ACP_AGENT_COMMAND=zeroclaw
export BUZZ_ACP_AGENT_ARGS=acp
buzz-acp
```

See `configs/buzz-acp.env.example`.

## Docker (lean)

```bash
# with ../openAGI present
docker compose --profile bridge-only up --build
# default DRY_RUN=1 inside compose unless overridden
```

Full monorepo builds of Buzz/ZeroClaw: `--profile full` (heavy; may need fork-specific env).

## Tests (no parents required)

```bash
cd bridge
pip install -r requirements.txt
python -m pytest tests -q
```

## What actually talks to what

| Hop | Protocol |
|-----|----------|
| Bridge → OpenAGI | HTTP `GET /proactive/suggestions`, `/pending-actions`, `/skills/suggested`, … |
| Bridge → ZeroClaw | ACP JSON-RPC 2.0 NDJSON over stdio (`session/prompt`) |
| Bridge → Buzz | `buzz messages send` / `buzz mem set`, or local outbox JSONL |
| Buzz room ↔ ZeroClaw | `buzz-acp` spawns `zeroclaw acp` |
