# Architecture

```
[ Human ]
    |
    v
[ Buzz Workspace ]  <--- Nostr signed events, channels, identity
    ^           ^
    |           |
[ buzz-acp ]----+---- stdio ACP ----> [ ZeroClaw `zeroclaw acp` ]
    ^                                      ^
    |                                      |
    |                               [ bridge ACP client ]
    |                                      ^
    +----- buzz-cli posts -----------------+
                                           |
                                    [ OpenAGI daemon ]
                                    observations / skills / suggestions
```

- **Buzz** — shared room, identities, optional agent engrams (`buzz mem`)
- **ZeroClaw** — sandboxed body via native ACP
- **OpenAGI** — proactive brain (HTTP API on :43210)
- **Bridge** — OpenAGI signals → ZeroClaw prompts → Buzz visibility + shared memory

Fake HTTP “ACP servers” in older commits are obsolete; see `bridge/legacy/`.
