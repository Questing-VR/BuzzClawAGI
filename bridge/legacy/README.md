# Legacy placeholders

These FastAPI stubs (`zeroclaw_acp.py`, `openagi_acp.py`) were early scaffolding.
They do **not** speak Agent Client Protocol.

Use instead:
- `../zeroclaw_acp_client.py` — real stdio JSON-RPC client for `zeroclaw acp`
- `../openagi_client.py` — HTTP client for OpenAGI's real daemon API
