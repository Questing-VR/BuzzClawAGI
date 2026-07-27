#!/usr/bin/env python3
"""Tests for ZeroClaw ACP client against mock_acp_agent.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zeroclaw_acp_client import ZeroClawAcpClient  # noqa: E402


@pytest.fixture
def mock_cmd() -> str:
    agent = Path(__file__).resolve().parent / "mock_acp_agent.py"
    return f"{sys.executable} {agent}"


def test_initialize_session_prompt(mock_cmd: str) -> None:
    with ZeroClawAcpClient(command=mock_cmd, request_timeout=10) as client:
        init = client.initialize()
        assert init.get("protocolVersion") == 1
        assert init.get("agentInfo", {}).get("name") == "mock-acp"

        sid = client.session_new()
        assert sid == "s-test-001"

        result = client.session_prompt("hello from test")
        assert result.stop_reason == "end_turn"
        assert "hello from test" in result.content
        assert result.session_id == sid


def test_prompt_convenience(mock_cmd: str) -> None:
    client = ZeroClawAcpClient(command=mock_cmd, request_timeout=10)
    try:
        result = client.prompt("shortcut")
        assert "shortcut" in result.content
    finally:
        client.close()


def test_permission_auto_allow(mock_cmd: str) -> None:
    client = ZeroClawAcpClient(
        command=mock_cmd,
        permission_policy="allow-once",
        request_timeout=10,
    )
    try:
        result = client.prompt("do something NEED_PERM please")
        assert result.stop_reason == "end_turn"
        assert "NEED_PERM" in result.content
    finally:
        client.close()
