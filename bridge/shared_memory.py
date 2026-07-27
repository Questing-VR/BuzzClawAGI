#!/usr/bin/env python3
"""Dual-write important facts to OpenAGI memory, ZeroClaw, and Buzz."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol

log = logging.getLogger("buzzclaw.memory")


class SupportsRemember(Protocol):
    def memory_remember(self, content: str, **kwargs: Any) -> Any: ...


class SupportsPrompt(Protocol):
    def prompt(self, text: str, **kwargs: Any) -> Any: ...


class SupportsBuzz(Protocol):
    def post_message(self, content: str, **kwargs: Any) -> Any: ...

    def mem_set(self, slug: str, value: str) -> Any: ...


@dataclass
class MemoryWriteResult:
    slug: str
    openagi_ok: bool = False
    zeroclaw_ok: bool = False
    buzz_mem_ok: bool = False
    buzz_note_ok: bool = False
    details: List[str] = field(default_factory=list)


def fact_slug(content: str, prefix: str = "buzzclaw") -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", content.strip().lower())[:48].strip("-")
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    base = clean or "fact"
    return f"{prefix}/{base}-{h}"


class SharedMemory:
    def __init__(
        self,
        openagi: Optional[SupportsRemember] = None,
        zeroclaw: Optional[SupportsPrompt] = None,
        buzz: Optional[SupportsBuzz] = None,
        *,
        dry_run: bool = False,
    ):
        self.openagi = openagi
        self.zeroclaw = zeroclaw
        self.buzz = buzz
        self.dry_run = dry_run

    def write_fact(
        self,
        content: str,
        *,
        tags: Optional[List[str]] = None,
        importance: str = "high",
        also_prompt_zeroclaw: bool = True,
        post_channel_note: bool = True,
    ) -> MemoryWriteResult:
        content = (content or "").strip()
        slug = fact_slug(content)
        result = MemoryWriteResult(slug=slug)

        if not content:
            result.details.append("empty content")
            return result

        if self.dry_run:
            result.details.append(f"dry-run would dual-write slug={slug}")
            result.openagi_ok = result.zeroclaw_ok = result.buzz_note_ok = True
            return result

        # 1) OpenAGI
        if self.openagi:
            try:
                resp = self.openagi.memory_remember(
                    content,
                    tags=tags or ["buzzclaw", "shared"],
                    importance=importance,
                    source="buzzclaw-bridge",
                )
                result.openagi_ok = resp is not None
                result.details.append(f"openagi={'ok' if result.openagi_ok else 'fail'}")
            except Exception as e:
                result.details.append(f"openagi error: {e}")
        else:
            result.details.append("openagi skipped")

        # 2) ZeroClaw long-term memory via prompt
        if also_prompt_zeroclaw and self.zeroclaw:
            try:
                pr = self.zeroclaw.prompt(
                    "Store this durable fact in long-term memory and confirm briefly:\n"
                    f"{content}"
                )
                result.zeroclaw_ok = True
                result.details.append(
                    f"zeroclaw stop={getattr(pr, 'stop_reason', '?')}"
                )
            except Exception as e:
                result.details.append(f"zeroclaw error: {e}")
        else:
            result.details.append("zeroclaw skipped")

        # 3) Buzz mem engram + human-visible channel note
        if self.buzz:
            try:
                mem = self.buzz.mem_set(slug, content)
                result.buzz_mem_ok = bool(getattr(mem, "ok", False))
                result.details.append(f"buzz_mem mode={getattr(mem, 'mode', '?')}")
            except Exception as e:
                result.details.append(f"buzz_mem error: {e}")

            if post_channel_note:
                try:
                    note = self.buzz.post_message(f"Shared memory `{slug}`: {content[:500]}")
                    result.buzz_note_ok = bool(
                        getattr(note, "ok", False) or getattr(note, "mode", "") == "outbox"
                    )
                    # outbox counts as durable handoff
                    if getattr(note, "mode", "") == "outbox":
                        result.buzz_note_ok = True
                    result.details.append(f"buzz_note mode={getattr(note, 'mode', '?')}")
                except Exception as e:
                    result.details.append(f"buzz_note error: {e}")
        else:
            result.details.append("buzz skipped")

        log.info("shared memory %s: %s", slug, "; ".join(result.details))
        return result
