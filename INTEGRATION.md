# Integration Guide

## 1. Agent Client Protocol (real)

ZeroClaw speaks ACP natively: `zeroclaw acp` (JSON-RPC 2.0, NDJSON stdio).

Bridge client: `bridge/zeroclaw_acp_client.py`

- `initialize` → `session/new` → `session/prompt`
- Handles `session/request_permission` via `ACP_AUTO_PERMISSION`
- Unit-tested with `bridge/tests/mock_acp_agent.py`

Buzz attaches external agents with **`buzz-acp`**, not a custom HTTP port:

```bash
export BUZZ_ACP_AGENT_COMMAND=zeroclaw
export BUZZ_ACP_AGENT_ARGS=acp
buzz-acp
```

## 2. OpenAGI → ZeroClaw

`bridge/openagi_to_zeroclaw.py` polls:

- `GET /proactive/suggestions`
- `GET /pending-actions`
- `GET /skills/suggested`
- optional observations

Maps each signal to a sandbox-oriented prompt and runs it via ACP.

## 3. Buzz posts + identity

`bridge/buzz_publisher.py` calls `buzz messages send` when CLI + keys exist; otherwise appends `.bridge-state/buzz_outbox.jsonl`.

Keys: `scripts/setup-agent-identity.md`

## 4. Shared memory

`bridge/shared_memory.py` dual-writes important facts to:

1. OpenAGI `POST /memory/remember`
2. ZeroClaw (prompt to store)
3. Buzz `mem set` + channel note

## 5. Hardening

Tool execution stays inside ZeroClaw. Bridge should not shell out arbitrary commands except `zeroclaw` / `buzz` CLIs. Review `ACP_AUTO_PERMISSION` before production.
