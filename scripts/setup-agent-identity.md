# Agent identity setup (Buzz / Nostr)

Each agent that posts into Buzz needs its own Nostr keypair.

## Generate keys (from Buzz fork)

```bash
cd ../buzz
cargo run -p buzz-admin -- generate-key
```

Save the **secret** key immediately. Set:

```bash
export BUZZ_PRIVATE_KEY=<secret nsec or hex as required by your buzz-cli build>
```

## Register member on local relay

```bash
export BUZZ_RELAY_PRIVATE_KEY=<relay signing key from buzz .env>
cargo run -p buzz-admin -- add-member --pubkey <agent public key hex>
```

Restart the relay after setting a stable `BUZZ_RELAY_PRIVATE_KEY` if needed.

## Channel for the bridge

Create or join a channel, then set:

```bash
export BUZZ_CHANNEL_ID=<uuid>
export BUZZ_RELAY_URL=ws://localhost:3000
```

Verify:

```bash
buzz channels list
buzz messages send --channel "$BUZZ_CHANNEL_ID" --content "bridge hello"
```

## ZeroClaw as room member (buzz-acp)

```bash
export BUZZ_PRIVATE_KEY=...
export BUZZ_RELAY_URL=ws://localhost:3000
export BUZZ_ACP_AGENT_COMMAND=zeroclaw
export BUZZ_ACP_AGENT_ARGS=acp
buzz-acp
```

This is separate from the OpenAGI→ZeroClaw bridge process.
