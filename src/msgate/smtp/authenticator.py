"""SMTP AUTH authenticator with Smart Auth Sanitizer."""

from __future__ import annotations

from dataclasses import dataclass

from aiosmtpd.smtp import AuthResult, LoginPassword

from msgate.auth.sanitize import SanitizedAuth, sanitize_username
from msgate.events import EventHub
from msgate.logging_setup import get_logger

log = get_logger("smtp.auth")


@dataclass(slots=True)
class SessionAuth:
    sanitized: SanitizedAuth
    password: str


class SmtpAuthenticator:
    def __init__(
        self,
        default_domain: str | None = None,
        *,
        events: EventHub | None = None,
    ) -> None:
        self.default_domain = default_domain
        self._events = events
        self._by_peer: dict[str, SessionAuth] = {}

    def remember(self, peer_ip: str, auth: SessionAuth) -> None:
        self._by_peer[peer_ip] = auth

    def get(self, peer_ip: str) -> SessionAuth | None:
        return self._by_peer.get(peer_ip)

    def clear(self, peer_ip: str) -> None:
        self._by_peer.pop(peer_ip, None)

    def __call__(self, server, session, envelope, mechanism, auth_data) -> AuthResult:
        peer_ip = session.peer[0] if session.peer else ""
        mechanism_u = (mechanism or "").upper()

        if mechanism_u not in {"PLAIN", "LOGIN"}:
            log.warning("unsupported AUTH mechanism=%s peer=%s", mechanism, peer_ip)
            if self._events:
                self._events.publish_sync("auth.fail", f"Unsupported {mechanism}", peer=peer_ip)
            return AuthResult(success=False, handled=True)

        if not isinstance(auth_data, LoginPassword):
            return AuthResult(success=False, handled=True)

        raw_user = auth_data.login.decode("utf-8", errors="replace")
        password = auth_data.password.decode("utf-8", errors="replace")

        try:
            sanitized = sanitize_username(raw_user, default_domain=self.default_domain)
        except ValueError as exc:
            log.warning("AUTH sanitize failed peer=%s err=%s raw=%r", peer_ip, exc, raw_user)
            if self._events:
                self._events.publish_sync("auth.fail", str(exc), peer=peer_ip, raw=raw_user)
            return AuthResult(success=False, handled=True)

        self.remember(peer_ip, SessionAuth(sanitized=sanitized, password=password))
        log.info(
            "AUTH ok mechanism=%s peer=%s raw=%r sanitized=%r ews_user=%r",
            mechanism_u,
            peer_ip,
            sanitized.raw,
            sanitized.username,
            sanitized.ews_username,
        )
        if self._events:
            self._events.publish_sync(
                "auth.ok",
                f"AUTH {mechanism_u} {sanitized.raw} → {sanitized.ews_username}",
                peer=peer_ip,
                raw=sanitized.raw,
                ews_user=sanitized.ews_username,
            )
        return AuthResult(success=True, handled=True, auth_data=auth_data)
