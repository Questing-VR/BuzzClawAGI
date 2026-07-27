#!/usr/bin/env python3
"""
Real bridge: OpenAGI proactive decisions → ZeroClaw ACP / Buzz

This is the start of the actual integration.
"""

import os
import time
import requests
from typing import Any

OPENAGI_URL = os.getenv("OPENAGI_URL", "http://127.0.0.1:43210")
ZEROCLAW_ACP = os.getenv("ZEROCLAW_ACP", "http://127.0.0.1:9001")  # or stdio later
BUZZ_RELAY = os.getenv("BUZZ_RELAY", "ws://localhost:3000")

def poll_openagi_signals():
    """Poll OpenAGI for new proactive decisions / suggested actions."""
    try:
        # OpenAGI exposes activity / observations / suggested skills
        r = requests.get(f"{OPENAGI_URL}/observations/search?q=proactive", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"OpenAGI poll error: {e}")
    return []

def send_to_zeroclaw(action: dict[str, Any]):
    """Send a tool call or command to ZeroClaw via ACP."""
    # ZeroClaw ACP is JSON-RPC. This is the shape.
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": action.get("tool", "shell"),
            "arguments": action.get("args", {})
        },
        "id": 1
    }
    try:
        # Placeholder — real ACP is usually stdio or dedicated endpoint
        print(f"[bridge] → ZeroClaw: {payload}")
        # requests.post(ZEROCLAW_ACP, json=payload)  # when HTTP ACP is available
    except Exception as e:
        print(f"ZeroClaw error: {e}")

def main():
    print("BuzzClawAGI bridge started")
    print(f"OpenAGI: {OPENAGI_URL}")
    print(f"ZeroClaw ACP: {ZEROCLAW_ACP}")
    print(f"Buzz: {BUZZ_RELAY}")

    while True:
        signals = poll_openagi_signals()
        for sig in signals:
            # Very rough mapping for now
            if sig.get("type") in ("suggested_skill", "proactive_action", "scrutiny_act"):
                send_to_zeroclaw({
                    "tool": "run_skill" if "skill" in str(sig).lower() else "shell",
                    "args": sig
                })
        time.sleep(10)

if __name__ == "__main__":
    main()
