"""Tests for reverse-proxy subpath URL helpers."""

from __future__ import annotations

import os
from unittest.mock import Mock

from msgate.http.root_path import (
    configured_root_path,
    cookie_path,
    join_root,
    request_root_path,
)


def test_join_root_empty() -> None:
    req = Mock(headers={})
    assert join_root(req, "/api/v1/config") == "/api/v1/config"


def test_join_root_from_env(monkeypatch) -> None:
    monkeypatch.setenv("MSGATE_ROOT_PATH", "/msgate")
    req = Mock(headers={})
    assert join_root(req, "/ui/settings") == "/msgate/ui/settings"
    assert join_root(req, "/") == "/msgate/"
    assert cookie_path(req) == "/msgate"


def test_join_root_from_forwarded_prefix(monkeypatch) -> None:
    monkeypatch.delenv("MSGATE_ROOT_PATH", raising=False)
    req = Mock(headers={"x-forwarded-prefix": "/msgate"})
    assert request_root_path(req) == "/msgate"
    assert join_root(req, "/api/v1/config") == "/msgate/api/v1/config"


def test_configured_root_path_normalizes(monkeypatch) -> None:
    monkeypatch.setenv("MSGATE_ROOT_PATH", "msgate/")
    assert configured_root_path() == "/msgate"
