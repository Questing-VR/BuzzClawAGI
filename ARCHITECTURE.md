# Architecture of the Threesome

```
[ Human ]
    |
    v
[ Buzz Workspace ]  <--- Nostr signed events, channels, Git, identity
    ^           ^
    |           |
[ ACP Bridge ]--+-----> [ ZeroClaw Runtime ]  (sandboxed body + tools)
    |
    +-----> [ OpenAGI Daemon ]  (proactive brain + skill evolution)
```

- Buzz is the shared nervous system and social layer
- ZeroClaw is the secure execution body
- OpenAGI is the always-on mind that decides when and what to do

All three share cryptographic identity and memory via signed Buzz events + local stores.

Result: agents that act before you ask, never leave the sandbox, and collaborate in the same room as humans.
