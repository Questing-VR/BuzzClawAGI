# BuzzClawAGI

Working glue for **Buzz** (Nostr workspace) + **ZeroClaw** (sandboxed ACP agent) + **OpenAGI** (proactive daemon).

## Architecture

```
OpenAGI (:43210) --HTTP--> bridge --stdio ACP--> zeroclaw acp
                              |
                              +-- buzz-cli --> Buzz relay (:3000)

Separately: buzz-acp spawns `zeroclaw acp` so ZeroClaw is a channel member.
```

## Status

See **[docs/INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md)** for what is implemented vs still untested live.

## Quick start

```bash
cp .env.example .env
# tests (no parents required)
cd bridge && pip install -r requirements.txt && python -m pytest tests -q
# dry-run bridge
DRY_RUN=1 python openagi_to_zeroclaw.py
```

Full run instructions: **[docs/RUN.md](docs/RUN.md)**  
Identity setup: **[scripts/setup-agent-identity.md](scripts/setup-agent-identity.md)**

## Parent forks

- https://github.com/Questing-VR/buzz  
- https://github.com/Questing-VR/zeroclaw  
- https://github.com/Questing-VR/openAGI  

## Layout

| Path | Role |
|------|------|
| `bridge/` | ACP client, OpenAGI client, Buzz publisher, main loop |
| `configs/` | Env/config examples for ACP + buzz-acp |
| `scripts/` | Launchers + identity notes |
| `docker-compose.yml` | Profiles `bridge-only` / `full` |
