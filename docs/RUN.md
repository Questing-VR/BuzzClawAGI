# How to run BuzzClawAGI

## Recommended: one project install

From the **BuzzClawAGI** repo root (this is the combined project):

```powershell
# Windows
.\install.ps1              # clones deps/buzz, deps/zeroclaw, deps/openAGI + builds + bridge tests
.\start.ps1 -DryRun        # OpenAGI + bridge without needing ZeroClaw yet
.\start.ps1                # live (uses deps/zeroclaw if built)
```

```bash
# Linux/macOS
./install.sh
./start.sh --dry-run
./start.sh
```

Faster install (OpenAGI + Python bridge only):

```powershell
.\install.ps1 -SkipRust
```

Install pulls **your three forks** into `deps/` so you do not juggle sibling checkouts by hand.

## Prerequisites

| Tool | Role |
|------|------|
| Git | clone forks into `deps/` |
| Python 3.10+ | bridge |
| Node 22+ | OpenAGI |
| Rust/cargo | ZeroClaw + buzz-cli/buzz-acp (optional with `-SkipRust` / `--skip-rust`) |

Edit `.env` (created from `.env.example`) for `BUZZ_*` and tokens.

## Manual path (if you prefer sibling repos)

Set `BUZZ_PATH` / `ZEROCLAW_PATH` / `OPENAGI_PATH` or keep classic siblings and use older `scripts/start-threesome.*` helpers.

### OpenAGI only

```bash
cd deps/openAGI   # after install
npm run serve
```

### Bridge only

```bash
cd bridge
DRY_RUN=1 python openagi_to_zeroclaw.py
```

## ZeroClaw as Buzz channel member

After install has built binaries:

```bash
export PATH="$PWD/deps/zeroclaw/target/release:$PWD/deps/buzz/target/release:$PATH"
export BUZZ_PRIVATE_KEY=nsec1...
export BUZZ_RELAY_URL=ws://localhost:3000
export BUZZ_ACP_AGENT_COMMAND=zeroclaw
export BUZZ_ACP_AGENT_ARGS=acp
buzz-acp
```

See `configs/buzz-acp.env.example` and `scripts/setup-agent-identity.md`.

## Docker (lean)

```bash
# install first so deps/openAGI exists, or set OPENAGI_PATH
docker compose --profile bridge-only up --build
```

## Tests (bridge only, no parents)

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
