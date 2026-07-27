#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signal_map import build_prompt, extract_remember_lines, normalize, stable_id


def test_normalize_skill() -> None:
    sig = normalize(
        {
            "_source": "skill_suggested",
            "name": "morning-brief",
            "description": "Summarize calendar",
        }
    )
    assert sig.type == "skill"
    assert "morning-brief" in sig.title
    assert "morning-brief" in sig.id


def test_normalize_pending_action() -> None:
    sig = normalize(
        {
            "_source": "pending_action",
            "id": "act-1",
            "title": "Restart service",
            "body": "nginx config changed",
            "importance": "high",
        }
    )
    assert sig.type == "action"
    assert sig.remember is True
    prompt = build_prompt(sig)
    assert "pending action" in prompt.lower() or "Restart service" in prompt


def test_stable_id_hash_fallback() -> None:
    a = stable_id({"foo": 1})
    b = stable_id({"foo": 1})
    c = stable_id({"foo": 2})
    assert a == b
    assert a != c


def test_extract_remember() -> None:
    text = "Did stuff\nREMEMBER: User prefers dark mode\nDone"
    facts = extract_remember_lines(text)
    assert facts == ["User prefers dark mode"]
