"""Session cookie middleware and auth gate."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from msgate.auth.admin import ADMIN_USERNAME, admin_exists
from msgate.auth.session import COOKIE_NAME, MAX_AGE, decode_session, encode_session, session_key

PUBLIC_PATHS = frozenset({"/healthz", "/readyz", "/metrics"})
SETUP_PATH = "/ui/setup"
LOGIN_PATH = "/ui/login"
CHANGE_PATH = "/ui/change-password"
AUTH_PREFIX = "/ui/auth"


def _wants_html(request: Request) -> bool:
    path = request.url.path
    if path.startswith("/api/"):
        return False
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return False
    return "text/html" in accept or "*/*" in accept or not accept


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _redirect(url: str) -> RedirectResponse:
    resp = RedirectResponse(url=url, status_code=303)
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _htmx_redirect(url: str, *, status_code: int = 401) -> Response:
    """Force a full-page navigation — do not swap login HTML into an HTMX target."""
    return Response(
        status_code=status_code,
        headers={"HX-Redirect": url, "Cache-Control": "no-store"},
    )


def _unauthorized(request: Request) -> Response:
    if _is_htmx(request):
        return _htmx_redirect(LOGIN_PATH, status_code=401)
    if _wants_html(request):
        return _redirect(LOGIN_PATH)
    return JSONResponse({"detail": "Not authenticated"}, status_code=401)


def _forbidden_change(request: Request) -> Response:
    if _is_htmx(request):
        return _htmx_redirect(CHANGE_PATH, status_code=403)
    if _wants_html(request):
        return _redirect(CHANGE_PATH)
    return JSONResponse({"detail": "Password change required"}, status_code=403)


def _need_setup(request: Request) -> Response:
    if _is_htmx(request):
        return _htmx_redirect(SETUP_PATH, status_code=401)
    if _wants_html(request):
        return _redirect(SETUP_PATH)
    return JSONResponse({"detail": "Admin setup required"}, status_code=401)


def load_session(request: Request) -> dict:
    state = request.app.state.msgate
    key = session_key(state)
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return {}
    data = decode_session(token, key)
    return data or {}


def save_session(response: Response, request: Request, session: dict) -> None:
    if not session:
        response.delete_cookie(COOKIE_NAME, path="/")
        return
    state = request.app.state.msgate
    key = session_key(state)
    response.set_cookie(
        COOKIE_NAME,
        encode_session(session, key),
        max_age=MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.msgate_session = load_session(request)
        response = await call_next(request)
        session = getattr(request.state, "msgate_session", None)
        if session is not None:
            save_session(response, request, session)
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS:
            return await call_next(request)

        state = request.app.state.msgate
        with state.session_factory() as session:
            has_admin = admin_exists(session)

        session_data = load_session(request)

        if not has_admin:
            if path == SETUP_PATH or path.startswith(f"{AUTH_PREFIX}/setup"):
                return await call_next(request)
            return _need_setup(request)

        logged_in = session_data.get("admin_user") == ADMIN_USERNAME
        must_change = bool(session_data.get("must_change_password"))

        if path == SETUP_PATH or path.startswith(f"{AUTH_PREFIX}/setup"):
            return _redirect(LOGIN_PATH)

        if not logged_in:
            if path == LOGIN_PATH or path.startswith(f"{AUTH_PREFIX}/login"):
                return await call_next(request)
            return _unauthorized(request)

        if must_change:
            allowed = {
                CHANGE_PATH,
                f"{AUTH_PREFIX}/change-password",
                f"{AUTH_PREFIX}/logout",
            }
            if path not in allowed:
                return _forbidden_change(request)

        request.state.msgate_session = session_data
        return await call_next(request)
