"""Schedule daily/weekly digest emails."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from msgate.app.state import AppState
from msgate.logging_setup import get_logger
from msgate.ops.alerts_config import OpsAlertsConfig, load_ops_alerts
from msgate.ops.digest_mail import DigestSendResult, send_digest
from msgate.ops.digest_report import DigestReport, collect_digest
from msgate.ops.digest_state import DigestState, load_digest_state, save_digest_state

log = get_logger("ops.digest_scheduler")


class DigestScheduler:
    def __init__(self, state: AppState, *, interval: float = 60.0) -> None:
        self._state = state
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="msgate-digest",
            daemon=True,
        )
        self._thread.start()
        log.info("digest scheduler started interval=%ss", self._interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        log.info("digest scheduler stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("digest scheduler tick failed")
            self._stop.wait(self._interval)

    def tick(self, *, now: datetime | None = None) -> list[str]:
        """Evaluate due digests. Returns periods sent (for tests)."""
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        sent: list[str] = []
        with self._state.session_factory() as session:
            ops = load_ops_alerts(session)
            st = load_digest_state(session)
        if not ops.admin_email.strip():
            return sent
        if ops.digest_daily_enabled and self._daily_due(ops, st, now):
            report = self._build(period="daily", now=now)
            if self._dispatch(ops, report).ok:
                with self._state.session_factory() as session:
                    st = load_digest_state(session)
                    st.last_daily = now.strftime("%Y-%m-%d")
                    save_digest_state(session, st)
                sent.append("daily")
        if ops.digest_weekly_enabled and self._weekly_due(ops, st, now):
            # reload state after possible daily update
            with self._state.session_factory() as session:
                st = load_digest_state(session)
            report = self._build(period="weekly", now=now)
            if self._dispatch(ops, report).ok:
                with self._state.session_factory() as session:
                    st = load_digest_state(session)
                    st.last_weekly = _iso_week(now)
                    save_digest_state(session, st)
                sent.append("weekly")
        return sent

    def send_manual(self, *, period: str = "manual") -> DigestSendResult:
        with self._state.session_factory() as session:
            ops = load_ops_alerts(session)
        if not ops.admin_email.strip():
            return DigestSendResult(
                False,
                "Admin alert email is empty — save it under Capacity alerts first.",
            )
        report = self._build(period=period, now=datetime.now(UTC))
        return self._dispatch(ops, report)

    def _dispatch(self, ops: OpsAlertsConfig, report: DigestReport) -> DigestSendResult:
        return send_digest(
            self._state,
            report,
            to_email=ops.admin_email.strip(),
            subject_template=ops.digest_subject or "[msgate] {period} digest",
            include_body=ops.digest_include_body,
        )

    def _build(self, *, period: str, now: datetime) -> DigestReport:
        start, end = window_for(period, now)
        with self._state.session_factory() as session:
            return collect_digest(
                session,
                period=period,
                window_start=start,
                window_end=end,
            )

    def _daily_due(self, ops: OpsAlertsConfig, st: DigestState, now: datetime) -> bool:
        if now.hour < max(0, min(23, int(ops.digest_hour_utc))):
            return False
        today = now.strftime("%Y-%m-%d")
        return st.last_daily != today

    def _weekly_due(self, ops: OpsAlertsConfig, st: DigestState, now: datetime) -> bool:
        if now.weekday() != max(0, min(6, int(ops.digest_weekday))):
            return False
        if now.hour < max(0, min(23, int(ops.digest_hour_utc))):
            return False
        return st.last_weekly != _iso_week(now)


def window_for(period: str, now: datetime) -> tuple[datetime, datetime]:
    end = now
    if period == "weekly":
        start = end - timedelta(days=7)
    else:
        start = end - timedelta(days=1)
    return start, end


def _iso_week(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
