"""WebSocket live traffic stream."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from msgate.app.state import AppState
from msgate.auth.admin import ADMIN_USERNAME
from msgate.auth.session import COOKIE_NAME, decode_session, session_key

router = APIRouter(tags=["websocket"])


def _ws_session(websocket: WebSocket) -> dict:
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        return {}
    state: AppState = websocket.app.state.msgate
    return decode_session(token, session_key(state)) or {}


@router.websocket("/api/v1/ws/traffic")
async def traffic_ws(websocket: WebSocket):
    session = _ws_session(websocket)
    if session.get("admin_user") != ADMIN_USERNAME:
        await websocket.close(code=4401)
        return
    if session.get("must_change_password"):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    state: AppState = websocket.app.state.msgate
    queue = await state.events.subscribe()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_text(msg)
            except TimeoutError:
                await websocket.send_text('{"kind":"ping","message":"keepalive","data":{}}')
    except WebSocketDisconnect:
        pass
    finally:
        await state.events.unsubscribe(queue)
