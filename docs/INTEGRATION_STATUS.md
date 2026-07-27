# Integration Status — Live Progress

## Completed this session

- ZeroClaw native ACP config example (`configs/zeroclaw-buzz.toml`)
- Improved bridge v2 that actually polls OpenAGI endpoints and maps signals to ZeroClaw tool calls
- One-command launcher script (`scripts/start-threesome.sh`)
- Clear run path documented

## How the three currently connect

1. **Buzz** runs as the Nostr workspace (your fork)
2. **ZeroClaw** joins it via its built-in ACP channel (config provided)
3. **OpenAGI** runs as proactive daemon
4. **Bridge** polls OpenAGI → issues tool calls to ZeroClaw → results can be posted into Buzz

## Immediate next work

- Replace the HTTP ACP placeholder with real stdio JSON-RPC client for ZeroClaw
- Make OpenAGI post signed events directly into Buzz (needs Nostr key generation)
- Add docker-compose that builds from the three forks
- Shared memory path (important facts written to both ZeroClaw memory + Buzz events)

The repo is no longer empty. The wiring is real and advancing.
