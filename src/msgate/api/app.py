"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from msgate import __version__
from msgate.api.routes import (
    auth_ui,
    config,
    ha,
    health,
    messages,
    metrics,
    queue,
    stats,
    tools,
    ui,
    ui_logs,
    ui_messages,
    ws,
)
from msgate.app.state import AppState
from msgate.auth.web_middleware import AuthMiddleware, SessionMiddleware
from msgate.http.root_path import configured_root_path


def create_app(state: AppState) -> FastAPI:
    root = configured_root_path()
    openapi_path = "/openapi.json"
    browser_openapi = f"{root}{openapi_path}" if root else openapi_path

    app = FastAPI(
        title="msgate API",
        description=(
            "SMTP → EWS/Graph gateway management API.\n\n"
            "OpenAPI **examples are fictional** (`example.com`, `DOMAIN\\\\svc.msgate`). "
            "They are not live data. Use **Try it out** only when authenticated — "
            "that returns real queue/config from this instance."
        ),
        version=__version__,
        root_path=root,
        docs_url=None,
        redoc_url=None,
        openapi_url=openapi_path,
    )
    app.state.msgate = state
    app.add_middleware(AuthMiddleware)
    app.add_middleware(SessionMiddleware)

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url=browser_openapi, title=f"{app.title} — Swagger")

    @app.get("/redoc", include_in_schema=False)
    async def redoc_ui() -> HTMLResponse:
        return get_redoc_html(openapi_url=browser_openapi, title=f"{app.title} — ReDoc")

    app.include_router(auth_ui.router)
    app.include_router(ui.router)
    app.include_router(ui_logs.router)
    app.include_router(ui_messages.router)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(ha.router)
    app.include_router(stats.router)
    app.include_router(config.router)
    app.include_router(queue.router)
    app.include_router(messages.router)
    app.include_router(tools.router)
    app.include_router(ws.router)
    return app
