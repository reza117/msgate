"""Web auth routes: setup, login, logout, change password."""

from __future__ import annotations

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
from msgate.auth.settings import help_url
from msgate.auth.web_middleware import load_session
from msgate.ui.render import templates

router = APIRouter(tags=["auth"])


def _session(request: Request) -> dict:
    data = getattr(request.state, "msgate_session", None)
    if data is None:
        data = load_session(request)
    request.state.msgate_session = data
    return data


def _auth_ctx(request: Request, *, error: str | None = None) -> dict:
    return {
        "version": __version__,
        "error": error,
        "help_url": help_url(),
    }


def _login_session(request: Request, *, must_change: bool) -> None:
    session = _session(request)
    session["admin_user"] = ADMIN_USERNAME
    session["must_change_password"] = must_change
    request.state.msgate_session = session


@router.get("/ui/setup", response_class=HTMLResponse)
def ui_setup(request: Request, state: AppState = Depends(get_state)):
    with state.session_factory() as session:
        if admin_exists(session):
            return RedirectResponse(url="/ui/login", status_code=303)
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
                return RedirectResponse(url="/ui/login", status_code=303)
            create_admin(session, password, must_change_password=False)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "auth/setup.html",
            _auth_ctx(request, error=str(exc)),
            status_code=400,
        )
    _login_session(request, must_change=False)
    return RedirectResponse(url="/", status_code=303)


@router.get("/ui/login", response_class=HTMLResponse)
def ui_login(request: Request, state: AppState = Depends(get_state)):
    with state.session_factory() as session:
        if not admin_exists(session):
            return RedirectResponse(url="/ui/setup", status_code=303)
    session = _session(request)
    if session.get("admin_user") == ADMIN_USERNAME:
        if session.get("must_change_password"):
            return RedirectResponse(url="/ui/change-password", status_code=303)
        return RedirectResponse(url="/", status_code=303)
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
            return RedirectResponse(url="/ui/setup", status_code=303)
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
        return RedirectResponse(url="/ui/change-password", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.get("/ui/change-password", response_class=HTMLResponse)
def ui_change_password(request: Request):
    session = _session(request)
    if session.get("admin_user") != ADMIN_USERNAME:
        return RedirectResponse(url="/ui/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "auth/change_password.html",
        _auth_ctx(request),
    )


@router.post("/ui/auth/change-password")
def auth_change_password(
    request: Request,
    current_password: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    state: AppState = Depends(get_state),
):
    session = _session(request)
    if session.get("admin_user") != ADMIN_USERNAME:
        return RedirectResponse(url="/ui/login", status_code=303)
    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "auth/change_password.html",
            _auth_ctx(request, error="New passwords do not match"),
            status_code=400,
        )
    with state.session_factory() as session_db:
        if not check_admin_password(session_db, current_password):
            return templates.TemplateResponse(
                request,
                "auth/change_password.html",
                _auth_ctx(request, error="Current password is incorrect"),
                status_code=401,
            )
        try:
            set_admin_password(session_db, password, must_change_password=False)
        except ValueError as exc:
            return templates.TemplateResponse(
                request,
                "auth/change_password.html",
                _auth_ctx(request, error=str(exc)),
                status_code=400,
            )
    session["must_change_password"] = False
    request.state.msgate_session = session
    return RedirectResponse(url="/", status_code=303)


@router.post("/ui/auth/logout")
def auth_logout(request: Request):
    request.state.msgate_session = {}
    return RedirectResponse(url="/ui/login", status_code=303)


@router.get("/ui/help", response_class=HTMLResponse)
def ui_help(request: Request):
    return templates.TemplateResponse(
        request,
        "auth/help.html",
        _auth_ctx(request),
    )
