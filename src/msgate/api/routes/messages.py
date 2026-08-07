"""Diagnostic message send API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from msgate.api.backend import require_backend_credentials
from msgate.api.deps import get_state
from msgate.app.state import AppState
from msgate.schemas.messages import EmailMessageRequest

router = APIRouter(prefix="/api/v1", tags=["messages"])


@router.post("/messages/test")
def send_test_email(
    body: EmailMessageRequest,
    state: AppState = Depends(get_state),
) -> dict[str, str]:
    username, password = require_backend_credentials(state)
    result = state.queue.submit_test(
        sender=str(body.sender),
        recipients=[str(r) for r in body.recipients],
        subject=body.subject,
        body=body.body,
        is_html=body.is_html,
        ews_username=username,
        password=password,
    )
    return {"message_id": result.message_id, "status": result.status}
