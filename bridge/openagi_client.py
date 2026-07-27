#!/usr/bin/env python3
"""HTTP client for OpenAGI daemon endpoints (port 43210 by default)."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

log = logging.getLogger("buzzclaw.openagi")


class OpenAgiClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 8.0,
    ):
        self.base_url = (base_url or os.getenv("OPENAGI_URL", "http://127.0.0.1:43210")).rstrip(
            "/"
        )
        self.token = token if token is not None else os.getenv("OPENAGI_AUTH_TOKEN", "")
        self.timeout = timeout
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = self.session.get(url, params=params, timeout=self.timeout)
            if r.status_code == 401:
                log.error("OpenAGI auth failed (401) — set OPENAGI_AUTH_TOKEN")
                return None
            if r.status_code >= 400:
                log.warning("OpenAGI GET %s → %s %s", path, r.status_code, r.text[:200])
                return None
            return r.json()
        except requests.RequestException as e:
            log.warning("OpenAGI GET %s error: %s", path, e)
            return None

    def _post(self, path: str, body: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            r = self.session.post(url, json=body, timeout=self.timeout)
            if r.status_code >= 400:
                log.warning("OpenAGI POST %s → %s %s", path, r.status_code, r.text[:200])
                return None
            return r.json() if r.content else {}
        except requests.RequestException as e:
            log.warning("OpenAGI POST %s error: %s", path, e)
            return None

    def health(self) -> bool:
        data = self._get("/health")
        return data is not None

    def proactive_suggestions(self, status: str = "pending") -> List[Dict[str, Any]]:
        data = self._get("/proactive/suggestions", {"status": status})
        return _as_list(data)

    def pending_actions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"status": status} if status else None
        data = self._get("/pending-actions", params)
        if isinstance(data, dict) and "actions" in data:
            return _as_list(data["actions"])
        return _as_list(data)

    def skills_suggested(self) -> List[Dict[str, Any]]:
        data = self._get("/skills/suggested")
        return _as_list(data)

    def skills(self) -> List[Dict[str, Any]]:
        data = self._get("/skills")
        return _as_list(data)

    def observations_search(self, q: str = "act") -> List[Dict[str, Any]]:
        data = self._get("/observations/search", {"q": q})
        return _as_list(data)

    def observations_recent(self) -> Any:
        return self._get("/observations/recent-context")

    def memory_snapshot(self) -> Any:
        return self._get("/memory")

    def memory_remember(
        self,
        content: str,
        *,
        tags: Optional[List[str]] = None,
        importance: str = "normal",
        source: str = "buzzclaw-bridge",
        scope: str = "main",
    ) -> Any:
        return self._post(
            "/memory/remember",
            {
                "content": content,
                "tags": tags or ["buzzclaw", "shared"],
                "importance": importance,
                "source": source,
                "scope": scope,
            },
        )

    def collect_signals(self, *, include_observations: bool = False) -> List[Dict[str, Any]]:
        """Pull primary proactive surfaces and tag source endpoint."""
        out: List[Dict[str, Any]] = []
        for item in self.proactive_suggestions():
            out.append(_tag(item, "proactive_suggestion"))
        for item in self.pending_actions():
            out.append(_tag(item, "pending_action"))
        for item in self.skills_suggested():
            out.append(_tag(item, "skill_suggested"))
        if include_observations or not out:
            for item in self.observations_search("act"):
                out.append(_tag(item, "observation"))
        return out


def _as_list(data: Any) -> List[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [x if isinstance(x, dict) else {"value": x} for x in data]
    if isinstance(data, dict):
        # common envelopes
        for key in ("items", "suggestions", "actions", "skills", "results", "data"):
            if key in data and isinstance(data[key], list):
                return [x if isinstance(x, dict) else {"value": x} for x in data[key]]
        return [data]
    return [{"value": data}]


def _tag(item: Dict[str, Any], source: str) -> Dict[str, Any]:
    merged = dict(item)
    merged.setdefault("_source", source)
    return merged
