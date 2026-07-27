#!/usr/bin/env python3
"""
BuzzClawAGI Bridge v3
OpenAGI (proactive brain) → ZeroClaw ACP (hardened body) → Buzz (shared room)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Set

from buzz_publisher import BuzzPublisher
from openagi_client import OpenAgiClient
from shared_memory import SharedMemory
from signal_map import extract_remember_lines, normalize
from zeroclaw_acp_client import open_acp_client

# ── config ─────────────────────────────────────────────────────────

OPENAGI_URL = os.getenv("OPENAGI_URL", "http://127.0.0.1:43210")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "8"))
DRY_RUN = os.getenv("DRY_RUN", "0") in ("1", "true", "yes")
INCLUDE_OBS = os.getenv("INCLUDE_OBSERVATIONS", "0") in ("1", "true", "yes")
STATE_DIR = Path(os.getenv("BRIDGE_STATE_DIR", ".bridge-state"))
MAX_SEEN = int(os.getenv("BRIDGE_MAX_SEEN", "5000"))
ONCE = os.getenv("BRIDGE_ONCE", "0") in ("1", "true", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("buzzclaw.bridge")


class SeenStore:
    """Bounded dedup set persisted as JSON lines of ids."""

    def __init__(self, path: Path, max_size: int = 5000):
        self.path = path
        self.max_size = max_size
        self.ids: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    self.ids.add(line)
        except OSError as e:
            log.warning("could not load seen store: %s", e)

    def contains(self, sid: str) -> bool:
        return sid in self.ids

    def add(self, sid: str) -> None:
        self.ids.add(sid)
        if len(self.ids) > self.max_size:
            # drop arbitrary older half by rewriting
            keep = list(self.ids)[len(self.ids) // 2 :]
            self.ids = set(keep)
            self.path.write_text("\n".join(sorted(self.ids)) + "\n", encoding="utf-8")
            return
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(sid + "\n")
        except OSError as e:
            log.warning("seen store append failed: %s", e)


def process_signal(
    raw: Dict[str, Any],
    *,
    acp: Any,
    buzz: BuzzPublisher,
    memory: SharedMemory,
    seen: SeenStore,
) -> None:
    sig = normalize(raw)
    if seen.contains(sig.id):
        return
    seen.add(sig.id)

    log.info("signal type=%s id=%s title=%s", sig.type, sig.id[:48], sig.title[:80])
    prompt = sig.to_prompt()

    if DRY_RUN:
        log.info("[dry-run] prompt (%d chars):\n%s", len(prompt), prompt[:500])
        buzz.post_message(f"[dry-run] OpenAGI signal `{sig.title}` ({sig.type})")
        if sig.remember:
            memory.write_fact(f"{sig.title}: {sig.body[:300]}", importance=sig.importance)
        return

    try:
        result = acp.prompt(prompt)
    except Exception as e:
        log.error("ZeroClaw ACP prompt failed: %s", e)
        buzz.post_message(f"Bridge error on signal `{sig.title}`: {e}")
        return

    summary = (result.content or "").strip()
    log.info(
        "ZeroClaw done stop=%s content_len=%d",
        result.stop_reason,
        len(summary),
    )
    post = (
        f"**OpenAGI → ZeroClaw** `{sig.type}`: {sig.title}\n"
        f"{summary[:1500] if summary else '(no content returned)'}"
    )
    pr = buzz.post_message(post)
    log.info("Buzz post: %s %s", pr.mode, pr.detail)

    facts = extract_remember_lines(summary)
    if sig.remember and not facts:
        facts = [f"{sig.title}: {sig.body[:400]}"]
    for fact in facts:
        mr = memory.write_fact(fact, importance=sig.importance)
        log.info("memory write: %s", "; ".join(mr.details))


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("BuzzClawAGI bridge v3 starting")
    log.info("OpenAGI  → %s", OPENAGI_URL)
    log.info("DRY_RUN  → %s", DRY_RUN)
    log.info("state    → %s", STATE_DIR.resolve())

    openagi = OpenAgiClient(OPENAGI_URL)
    buzz = BuzzPublisher(state_dir=str(STATE_DIR))
    seen = SeenStore(STATE_DIR / "seen_ids.txt", max_size=MAX_SEEN)

    healthy = openagi.health()
    if not healthy:
        log.warning(
            "OpenAGI /health failed at %s — will retry quietly until it is up "
            "(start with scripts/start.ps1 so the daemon launches correctly on Windows)",
            OPENAGI_URL,
        )

    acp = open_acp_client(dry_run=DRY_RUN)
    memory = SharedMemory(openagi=openagi, zeroclaw=None if DRY_RUN else acp, buzz=buzz, dry_run=DRY_RUN)
    down_streak = 0

    try:
        while True:
            try:
                if not openagi.health():
                    down_streak += 1
                    # Log once, then every ~10 failed cycles — avoid spam
                    if down_streak == 1 or down_streak % 10 == 0:
                        log.warning(
                            "OpenAGI still unreachable at %s (attempt %d)",
                            OPENAGI_URL,
                            down_streak,
                        )
                    if ONCE:
                        log.error("BRIDGE_ONCE set and OpenAGI is down — exit 1")
                        return 1
                    time.sleep(POLL_INTERVAL)
                    continue
                if down_streak:
                    log.info("OpenAGI is reachable again after %d failed polls", down_streak)
                    down_streak = 0

                signals = openagi.collect_signals(include_observations=INCLUDE_OBS)
                log.debug("polled %d raw items", len(signals))
                for raw in signals:
                    process_signal(raw, acp=acp, buzz=buzz, memory=memory, seen=seen)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log.exception("poll cycle error: %s", e)

            if ONCE:
                log.info("BRIDGE_ONCE set — exiting after one cycle")
                break
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log.info("interrupted")
    finally:
        try:
            acp.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
