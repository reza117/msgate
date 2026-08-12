"""Shared Jinja context for Web UI templates."""

from __future__ import annotations

from starlette.requests import Request

from msgate.http.root_path import join_root, request_root_path


def template_context(request: Request, **extra: object) -> dict:
    ctx = {
        "root_path": request_root_path(request),
        "rp": lambda path: join_root(request, path),
    }
    ctx.update(extra)
    return ctx
