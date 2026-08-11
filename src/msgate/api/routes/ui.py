"""Web UI page routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from msgate import __version__
from msgate.api.deps import get_state
from msgate.api.stats import compute_stats
from msgate.app.state import AppState
from msgate.auth.settings import help_url
from msgate.auth.web_middleware import load_session
from msgate.config.store import redact_config
from msgate.drivers.registry import backend_label, check_backend_health
from msgate.ops.alerts_config import load_ops_alerts, save_ops_alerts
from msgate.ops.capacity import evaluate_capacity
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


@router.get("/ui/settings", response_class=HTMLResponse)
def ui_settings(request: Request, state: AppState = Depends(get_state)):
    return _render(request, state, "settings.html", "Settings")


@router.get("/ui/account", response_class=HTMLResponse)
def ui_account(request: Request, state: AppState = Depends(get_state)):
    return _render(request, state, "account.html", "Account")


@router.post("/ui/account/alerts")
def ui_account_alerts(
    request: Request,
    state: AppState = Depends(get_state),
    admin_email: str = Form(""),
    email_alerts_enabled: str | None = Form(None),
):
    with state.session_factory() as session:
        ops = load_ops_alerts(session)
        ops.admin_email = admin_email.strip()
        ops.email_alerts_enabled = email_alerts_enabled is not None
        save_ops_alerts(session, ops)
    return RedirectResponse(url="/ui/account?alerts=1", status_code=303)


@router.post("/ui/account/digests")
def ui_account_digests(
    request: Request,
    state: AppState = Depends(get_state),
    digest_daily_enabled: str | None = Form(None),
    digest_weekly_enabled: str | None = Form(None),
    digest_include_body: str | None = Form(None),
    digest_subject: str = Form("[msgate] {period} digest"),
    digest_hour_utc: int = Form(6),
    digest_weekday: int = Form(0),
):
    with state.session_factory() as session:
        ops = load_ops_alerts(session)
        ops.digest_daily_enabled = digest_daily_enabled is not None
        ops.digest_weekly_enabled = digest_weekly_enabled is not None
        ops.digest_include_body = digest_include_body is not None
        ops.digest_subject = (digest_subject or "[msgate] {period} digest").strip()[:200]
        ops.digest_hour_utc = max(0, min(23, int(digest_hour_utc)))
        ops.digest_weekday = max(0, min(6, int(digest_weekday)))
        save_ops_alerts(session, ops)
    return RedirectResponse(url="/ui/account?digests=1", status_code=303)


@router.post("/ui/account/digests/send")
def ui_account_digests_send(request: Request, state: AppState = Depends(get_state)):
    from urllib.parse import quote

    sched = getattr(state, "digest_scheduler", None)
    if sched is None:
        from msgate.ops.digest_scheduler import DigestScheduler

        sched = DigestScheduler(state)
        state.digest_scheduler = sched
    result = sched.send_manual()
    if result.ok:
        return RedirectResponse(url="/ui/account?digest_sent=1", status_code=303)
    detail = result.error or "Digest not sent."
    return RedirectResponse(
        url=f"/ui/account?error={quote(detail)}",
        status_code=303,
    )


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


def _capacity(state: AppState):
    if state.capacity_status is not None:
        return state.capacity_status
    with state.session_factory() as session:
        ops = load_ops_alerts(session)
        pending = state.queue.pending_count(session)
        return evaluate_capacity(
            session,
            pending=pending,
            circuit=state.circuit,
            ops=ops,
        )


def _render(request: Request, state: AppState, template: str, page: str):
    cfg = state.runtime.get()
    stats = _stats(state)
    success = None
    if request.query_params.get("ok") == "1":
        success = "Password updated."
    elif request.query_params.get("alerts") == "1":
        success = "Alert settings saved."
    elif request.query_params.get("digests") == "1":
        success = "Digest settings saved."
    elif request.query_params.get("digest_sent") == "1":
        success = "Digest emailed."
    with state.session_factory() as session:
        ops = load_ops_alerts(session)
    ctx = {
        "version": __version__,
        "page": page,
        "stats": stats,
        "smtp_port": cfg.smtp.port,
        "backend_label": stats.backend_name,
        "backend_ok": stats.backend_connected,
        "ews_ok": stats.backend_connected,
        "help_url": help_url(),
        "must_change_password": bool(_session_data(request).get("must_change_password")),
        "capacity": _capacity(state),
        "ops_alerts": ops,
        "error": request.query_params.get("error"),
        "success": success,
    }
    if page == "Settings":
        ctx["config_json"] = redact_config(cfg).model_dump_json()
    return templates.TemplateResponse(request, template, ctx)
