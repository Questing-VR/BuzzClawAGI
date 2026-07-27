#!/usr/bin/env python3
"""Minimal ACP agent for unit tests. Speaks NDJSON JSON-RPC 2.0 on stdio."""

from __future__ import annotations

import json
import sys


def reply(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    session_id = "s-test-001"
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        rid = msg.get("id")

        if method == "initialize":
            reply(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "protocolVersion": 1,
                        "agentCapabilities": {
                            "loadSession": False,
                            "promptCapabilities": {
                                "image": False,
                                "audio": False,
                                "embeddedContext": False,
                            },
                        },
                        "agentInfo": {
                            "name": "mock-acp",
                            "title": "Mock ACP Agent",
                            "version": "0.0.1",
                        },
                    },
                }
            )
        elif method == "session/new":
            reply(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {"sessionId": session_id, "workspaceDir": "."},
                }
            )
        elif method == "session/prompt":
            params = msg.get("params") or {}
            prompt = params.get("prompt", "")
            if isinstance(prompt, list):
                prompt = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p) for p in prompt
                )
            # stream a chunk
            reply(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "agent_message_chunk",
                            "content": {
                                "type": "text",
                                "text": f"Echo: {prompt[:200]}",
                            },
                        },
                    },
                }
            )
            # optional permission request when prompt contains NEED_PERM
            if "NEED_PERM" in str(prompt):
                reply(
                    {
                        "jsonrpc": "2.0",
                        "id": "zc-out-0",
                        "method": "session/request_permission",
                        "params": {
                            "sessionId": session_id,
                            "options": [
                                {
                                    "optionId": "allow-once",
                                    "name": "Allow once",
                                    "kind": "allow_once",
                                },
                                {
                                    "optionId": "reject-once",
                                    "name": "Reject",
                                    "kind": "reject_once",
                                },
                            ],
                            "toolCall": {
                                "toolCallId": "tc-1",
                                "title": "shell",
                                "kind": "execute",
                                "status": "pending",
                            },
                        },
                    }
                )
                # wait for permission response
                for pline in sys.stdin:
                    pline = pline.strip()
                    if not pline:
                        continue
                    try:
                        presp = json.loads(pline)
                    except json.JSONDecodeError:
                        continue
                    if presp.get("id") == "zc-out-0":
                        break
            reply(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "sessionId": session_id,
                        "stopReason": "end_turn",
                        "content": f"Echo: {prompt[:200]}",
                    },
                }
            )
        elif method == "session/stop":
            reply(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {"sessionId": session_id, "stopped": True},
                }
            )
        elif method == "session/cancel":
            if rid is not None:
                reply({"jsonrpc": "2.0", "id": rid, "result": {}})
        else:
            if rid is not None:
                reply(
                    {
                        "jsonrpc": "2.0",
                        "id": rid,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }
                )


if __name__ == "__main__":
    main()
