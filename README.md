# BuzzClawAGI

**Real integration of Buzz + ZeroClaw + OpenAGI**

This is no longer a manifesto. This repo now contains the working glue that makes the three systems talk to each other.

## Architecture (actual)

- **Buzz** = the shared room (Nostr relay + channels + identity)
- **ZeroClaw** = the hardened agent body (already has native ACP)
- **OpenAGI** = the proactive brain (daemon that watches + decides)

ZeroClaw joins Buzz as a first-class agent via its built-in ACP support.
OpenAGI runs as a daemon and pushes decisions into ZeroClaw / Buzz via the bridge.

## Current status

- ZeroClaw ACP connection to Buzz is documented and scripted
- OpenAGI → ZeroClaw bridge started
- Launch scripts and docker-compose that use *your* forks
- Config templates for the three-way handshake

## How to run (real path)

1. Make sure the three parent forks exist in your account (they do).
2. Clone this repo.
3. Follow `docs/RUN.md`

We are building the real thing now.
