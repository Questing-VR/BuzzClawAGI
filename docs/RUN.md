# How to actually run the threesome

## Prerequisites

- Your three forks:
  - https://github.com/Questing-VR/buzz
  - https://github.com/Questing-VR/zeroclaw
  - https://github.com/Questing-VR/openAGI
- Docker + Docker Compose
- Rust toolchain (for ZeroClaw / Buzz if building from source)
- Node 20+ (for OpenAGI)

## Step 1 — Start Buzz relay

```bash
cd ../buzz
just setup
just relay          # or just dev for full desktop
```

Buzz will be on `ws://localhost:3000`

## Step 2 — Start ZeroClaw as a Buzz agent (ACP)

ZeroClaw already speaks ACP natively.

```bash
cd ../zeroclaw
# configure an agent that uses ACP channel pointing at Buzz
zeroclaw agent --acp --buzz-relay ws://localhost:3000
```

(Exact flag names may vary — check `zeroclaw channels acp --help` after install)

This makes ZeroClaw appear as a full member inside Buzz with its own keypair.

## Step 3 — Start OpenAGI daemon

```bash
cd ../openAGI
npm install
npm run serve
```

OpenAGI runs on `http://127.0.0.1:43210`

## Step 4 — Run the bridge

From this repo:

```bash
cd bridge
pip install -r requirements.txt
python openagi_to_zeroclaw.py
```

The bridge listens to OpenAGI proactive signals / decisions and turns them into ZeroClaw tool calls or Buzz posts.

## What happens

OpenAGI notices patterns → scores them → decides to act → bridge tells ZeroClaw → ZeroClaw executes sandboxed → result (and any new skill) is posted into the Buzz channel as a signed event.

Humans see everything in one room.
