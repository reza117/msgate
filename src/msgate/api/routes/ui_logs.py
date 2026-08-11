"""Logs UI routes."""

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
from msgate.observability.log_reader import list_log_files, search_logs, today_log_stem
from msgate.ops.alerts_config import load_ops_alerts
from msgate.ops.capacity import evaluate_capacity
from msgate.ui.render import templates

router = APIRouter(tags=["ui-logs"])


def _session_data(request: Request) -> dict:
    data = getattr(request.state, "msgate_session", None)
    if data is None:
        data = load_session(request)
    return data


@router.get("/ui/logs", response_class=HTMLResponse)
def ui_logs(request: Request, state: AppState = Depends(get_state)):
    q = request.query_params.get("q", "")
    level = request.query_params.get("level", "")
    logger = request.query_params.get("logger", "")
    day = request.query_params.get("day", "")
    try:
        limit = int(request.query_params.get("limit", "200"))
    except ValueError:
        limit = 200

    entries = search_logs(query=q, level=level, logger=logger, day=day, limit=limit)
    files = list_log_files()
    cfg = state.runtime.get()
    with state.session_factory() as session:
        pending = state.queue.pending_count(session)
        ops = load_ops_alerts(session)
        capacity = state.capacity_status or evaluate_capacity(
            session,
            pending=pending,
            circuit=state.circuit,
            ops=ops,
        )
    health = check_backend_health(cfg)
    with state.session_factory() as session:
        stats = compute_stats(
            session,
            pending=pending,
            auth_errors=state.events.auth_errors_24h,
            backend_latency_ms=health.latency_ms,
            smtp_port=cfg.smtp.port,
            backend_name=backend_label(cfg),
            backend_connected=health.ok,
        )

    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "version": __version__,
            "page": "Logs",
            "stats": stats,
            "smtp_port": cfg.smtp.port,
            "backend_label": stats.backend_name,
            "backend_ok": stats.backend_connected,
            "ews_ok": stats.backend_connected,
            "help_url": help_url(),
            "must_change_password": bool(_session_data(request).get("must_change_password")),
            "capacity": capacity,
            "q": q,
            "level": level,
            "logger": logger,
            "day": day,
            "limit": limit,
            "entries": entries,
            "log_files": [p.name for p in files[:30]],
            "today": today_log_stem(),
            "error": None,
            "success": None,
        },
    )
