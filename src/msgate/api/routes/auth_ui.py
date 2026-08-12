"""Web auth routes: setup, login, logout, change password."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from msgate import __version__
from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.auth.admin import (
    ADMIN_USERNAME,
    admin_exists,
    check_admin_password,
    create_admin,
    get_admin,
    set_admin_password,
)
from msgate.auth.settings import external_help_url, help_url
from msgate.auth.session import COOKIE_NAME
from msgate.auth.web_middleware import load_session
from msgate.http.root_path import cookie_path, join_root
from msgate.ui.context import template_context
from msgate.ui.render import templates

router = APIRouter(tags=["auth"])


def _session(request: Request) -> dict:
    data = getattr(request.state, "msgate_session", None)
    if data is None:
        data = load_session(request)
    request.state.msgate_session = data
    return data


def _redirect(request: Request, path: str) -> RedirectResponse:
    return RedirectResponse(url=join_root(request, path), status_code=303)


def _auth_ctx(
    request: Request,
    *,
    error: str | None = None,
    forced: bool = False,
    next_url: str = "/",
) -> dict:
    return template_context(
        request,
        version=__version__,
        error=error,
        help_url=help_url(),
        external_help_url=external_help_url(),
        forced=forced,
        next_url=next_url,
    )


def _login_session(request: Request, *, must_change: bool) -> None:
    session = _session(request)
    session["admin_user"] = ADMIN_USERNAME
    session["must_change_password"] = must_change
    request.state.msgate_session = session


@router.get("/ui/setup", response_class=HTMLResponse)
def ui_setup(request: Request, state: AppState = Depends(get_state)):
    with state.session_factory() as session:
        if admin_exists(session):
            return _redirect(request, "/ui/login")
    return templates.TemplateResponse(
        request,
        "auth/setup.html",
        _auth_ctx(request),
    )


@router.post("/ui/auth/setup")
def auth_setup(
    request: Request,
    password: str = Form(...),
    password_confirm: str = Form(...),
    state: AppState = Depends(get_state),
):
    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "auth/setup.html",
            _auth_ctx(request, error="Passwords do not match"),
            status_code=400,
        )
    try:
        with state.session_factory() as session:
            if admin_exists(session):
                return _redirect(request, "/ui/login")
            create_admin(session, password, must_change_password=False)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "auth/setup.html",
            _auth_ctx(request, error=str(exc)),
            status_code=400,
        )
    _login_session(request, must_change=False)
    return _redirect(request, "/")


@router.get("/ui/login", response_class=HTMLResponse)
def ui_login(request: Request, state: AppState = Depends(get_state)):
    with state.session_factory() as session:
        if not admin_exists(session):
            return _redirect(request, "/ui/setup")
    session = _session(request)
    if session.get("admin_user") == ADMIN_USERNAME:
        if session.get("must_change_password"):
            return _redirect(request, "/ui/change-password")
        return _redirect(request, "/")
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        _auth_ctx(request),
    )


@router.post("/ui/auth/login")
def auth_login(
    request: Request,
    password: str = Form(...),
    state: AppState = Depends(get_state),
):
    with state.session_factory() as session:
        if not admin_exists(session):
            return _redirect(request, "/ui/setup")
        row = get_admin(session)
        if not check_admin_password(session, password):
            return templates.TemplateResponse(
                request,
                "auth/login.html",
                _auth_ctx(request, error="Invalid password"),
                status_code=401,
            )
        must_change = bool(row and row.must_change_password)
    _login_session(request, must_change=must_change)
    if must_change:
        return _redirect(request, "/ui/change-password")
    return _redirect(request, "/")


@router.get("/ui/change-password", response_class=HTMLResponse)
def ui_change_password(request: Request):
    session = _session(request)
    if session.get("admin_user") != ADMIN_USERNAME:
        return _redirect(request, "/ui/login")
    forced = bool(session.get("must_change_password"))
    return templates.TemplateResponse(
        request,
        "auth/change_password.html",
        _auth_ctx(request, forced=forced, next_url="/"),
    )


@router.post("/ui/auth/change-password")
def auth_change_password(
    request: Request,
    current_password: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    next: str = Form("/"),
    state: AppState = Depends(get_state),
):
    session = _session(request)
    if session.get("admin_user") != ADMIN_USERNAME:
        return _redirect(request, "/ui/login")
    forced = bool(session.get("must_change_password"))
    next_url = next if next.startswith("/ui/") or next == "/" else "/"

    def _fail(msg: str, status: int = 400):
        if next_url.startswith("/ui/account"):
            return _redirect(request, f"/ui/account?error={quote(msg)}")
        return templates.TemplateResponse(
            request,
            "auth/change_password.html",
            _auth_ctx(request, error=msg, forced=forced, next_url=next_url),
            status_code=status,
        )

    if password != password_confirm:
        return _fail("New passwords do not match")
    with state.session_factory() as session_db:
        if not check_admin_password(session_db, current_password):
            return _fail("Current password is incorrect", status=401)
        try:
            set_admin_password(session_db, password, must_change_password=False)
        except ValueError as exc:
            return _fail(str(exc))
    session["must_change_password"] = False
    request.state.msgate_session = session
    if next_url.startswith("/ui/account"):
        return _redirect(request, "/ui/account?ok=1")
    return _redirect(request, next_url or "/")


@router.post("/ui/auth/logout")
def auth_logout(request: Request):
    request.state.msgate_session = {}
    resp = _redirect(request, "/ui/login")
    resp.headers["Cache-Control"] = "no-store"
    resp.delete_cookie(COOKIE_NAME, path=cookie_path(request))
    return resp


@router.get("/ui/help", response_class=HTMLResponse)
def ui_help(request: Request):
    return templates.TemplateResponse(
        request,
        "auth/help.html",
        _auth_ctx(request),
    )
