#!/usr/bin/env python3
"""ZeroClaw ACP client: JSON-RPC 2.0 over stdio (primary) or WebSocket (fallback).

Protocol matches ZeroClaw `zeroclaw acp` / Agent Client Protocol:
  initialize → session/new → session/prompt (+ session/update stream)
  client must answer session/request_permission
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

log = logging.getLogger("buzzclaw.acp")

PermissionPolicy = str  # allow-once | allow-always | reject-once | manual


@dataclass
class PromptResult:
    session_id: str
    stop_reason: str
    content: str
    updates: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


class AcpError(RuntimeError):
    def __init__(self, message: str, code: Optional[int] = None, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class ZeroClawAcpClient:
    """Drive a ZeroClaw ACP agent process over NDJSON stdio."""

    def __init__(
        self,
        command: Optional[str] = None,
        *,
        permission_policy: Optional[PermissionPolicy] = None,
        request_timeout: float = 120.0,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        cmd = command or os.getenv("ZEROCLAW_ACP_CMD", "zeroclaw acp")
        self._cmd_parts = shlex.split(cmd, posix=os.name != "nt")
        self.permission_policy = (
            permission_policy
            or os.getenv("ACP_AUTO_PERMISSION", "allow-once")
        ).strip()
        self.request_timeout = float(
            os.getenv("ZEROCLAW_ACP_TIMEOUT", str(request_timeout))
        )
        self.cwd = cwd
        self.env = {**os.environ, **(env or {})}
        self.on_update = on_update

        self._proc: Optional[subprocess.Popen] = None
        self._reader: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._id = 0
        self._pending: Dict[Union[int, str], threading.Event] = {}
        self._results: Dict[Union[int, str], Dict[str, Any]] = {}
        self._errors: Dict[Union[int, str], AcpError] = {}
        self._updates: List[Dict[str, Any]] = []
        self._alive = False
        self._session_id: Optional[str] = None
        self._stdout_buffer = ""

    # ── lifecycle ──────────────────────────────────────────────────

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        log.info("Starting ACP agent: %s", " ".join(self._cmd_parts))
        self._proc = subprocess.Popen(
            self._cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.cwd,
            env=self.env,
        )
        self._alive = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        # drain stderr in background so pipe never fills
        threading.Thread(target=self._stderr_loop, daemon=True).start()

    def close(self) -> None:
        self._alive = False
        if self._session_id:
            try:
                self.session_stop(self._session_id)
            except Exception as e:
                log.debug("session_stop on close: %s", e)
        if self._proc and self._proc.poll() is None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None

    def __enter__(self) -> "ZeroClawAcpClient":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ── protocol ───────────────────────────────────────────────────

    def initialize(self, protocol_version: int = 1) -> Dict[str, Any]:
        return self._request(
            "initialize",
            {"protocolVersion": protocol_version, "clientInfo": {"name": "buzzclawagi-bridge", "version": "0.3.0"}},
        )

    def session_new(
        self,
        agent_alias: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> str:
        params: Dict[str, Any] = {}
        alias = agent_alias or os.getenv("ZEROCLAW_AGENT_ALIAS")
        if alias:
            params["agentAlias"] = alias
        workspace = cwd or os.getenv("ZEROCLAW_ACP_CWD")
        if workspace:
            params["cwd"] = workspace
        result = self._request("session/new", params)
        sid = result.get("sessionId") or result.get("session_id")
        if not sid:
            raise AcpError(f"session/new missing sessionId: {result}")
        self._session_id = str(sid)
        return self._session_id

    def session_prompt(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        session_id: Optional[str] = None,
        *,
        collect_updates: bool = True,
    ) -> PromptResult:
        sid = session_id or self._session_id
        if not sid:
            raise AcpError("no session; call session_new first")
        before = len(self._updates) if collect_updates else 0
        result = self._request(
            "session/prompt",
            {"sessionId": sid, "prompt": prompt},
            timeout=self.request_timeout,
        )
        updates = self._updates[before:] if collect_updates else []
        content = result.get("content") or ""
        if not content:
            # assemble text from agent_message_chunk updates
            chunks = []
            for u in updates:
                upd = u.get("params", {}).get("update") or u.get("update") or {}
                if upd.get("sessionUpdate") == "agent_message_chunk":
                    c = upd.get("content") or {}
                    if isinstance(c, dict) and c.get("text"):
                        chunks.append(c["text"])
                    elif isinstance(c, str):
                        chunks.append(c)
            content = "".join(chunks)
        return PromptResult(
            session_id=str(result.get("sessionId") or sid),
            stop_reason=str(result.get("stopReason") or result.get("stop_reason") or "end_turn"),
            content=content if isinstance(content, str) else json.dumps(content),
            updates=updates,
            raw=result,
        )

    def session_cancel(self, session_id: Optional[str] = None) -> None:
        sid = session_id or self._session_id
        if not sid:
            return
        # notification-style cancel is allowed; still send as request if server expects reply
        try:
            self._request("session/cancel", {"sessionId": sid}, timeout=10.0)
        except AcpError:
            self._notify("session/cancel", {"sessionId": sid})

    def session_stop(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or self._session_id
        if not sid:
            return {}
        return self._request("session/stop", {"sessionId": sid}, timeout=15.0)

    def ensure_session(self, agent_alias: Optional[str] = None, cwd: Optional[str] = None) -> str:
        """Start process, initialize, open session if needed."""
        self.start()
        if not self._session_id:
            self.initialize()
            self.session_new(agent_alias=agent_alias, cwd=cwd)
        return self._session_id  # type: ignore[return-value]

    def prompt(self, text: str, **kwargs) -> PromptResult:
        """Convenience: ensure session then prompt."""
        self.ensure_session(
            agent_alias=kwargs.pop("agent_alias", None),
            cwd=kwargs.pop("cwd", None),
        )
        return self.session_prompt(text, **kwargs)

    # ── transport ──────────────────────────────────────────────────

    def _next_id(self) -> int:
        with self._lock:
            self._id += 1
            return self._id

    def _write(self, obj: Dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise AcpError("ACP process not started")
        line = json.dumps(obj, separators=(",", ":")) + "\n"
        with self._lock:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
        log.debug("→ %s", line.strip()[:500])

    def _notify(self, method: str, params: Dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self._proc or self._proc.poll() is not None:
            self.start()
        req_id = self._next_id()
        event = threading.Event()
        with self._lock:
            self._pending[req_id] = event
        self._write(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {},
            }
        )
        wait = timeout if timeout is not None else self.request_timeout
        if not event.wait(wait):
            with self._lock:
                self._pending.pop(req_id, None)
            raise AcpError(f"timeout waiting for {method} (id={req_id})")
        with self._lock:
            if req_id in self._errors:
                err = self._errors.pop(req_id)
                self._results.pop(req_id, None)
                raise err
            result = self._results.pop(req_id, {})
        return result

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        try:
            for line in self._proc.stdout:
                if not self._alive:
                    break
                line = line.strip()
                if not line:
                    continue
                log.debug("← %s", line[:500])
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError as e:
                    log.warning("bad NDJSON from agent: %s (%s)", e, line[:200])
                    continue
                self._dispatch(msg)
        except Exception as e:
            log.error("ACP read loop ended: %s", e)
        finally:
            # unblock waiters
            with self._lock:
                for rid, ev in list(self._pending.items()):
                    self._errors[rid] = AcpError("ACP process closed")
                    ev.set()
                self._pending.clear()

    def _stderr_loop(self) -> None:
        if not self._proc or not self._proc.stderr:
            return
        try:
            for line in self._proc.stderr:
                log.debug("[acp-stderr] %s", line.rstrip())
        except Exception:
            pass

    def _dispatch(self, msg: Dict[str, Any]) -> None:
        # Response to our request
        if "id" in msg and ("result" in msg or "error" in msg):
            rid = msg["id"]
            with self._lock:
                if "error" in msg and msg["error"] is not None:
                    err = msg["error"]
                    self._errors[rid] = AcpError(
                        err.get("message", str(err)),
                        code=err.get("code"),
                        data=err.get("data"),
                    )
                else:
                    self._results[rid] = msg.get("result") or {}
                ev = self._pending.pop(rid, None)
            if ev:
                ev.set()
            return

        method = msg.get("method")
        if not method:
            return

        # Server → client request (permissions)
        if "id" in msg and method == "session/request_permission":
            self._handle_permission(msg)
            return

        # Notifications
        if method == "session/update":
            self._updates.append(msg)
            if self.on_update:
                try:
                    self.on_update(msg)
                except Exception as e:
                    log.debug("on_update error: %s", e)
            return

        log.debug("unhandled ACP message method=%s", method)

    def _handle_permission(self, msg: Dict[str, Any]) -> None:
        req_id = msg["id"]
        params = msg.get("params") or {}
        options = params.get("options") or []
        policy = self.permission_policy
        option_id = None

        if policy == "manual":
            log.warning("permission requested (manual mode) — auto-rejecting: %s", params)
            option_id = "reject-once"
        elif policy in ("allow-once", "allow_once"):
            option_id = "allow-once"
        elif policy in ("allow-always", "allow_always"):
            option_id = "allow-always"
        elif policy in ("reject-once", "reject_once"):
            option_id = "reject-once"
        else:
            option_id = "allow-once"

        # Prefer an option that exists on the wire
        ids = {o.get("optionId") for o in options if isinstance(o, dict)}
        if option_id not in ids and ids:
            # map common kinds
            for o in options:
                kind = (o.get("kind") or "").lower()
                if policy.startswith("allow") and "allow" in kind:
                    option_id = o.get("optionId")
                    break
                if policy.startswith("reject") and "reject" in kind:
                    option_id = o.get("optionId")
                    break
            else:
                option_id = next(iter(ids))

        log.info(
            "ACP permission auto-response policy=%s optionId=%s tool=%s",
            policy,
            option_id,
            (params.get("toolCall") or {}).get("title"),
        )
        if policy.startswith("reject") or policy == "manual":
            result = {"outcome": {"outcome": "selected", "optionId": option_id}}
        else:
            result = {"outcome": {"outcome": "selected", "optionId": option_id}}
        self._write({"jsonrpc": "2.0", "id": req_id, "result": result})


class HttpAcpFallback:
    """Best-effort HTTP fallback when ZEROCLAW_ACP_URL is http(s).

    ZeroClaw does not ship a tools/call HTTP API by default; this is only for
    custom gateways. Prefer stdio or WebSocket.
    """

    def __init__(self, url: str, timeout: float = 30.0):
        import requests

        self.url = url.rstrip("/")
        self.timeout = timeout
        self._requests = requests

    def prompt(self, text: str) -> PromptResult:
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "session/prompt",
            "params": {"prompt": text},
        }
        r = self._requests.post(self.url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        result = data.get("result") or data
        return PromptResult(
            session_id=str(result.get("sessionId") or "http"),
            stop_reason=str(result.get("stopReason") or "end_turn"),
            content=str(result.get("content") or json.dumps(result)),
            raw=result if isinstance(result, dict) else {"result": result},
        )


def open_acp_client(
    *,
    command: Optional[str] = None,
    url: Optional[str] = None,
    dry_run: bool = False,
) -> Any:
    """Factory: stdio client, HTTP fallback, or dry-run stub."""
    if dry_run:
        return DryRunAcpClient()
    url = url or os.getenv("ZEROCLAW_ACP_URL")
    if url and url.startswith(("http://", "https://")):
        log.warning("Using HTTP ACP fallback at %s — prefer stdio `zeroclaw acp`", url)
        return HttpAcpFallback(url)
    if url and url.startswith(("ws://", "wss://")):
        log.warning(
            "WebSocket ACP URL set (%s) but WS client not implemented in bridge v3; "
            "use stdio or zeroclaw-acp-bridge. Falling back to stdio.",
            url,
        )
    return ZeroClawAcpClient(command=command)


class DryRunAcpClient:
    """No-op client for bridge dry runs and unit tests of the loop."""

    def __init__(self) -> None:
        self.prompts: List[str] = []

    def ensure_session(self, **kwargs) -> str:
        return "dry-run-session"

    def prompt(self, text: str, **kwargs) -> PromptResult:
        self.prompts.append(text)
        return PromptResult(
            session_id="dry-run-session",
            stop_reason="end_turn",
            content=f"[dry-run] would execute prompt ({len(text)} chars)",
            raw={"dry_run": True},
        )

    def close(self) -> None:
        pass

    def __enter__(self) -> "DryRunAcpClient":
        return self

    def __exit__(self, *args) -> None:
        pass
