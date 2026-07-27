#!/usr/bin/env python3
"""
BuzzClawAGI Bridge v2
OpenAGI (proactive brain) → ZeroClaw (hardened body) → Buzz (shared room)
"""

import os
import time
import json
import requests
from datetime import datetime

OPENAGI_URL = os.getenv("OPENAGI_URL", "http://127.0.0.1:43210")
ZEROCLAW_ACP_URL = os.getenv("ZEROCLAW_ACP_URL", "http://127.0.0.1:9001")
BUZZ_CLI = os.getenv("BUZZ_CLI", "buzz-cli")  # if available in PATH
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "8"))

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_openagi_activity():
    """Pull recent proactive signals / suggested skills / observations."""
    endpoints = [
        "/observations/search?q=act",
        "/skills",
        "/memory",
    ]
    results = []
    for ep in endpoints:
        try:
            r = requests.get(f"{OPENAGI_URL}{ep}", timeout=4)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.append(data)
        except Exception as e:
            log(f"OpenAGI {ep} error: {e}")
    return results

def call_zeroclaw(tool: str, args: dict):
    """Send a tool call to ZeroClaw (ACP shape)."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": args
        },
        "id": int(time.time())
    }
    log(f"→ ZeroClaw tool={tool}")
    try:
        # When ZeroClaw exposes HTTP ACP this will work.
        # Until then it prints the call so you can wire stdio.
        r = requests.post(ZEROCLAW_ACP_URL, json=payload, timeout=10)
        log(f"ZeroClaw response: {r.status_code}")
        return r.json() if r.ok else None
    except Exception as e:
        log(f"ZeroClaw call failed (expected if no HTTP ACP yet): {e}")
        # Fallback: print the JSON-RPC so it can be piped into stdio ACP
        print(json.dumps(payload))
        return None

def post_to_buzz(text: str):
    """Best-effort post into Buzz (via buzz-cli if available)."""
    log(f"Would post to Buzz: {text[:120]}...")
    # Real version will use buzz-cli or direct Nostr event

def process_signal(sig: dict):
    """Map an OpenAGI signal into a ZeroClaw action."""
    sig_type = str(sig.get("type", "")).lower()
    name = str(sig.get("name", sig.get("skill", "unknown")))

    if "skill" in sig_type or "suggested" in str(sig).lower():
        call_zeroclaw("run_skill", {"skill": name, "source": "openagi"})
        post_to_buzz(f"OpenAGI suggested skill `{name}` — handed to ZeroClaw")
    elif "act" in sig_type or "scrutiny" in str(sig).lower():
        call_zeroclaw("shell", {"command": "echo 'proactive action received'"})
        post_to_buzz(f"OpenAGI decided to act: {name}")
    else:
        log(f"Ignoring signal type: {sig_type}")

def main():
    log("BuzzClawAGI bridge v2 started")
    log(f"OpenAGI  → {OPENAGI_URL}")
    log(f"ZeroClaw → {ZEROCLAW_ACP_URL}")

    seen = set()

    while True:
        signals = get_openagi_activity()
        for sig in signals:
            # crude dedup
            key = json.dumps(sig, sort_keys=True)[:200]
            if key in seen:
                continue
            seen.add(key)
            process_signal(sig)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
