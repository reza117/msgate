"""Browser-facing URL prefix when msgate sits behind a reverse-proxy subpath."""

from __future__ import annotations

import os

from starlette.requests import Request

_ENV_KEY = "MSGATE_ROOT_PATH"
_PREFIX_HEADER = "x-forwarded-prefix"


def _normalize(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p or p == "/":
        return ""
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/")


def configured_root_path() -> str:
    return _normalize(os.environ.get(_ENV_KEY, ""))


def request_root_path(request: Request | None) -> str:
    if request is not None:
        hdr = request.headers.get(_PREFIX_HEADER, "")
        if hdr:
            return _normalize(hdr)
    return configured_root_path()


def join_root(request: Request | None, path: str) -> str:
    """Build a path for redirects, links, fetch, and WebSocket URLs."""
    root = request_root_path(request)
    if not path:
        return root or "/"
    if not path.startswith("/"):
        path = "/" + path
    if not root:
        return path
    return root + path


def cookie_path(request: Request | None) -> str:
    root = request_root_path(request)
    return root if root else "/"
