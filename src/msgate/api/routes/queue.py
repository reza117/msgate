"""Outbound message queue API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.queue import repository as repo
from msgate.schemas.enums import MessageStatus
from msgate.schemas.message_detail import MessageDetail
from msgate.schemas.messages import MessageRecord
from msgate.ui.render import templates

router = APIRouter(prefix="/api/v1", tags=["queue"])


@router.get("/queue", response_model=list[MessageRecord])
def get_queue(
    status: MessageStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    state: AppState = Depends(get_state),
) -> list[MessageRecord]:
    with state.session_factory() as session:
        return state.queue.list_queue(session, status=status, limit=limit)


@router.get("/messages/{message_id}", response_model=MessageDetail)
def get_message(message_id: str, state: AppState = Depends(get_state)) -> MessageDetail:
    with state.session_factory() as session:
        row = repo.get_message(session, message_id)
        if row is None:
            raise HTTPException(status_code=404, detail="message not found")
        mime = repo.get_mime_bytes(row).decode("utf-8", errors="replace")[:4000]
        rec = repo.row_to_record(row)
        return MessageDetail(
            **rec.model_dump(),
            mime_preview=mime,
        )


@router.get("/ui/messages/{message_id}", response_class=HTMLResponse)
def ui_message_detail(
    message_id: str,
    request: Request,
    state: AppState = Depends(get_state),
):
    detail = get_message(message_id, state)
    return templates.TemplateResponse(
        request,
        "partials/message_detail.html",
        {"msg": detail},
    )
