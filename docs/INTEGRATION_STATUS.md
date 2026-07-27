# Integration Status — Live Progress

**Last updated:** 2026-07-27 (bridge v3)

## What works now (code + tests)

| Component | Status | Notes |
|-----------|--------|--------|
| ZeroClaw ACP **client** (stdio JSON-RPC) | **Implemented** | `bridge/zeroclaw_acp_client.py` — initialize, session/new, session/prompt, permission auto-policy, session/stop |
| Mock ACP agent + unit tests | **Pass** | `bridge/tests/mock_acp_agent.py` + `test_acp_client.py` |
| OpenAGI HTTP client | **Implemented** | Real endpoints: `/proactive/suggestions`, `/pending-actions`, `/skills/suggested`, observations, `/memory/remember` |
| Signal → prompt mapping | **Implemented** | `bridge/signal_map.py` + tests |
| Bridge main loop | **Implemented** | `bridge/openagi_to_zeroclaw.py` v3 — poll, dedup, ACP prompt, Buzz post, shared memory |
| Buzz publisher | **Implemented** | `buzz-cli` subprocess **or** durable outbox JSONL (honest — no fake signatures) |
| Shared memory dual-write | **Implemented** | OpenAGI remember + ZeroClaw prompt + Buzz mem/channel note |
| Docker compose | **Fixed (lean)** | Profiles `bridge-only` / `full`; OpenAGI :43210; no fictional ACP :9001 |
| Launcher | **Updated** | `scripts/start-threesome.sh` + `.ps1` |
| Fake FastAPI “ACP” servers | **Quarantined** | `bridge/legacy/` — not protocol-compatible |

## How the three connect

1. **Buzz** = Nostr workspace / relay (your fork). Agents need Nostr keys (`scripts/setup-agent-identity.md`).
2. **ZeroClaw as room member** = `buzz-acp` with `BUZZ_ACP_AGENT_COMMAND=zeroclaw` + `BUZZ_ACP_AGENT_ARGS=acp` (stdio ACP). **Not** HTTP port 9001.
3. **OpenAGI** = proactive daemon on `http://127.0.0.1:43210`.
4. **Bridge** = polls OpenAGI → `session/prompt` on ZeroClaw ACP → posts results via `buzz` CLI (or outbox).

## Verified this change set

- [x] Unit tests for ACP client against mock agent
- [x] Unit tests for signal map, OpenAGI HTTP mock server, shared memory, outbox
- [ ] Live `zeroclaw acp` on this machine (depends on local binary)
- [ ] Live OpenAGI daemon poll
- [ ] Live `buzz messages send` with real keys/relay
- [ ] E2E three-system run

## Known gaps

- WebSocket gateway ACP client not implemented (stdio primary; HTTP only as optional custom fallback).
- OpenAGI suggestion “ack/dismiss” after handling is local dedup only unless their API is wired later.
- `buzz mem set` needs owner/auth tag; channel note always attempted as human-visible fallback.
- Compose `full` profile builds parent Dockerfiles as-is — may need fork-specific env.
- Bridge auto-allows ACP permissions by default (`ACP_AUTO_PERMISSION=allow-once`) — security tradeoff for unattended operation.

## Next concrete steps

1. Run live smoke with installed `zeroclaw` + OpenAGI.
2. Wire suggestion resolve/dismiss endpoints if/when needed.
3. Optional WS ACP transport for remote ZeroClaw gateway.
4. Specialist spawn remains out of scope.

## File map (v3)

```
bridge/zeroclaw_acp_client.py
bridge/openagi_client.py
bridge/signal_map.py
bridge/buzz_publisher.py
bridge/shared_memory.py
bridge/openagi_to_zeroclaw.py
bridge/tests/*
configs/buzz-acp.env.example
configs/bridge.env.example
configs/zeroclaw-acp.toml.example
```
