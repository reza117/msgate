"""Diagnostic message send API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.schemas.messages import EmailMessageRequest

router = APIRouter(prefix="/api/v1", tags=["messages"])


@router.post("/messages/test")
def send_test_email(
    body: EmailMessageRequest,
    state: AppState = Depends(get_state),
) -> dict[str, str]:
    cfg = state.runtime.get()
    ews = cfg.ews
    if ews is None or not ews.username or not ews.password:
        raise HTTPException(
            status_code=400,
            detail="EWS username/password required in config for API test send",
        )

    result = state.queue.submit_test(
        sender=str(body.sender),
        recipients=[str(r) for r in body.recipients],
        subject=body.subject,
        body=body.body,
        is_html=body.is_html,
        ews_username=ews.username,
        password=ews.password,
    )
    return {"message_id": result.message_id, "status": result.status}
