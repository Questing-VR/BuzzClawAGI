#!/usr/bin/env python3
"""Normalize OpenAGI payloads into actionable signals and ZeroClaw prompts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Signal:
    id: str
    type: str  # skill | action | suggestion | observation | unknown
    title: str
    body: str
    importance: str = "normal"  # low | normal | high
    remember: bool = False
    source: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        return build_prompt(self)


def stable_id(payload: Dict[str, Any], source: str = "") -> str:
    for key in ("id", "uuid", "slug", "name", "skill", "actionId", "suggestionId"):
        val = payload.get(key)
        if val:
            return f"{source}:{val}" if source else str(val)
    blob = json.dumps(payload, sort_keys=True, default=str)[:2000]
    h = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{h}" if source else h


def normalize(payload: Dict[str, Any]) -> Signal:
    source = str(payload.get("_source") or payload.get("source") or "")
    text_blob = json.dumps(payload, default=str).lower()

    # type inference
    sig_type = "unknown"
    if source == "skill_suggested" or "skill" in str(payload.get("type", "")).lower():
        sig_type = "skill"
    elif source == "pending_action" or "action" in str(payload.get("type", "")).lower():
        sig_type = "action"
    elif source == "proactive_suggestion" or "suggest" in text_blob:
        sig_type = "suggestion"
    elif source == "observation" or "observ" in text_blob:
        sig_type = "observation"
    elif "skill" in text_blob and "suggest" in text_blob:
        sig_type = "skill"

    title = _first_str(
        payload,
        ("title", "name", "skill", "summary", "headline", "label"),
    ) or sig_type

    body = _first_str(
        payload,
        ("body", "description", "content", "text", "detail", "prompt", "reason"),
    )
    if not body:
        # compact remaining fields
        skip = {"_source", "id", "uuid", "title", "name"}
        body = json.dumps(
            {k: v for k, v in payload.items() if k not in skip},
            default=str,
            indent=2,
        )[:2000]

    importance = str(payload.get("importance") or payload.get("priority") or "normal").lower()
    if importance in ("critical", "urgent"):
        importance = "high"
    if importance not in ("low", "normal", "high"):
        severity = payload.get("severity") or payload.get("score")
        try:
            importance = "high" if float(severity) >= 0.7 else "normal"
        except (TypeError, ValueError):
            importance = "normal"

    remember = bool(
        payload.get("remember")
        or payload.get("share_memory")
        or importance == "high"
        or "remember" in text_blob
    )

    return Signal(
        id=stable_id(payload, source),
        type=sig_type,
        title=str(title)[:200],
        body=str(body)[:4000],
        importance=importance,
        remember=remember,
        source=source,
        raw=payload,
    )


def build_prompt(sig: Signal) -> str:
    header = (
        "You are ZeroClaw, the sandboxed execution body for BuzzClawAGI.\n"
        "OpenAGI (proactive brain) handed you a signal. Act carefully inside the sandbox.\n"
        "Summarize what you did and any durable facts worth remembering.\n\n"
    )
    if sig.type == "skill":
        task = (
            f"OpenAGI suggested skill `{sig.title}`.\n"
            f"Details:\n{sig.body}\n\n"
            "Evaluate whether to implement or dry-run this skill. "
            "Prefer safe read-only checks first. Report outcome."
        )
    elif sig.type == "action":
        task = (
            f"OpenAGI pending action: {sig.title}\n"
            f"Details:\n{sig.body}\n\n"
            "Execute only if clearly safe under your risk profile; otherwise explain blockers."
        )
    elif sig.type == "suggestion":
        task = (
            f"Proactive suggestion: {sig.title}\n"
            f"Details:\n{sig.body}\n\n"
            "Decide if action is warranted. If yes, take the smallest useful step and report."
        )
    elif sig.type == "observation":
        task = (
            f"Observation signal: {sig.title}\n"
            f"Details:\n{sig.body}\n\n"
            "Interpret briefly. Only act if there is a clear, low-risk next step."
        )
    else:
        task = f"Signal ({sig.type}): {sig.title}\n{sig.body}\n\nRespond with a concise plan or action."

    if sig.remember:
        task += (
            "\n\nIf you learn an important durable fact, state it clearly in a line "
            "starting with REMEMBER: so the bridge can dual-write shared memory."
        )
    return header + task


def extract_remember_lines(text: str) -> List[str]:
    lines = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s.upper().startswith("REMEMBER:"):
            fact = s.split(":", 1)[1].strip()
            if fact:
                lines.append(fact)
    return lines


def _first_str(payload: Dict[str, Any], keys: tuple) -> Optional[str]:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)):
            return str(v)
    return None
