#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from buzz_publisher import BuzzPublisher, PublishResult
from shared_memory import SharedMemory, fact_slug


class FakeOpenAgi:
    def __init__(self) -> None:
        self.calls = []

    def memory_remember(self, content: str, **kwargs):
        self.calls.append((content, kwargs))
        return {"ok": True}


class FakeAcp:
    def __init__(self) -> None:
        self.prompts = []

    def prompt(self, text: str, **kwargs):
        self.prompts.append(text)

        class R:
            stop_reason = "end_turn"
            content = "stored"

        return R()


class FakeBuzz:
    def __init__(self) -> None:
        self.posts = []
        self.mems = []

    def post_message(self, content: str, **kwargs):
        self.posts.append(content)
        return PublishResult(True, "cli", "ok")

    def mem_set(self, slug: str, value: str):
        self.mems.append((slug, value))
        return PublishResult(True, "cli", "ok")


def test_fact_slug_stable() -> None:
    assert fact_slug("Hello World") == fact_slug("Hello World")
    assert fact_slug("a") != fact_slug("b")


def test_dual_write() -> None:
    oa = FakeOpenAgi()
    acp = FakeAcp()
    buzz = FakeBuzz()
    sm = SharedMemory(openagi=oa, zeroclaw=acp, buzz=buzz)
    r = sm.write_fact("User timezone is America/Denver")
    assert r.openagi_ok and r.zeroclaw_ok and r.buzz_mem_ok and r.buzz_note_ok
    assert oa.calls
    assert acp.prompts
    assert buzz.mems
    assert buzz.posts


def test_outbox_when_no_cli(tmp_path: Path) -> None:
    pub = BuzzPublisher(
        channel_id="00000000-0000-0000-0000-000000000001",
        cli="buzz-cli-does-not-exist-xyz",
        state_dir=str(tmp_path),
        private_key="test",
    )
    r = pub.post_message("hello room")
    assert r.mode == "outbox"
    assert (tmp_path / "buzz_outbox.jsonl").exists()
    items = pub.read_outbox()
    assert items and items[0]["kind"] == "message"
