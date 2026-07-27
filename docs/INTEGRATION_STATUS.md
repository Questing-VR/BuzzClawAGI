# Integration Status — Live Progress

**Last updated:** 2026-07-27 (monorepo install path)

## Direct answer: “Are all three integrated as expected?”

**Not as a finished product you never touch again — but the wiring is real and install is unified.**

| Expectation | Reality |
|-------------|---------|
| Agents proactive + sandboxed + in Buzz with their own keys | **Designed path exists**; needs keys, relay, model APIs, and a live smoke on your box |
| Code that speaks real ACP / OpenAGI HTTP / Buzz CLI | **Yes** — bridge v3 |
| All three in **one project** with **1–2 install/start commands** | **Yes now** — `install.ps1` / `start.ps1` pull forks into `deps/` and run |
| Clone only the bridge and magically have binaries | **No** — install clones + builds parents (Rust builds take time) |
| Proven E2E green on CI/this agent host | **Not yet** — unit tests pass; full stack not live-tested here |

## What works in code

| Component | Status |
|-----------|--------|
| ZeroClaw ACP client (stdio JSON-RPC) | Done + unit tests |
| OpenAGI poll (suggestions / actions / skills) | Done + HTTP mock tests |
| Signal → ACP prompt mapping | Done |
| Buzz publish (CLI or outbox) | Done |
| Shared memory dual-write | Done |
| **`install.*` clones all three forks into `deps/`** | Done |
| **`start.*` runs OpenAGI + bridge** | Done |
| Live E2E three-system smoke | **Next on your machine** |

## What’s next to integrate (priority)

1. **Run `.\install.ps1` then `.\start.ps1 -DryRun`** — prove OpenAGI + bridge loop  
2. **Build ZeroClaw** (full install without `-SkipRust`) — live `session/prompt`  
3. **Buzz relay + keys** (`scripts/setup-agent-identity.md`) — real channel posts  
4. **`buzz-acp` + `zeroclaw acp`** — ZeroClaw as room member on @mentions  
5. Optional: suggestion ack API, WebSocket ACP, specialist spawn  

## One-project layout

```
BuzzClawAGI/          ← this git repo (glue + scripts)
  deps/buzz/          ← cloned by install (your fork)
  deps/zeroclaw/
  deps/openAGI/
  bridge/             ← integration runtime
```

Parents stay separate upstream repos (correct for size/history); **this repo is the single place you clone and install**.

## Commands that only install “one thing”

Earlier docs pointed at `pip install -r bridge/requirements.txt` alone — that is **only the glue**.  
Use the root installers instead:

```text
.\install.ps1          # all three + bridge
.\start.ps1            # run OpenAGI + bridge
```

## Known gaps

- Rust builds of Buzz/ZeroClaw can fail without system deps — install still leaves OpenAGI+bridge usable  
- `ACP_AUTO_PERMISSION=allow-once` is a security tradeoff for unattended bridge  
- Buzz relay is heavier than `npm run serve` — may need Docker/`just` from the buzz fork  
