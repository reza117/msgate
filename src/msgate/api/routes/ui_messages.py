"""Message table partial."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.ui.context import template_context
from msgate.ui.render import templates

router = APIRouter(tags=["ui"])


@router.get("/ui/partials/message-table", response_class=HTMLResponse)
def partial_message_table(request: Request, state: AppState = Depends(get_state)):
    with state.session_factory() as session:
        rows = state.queue.list_queue(session, limit=50)
    return templates.TemplateResponse(
        request,
        "partials/message_table.html",
        template_context(request, rows=rows),
    )
