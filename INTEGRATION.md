# Integration Guide — Making the Threesome Work

## 1. Agent Client Protocol (ACP) Bridge

Buzz speaks ACP. We make ZeroClaw and OpenAGI speak it too.

`bridge/` contains:
- `zeroclaw_acp.py` — thin ACP server wrapping ZeroClaw tools
- `openagi_acp.py` — ACP server that exposes OpenAGI's proactive signals as tools/events

Buzz agents can then call them as first-class members.

## 2. Shared Identity

Each agent gets its own Nostr keypair (generated on first run).
Buzz treats them as equal members. Permissions are scoped per-channel via Buzz's auth model.

## 3. Memory Sync

- ZeroClaw keeps local GRAPH/RAG + sandbox memory
- OpenAGI keeps long-term user/profile + skill bank
- Important facts are also written as signed Buzz events so the whole team sees them

## 4. Proactive Loop

OpenAGI runs as daemon:
1. Observes (opt-in screen/activity or Buzz events)
2. Scores signals with Adaptive Scrutiny
3. Decides to act → issues tool call via ACP to ZeroClaw
4. ZeroClaw executes sandboxed → returns result
5. Result + new skill (if any) posted back into Buzz channel

## 5. Hardening

Every tool call from OpenAGI goes through ZeroClaw's sandbox (WASM / Landlock / capability tokens). No poison allowed.

## Next concrete steps

- Flesh out the two ACP servers
- Wire OpenAGI's skill writer to post skills into Buzz as reusable artifacts
- Add a "specialist spawner" that creates new ZeroClaw instances on demand
