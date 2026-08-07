"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

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
    ui_messages,
    ws,
)
from msgate.app.state import AppState
from msgate.auth.web_middleware import AuthMiddleware, SessionMiddleware


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(
        title="msgate API",
        description="SMTP → EWS/Graph gateway management API",
        version=__version__,
    )
    app.state.msgate = state
    app.add_middleware(AuthMiddleware)
    app.add_middleware(SessionMiddleware)
    app.include_router(auth_ui.router)
    app.include_router(ui.router)
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
