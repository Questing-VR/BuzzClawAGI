# BuzzClawAGI 🐝🦑🧠

**The threesome from heaven.**

Buzz (Nostr workspace) + ZeroClaw (hardened runtime) + OpenAGI (proactive brain) living in one body.

## Quick Start (the orgy begins)

```bash
git clone https://github.com/Questing-VR/BuzzClawAGI
cd BuzzClawAGI
cp .env.example .env   # fill keys
docker compose up
```

This spins:
- Buzz relay + web UI
- ZeroClaw runtime (sandboxed agent)
- OpenAGI observer (proactive watcher)
- ACP bridge so they talk to each other

Agents appear as full members in Buzz channels with their own Nostr keys.

## How they fuck

1. **Buzz** owns the room (channels, signed events, Git, human presence)
2. **ZeroClaw** owns the body (sandbox, tools, memory, security)
3. **OpenAGI** owns the brain (watches activity, scores signals, spawns specialists, self-improves)

The bridge (ACP) lets OpenAGI tell ZeroClaw "do this", ZeroClaw reports back with signed results into Buzz, and humans see everything in one place.

See `INTEGRATION.md` and `ARCHITECTURE.md` for the dirty details.

Parent forks:
- https://github.com/Questing-VR/buzz
- https://github.com/Questing-VR/zeroclaw
- https://github.com/Questing-VR/openAGI
