"""Web UI page routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from msgate import __version__
from msgate.api.deps import get_state
from msgate.api.stats import compute_stats
from msgate.app.state import AppState
from msgate.auth.settings import help_url
from msgate.auth.web_middleware import load_session
from msgate.drivers.registry import backend_label, check_backend_health
from msgate.ui.render import templates

router = APIRouter(tags=["ui"])


def _session_data(request: Request) -> dict:
    data = getattr(request.state, "msgate_session", None)
    if data is None:
        data = load_session(request)
    return data


@router.get("/", response_class=HTMLResponse)
def ui_dashboard(request: Request, state: AppState = Depends(get_state)):
    return _render(request, state, "dashboard.html", "Overview")


@router.get("/ui/messages", response_class=HTMLResponse)
def ui_messages(request: Request, state: AppState = Depends(get_state)):
    return _render(request, state, "messages.html", "Messages")


@router.get("/ui/tools", response_class=HTMLResponse)
def ui_tools(request: Request, state: AppState = Depends(get_state)):
    return _render(request, state, "tools.html", "Tools")


@router.get("/ui/partials/stats", response_class=HTMLResponse)
def partial_stats(request: Request, state: AppState = Depends(get_state)):
    stats = _stats(state)
    return templates.TemplateResponse(
        request,
        "partials/stats_cards.html",
        {"stats": stats},
    )


def _stats(state: AppState):
    cfg = state.runtime.get()
    pending = 0
    with state.session_factory() as session:
        pending = state.queue.pending_count(session)
    health = check_backend_health(cfg)
    with state.session_factory() as session:
        return compute_stats(
            session,
            pending=pending,
            auth_errors=state.events.auth_errors_24h,
            backend_latency_ms=health.latency_ms,
            smtp_port=cfg.smtp.port,
            backend_name=backend_label(cfg),
            backend_connected=health.ok,
        )


def _render(request: Request, state: AppState, template: str, page: str):
    cfg = state.runtime.get()
    stats = _stats(state)
    return templates.TemplateResponse(
        request,
        template,
        {
            "version": __version__,
            "page": page,
            "stats": stats,
            "smtp_port": cfg.smtp.port,
            "backend_label": stats.backend_name,
            "backend_ok": stats.backend_connected,
            "ews_ok": stats.backend_connected,
            "help_url": help_url(),
            "must_change_password": bool(_session_data(request).get("must_change_password")),
        },
    )
