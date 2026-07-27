#!/usr/bin/env python3
"""Post messages (and optional mem engrams) into Buzz via buzz-cli.

If buzz CLI is unavailable, appends durable outbox JSONL — never pretends to
have signed a Nostr event.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("buzzclaw.buzz")


@dataclass
class PublishResult:
    ok: bool
    mode: str  # cli | outbox | skipped
    detail: str
    raw: Optional[str] = None


class BuzzPublisher:
    def __init__(
        self,
        *,
        channel_id: Optional[str] = None,
        cli: Optional[str] = None,
        state_dir: Optional[str] = None,
        private_key: Optional[str] = None,
        relay_url: Optional[str] = None,
        owner: Optional[str] = None,
    ):
        self.channel_id = channel_id or os.getenv("BUZZ_CHANNEL_ID", "")
        self.cli = cli or os.getenv("BUZZ_CLI", "buzz")
        self.state_dir = Path(state_dir or os.getenv("BRIDGE_STATE_DIR", ".bridge-state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.outbox = self.state_dir / "buzz_outbox.jsonl"
        self.private_key = private_key or os.getenv("BUZZ_PRIVATE_KEY", "")
        self.relay_url = relay_url or os.getenv("BUZZ_RELAY_URL", "ws://localhost:3000")
        self.owner = owner or os.getenv("BUZZ_OWNER_PUBKEY", "")

    def available(self) -> bool:
        return shutil.which(self.cli) is not None or Path(self.cli).exists()

    def _env(self) -> Dict[str, str]:
        env = os.environ.copy()
        if self.private_key:
            env["BUZZ_PRIVATE_KEY"] = self.private_key
        if self.relay_url:
            env["BUZZ_RELAY_URL"] = self.relay_url
        return env

    def post_message(self, content: str, *, channel_id: Optional[str] = None) -> PublishResult:
        text = (content or "").strip()
        if not text:
            return PublishResult(False, "skipped", "empty content")
        ch = channel_id or self.channel_id
        if not ch:
            return self._outbox("message", {"content": text, "error": "BUZZ_CHANNEL_ID not set"})

        if not self.available():
            return self._outbox(
                "message",
                {
                    "channel": ch,
                    "content": text,
                    "note": "buzz CLI not found; queued for later",
                },
            )

        if not self.private_key:
            log.warning("BUZZ_PRIVATE_KEY not set — CLI may fail auth")

        cmd = [
            self.cli,
            "messages",
            "send",
            "--channel",
            ch,
            "--content",
            text,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=self._env(),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return self._outbox(
                "message",
                {"channel": ch, "content": text, "error": str(e)},
            )

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            log.warning("buzz messages send failed: %s", err[:300])
            return self._outbox(
                "message",
                {"channel": ch, "content": text, "error": err[:500], "code": proc.returncode},
            )

        return PublishResult(True, "cli", "posted via buzz-cli", raw=proc.stdout.strip())

    def mem_set(self, slug: str, value: str) -> PublishResult:
        slug = slug.strip().strip("/")
        value = (value or "").strip()
        if not slug or not value:
            return PublishResult(False, "skipped", "slug/value required")

        if not self.available():
            return self._outbox("mem_set", {"slug": slug, "value": value})

        cmd = [self.cli, "mem", "set", slug, value]
        if self.owner:
            cmd.extend(["--owner", self.owner])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=self._env(),
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return self._outbox("mem_set", {"slug": slug, "value": value, "error": str(e)})

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            # mem requires owner auth — fall back to channel note, not silent success
            return self._outbox(
                "mem_set",
                {"slug": slug, "value": value, "error": err[:500], "code": proc.returncode},
            )
        return PublishResult(True, "cli", f"mem set {slug}", raw=proc.stdout.strip())

    def _outbox(self, kind: str, payload: Dict[str, Any]) -> PublishResult:
        record = {
            "ts": time.time(),
            "kind": kind,
            "payload": payload,
        }
        with self.outbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        log.info("Buzz outbox ← %s (%s)", kind, self.outbox)
        return PublishResult(
            ok=False,
            mode="outbox",
            detail=f"queued {kind} to {self.outbox}",
            raw=json.dumps(record),
        )

    def read_outbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.outbox.exists():
            return []
        lines = self.outbox.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
