# BuzzClawAGI

**One project** that wires together:

| Role | System | Your fork |
|------|--------|-----------|
| Shared room | **Buzz** (Nostr workspace) | `Questing-VR/buzz` |
| Sandboxed body | **ZeroClaw** (ACP agent) | `Questing-VR/zeroclaw` |
| Proactive brain | **OpenAGI** (HTTP daemon) | `Questing-VR/openAGI` |
| Glue | **bridge/** (this repo) | polls OpenAGI → ZeroClaw ACP → Buzz |

## Are all three “fully integrated”?

**Partially — honest status:**

| Layer | Ready? |
|-------|--------|
| Real protocol glue (ACP client, OpenAGI HTTP, Buzz CLI/outbox, shared memory) | **Yes** (unit-tested) |
| Single-repo install that pulls all three forks into `deps/` | **Yes** (`.\install.ps1` / `./install.sh`) |
| One-command start of OpenAGI + bridge | **Yes** (`.\start.ps1` / `./start.sh`) |
| Live E2E on your machine with real keys + relay | **You still run once** (keys, model APIs, Buzz relay) |
| Buzz desktop / full relay stack “just works” everywhere | **Not guaranteed** — Buzz is a large monorepo; relay needs its own deps (`just relay`) |

Details: [docs/INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md)

## Install everything (1–2 commands)

**Windows (PowerShell):**

```powershell
git clone https://github.com/Questing-VR/BuzzClawAGI.git
cd BuzzClawAGI
.\install.ps1
```

Faster first pass (skip long Rust builds — OpenAGI + bridge only):

```powershell
.\install.ps1 -SkipRust
```

**Linux/macOS:**

```bash
git clone https://github.com/Questing-VR/BuzzClawAGI.git
cd BuzzClawAGI
chmod +x install.sh start.sh scripts/*.sh
./install.sh
# or: ./install.sh --skip-rust
```

What install does:

1. Clones **your three forks** into `deps/buzz`, `deps/zeroclaw`, `deps/openAGI`
2. `npm install` for OpenAGI  
3. `cargo build --release` for ZeroClaw + `buzz-cli` / `buzz-acp` (unless skipped)  
4. `pip install` + runs bridge unit tests  
5. Creates `.env` from `.env.example` and writes `deps/path.ps1` / `path.sh`

## Start (1 command)

```powershell
.\start.ps1
# dry-run (no ZeroClaw required):
.\start.ps1 -DryRun
```

```bash
./start.sh
DRY_RUN=1 ./start.sh --dry-run
```

That starts **OpenAGI** and the **bridge**. For ZeroClaw as a **Buzz channel member**, also run `buzz-acp` after the relay is up (see `configs/buzz-acp.env.example`).

## Architecture

```
deps/openAGI  --HTTP-->  bridge/  --stdio ACP-->  deps/zeroclaw (zeroclaw acp)
                              |
                              +-- buzz-cli --> deps/buzz relay
```

## Layout

```
BuzzClawAGI/
  install.ps1 / install.sh     ← clone + build all three + bridge
  start.ps1 / start.sh         ← run stack
  bridge/                      ← integration code
  deps/                        ← filled by install (not in git)
  configs/                     ← env examples
  docs/
```

## Prerequisites

| Tool | Needed for |
|------|------------|
| Git | clone forks |
| Python 3.10+ | bridge |
| Node 22+ | OpenAGI |
| Rust/cargo | ZeroClaw + Buzz CLIs (optional with `-SkipRust`) |
| Model API keys | real agent turns (in parent configs / `.env`) |

## Docs

- [docs/RUN.md](docs/RUN.md) — detailed runbook  
- [docs/INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md) — what’s done vs next  
- [scripts/setup-agent-identity.md](scripts/setup-agent-identity.md) — Nostr keys for Buzz  
