"""CLI entrypoint."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time

import uvicorn

from msgate import __version__
from msgate.api.app import create_app
from msgate.app.bootstrap import admin_configured, build_app_state
from msgate.cli.admin import cmd_reset_password
from msgate.config_load import load_config_from_env
from msgate.logging_setup import get_logger, setup_logging
from msgate.observability.log_retention import purge_old_logs, setup_file_logging
from msgate.smtp.server import create_controller
from msgate.tls.negotiate import endpoint_from_url, prepare_ews_tls
from msgate.tls.probe import probe_profile
from msgate.tls.profiles import TlsMode, ladder_for_mode


def _run_api(app_state, host: str, port: int) -> None:
    app = create_app(app_state)
    uvicorn.run(app, host=host, port=port, log_level="info")


def _cmd_serve(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    log_path = setup_file_logging(args.log_level)
    log = get_logger("cli")
    purge_old_logs()
    if log_path:
        log.info("file logging enabled path=%s", log_path)

    state = build_app_state()
    config = state.runtime.get()

    # Bind API/UI first so the Web UI is reachable even if TLS/EWS is slow or down.
    api_host = args.api_host or os.environ.get("MSGATE_API_HOST", "127.0.0.1")
    api_port = int(args.api_port or os.environ.get("MSGATE_API_PORT", "8080"))
    api_thread = threading.Thread(
        target=_run_api,
        args=(state, api_host, api_port),
        name="msgate-api",
        daemon=True,
    )
    api_thread.start()
    log.info("API/UI listening on http://%s:%s", api_host, api_port)

    if config.ews is None:
        log.warning(
            "EWS not configured yet — API/UI will start; "
            "set Exchange settings in the Web UI (Settings) or MSGATE_EWS_* env on first boot"
        )
    else:
        try:
            negotiated = prepare_ews_tls(config.ews)
            log.info(
                "TLS ready profile=%s host=%s:%s cached=%s",
                negotiated.profile_id.value,
                negotiated.host,
                negotiated.port,
                negotiated.from_cache,
            )
        except Exception as exc:  # noqa: BLE001 — keep UI up; delivery may fail until fixed
            log.error("EWS TLS prepare failed (UI still up): %s", exc)

    state.worker.start()
    controller, _auth = create_controller(state.runtime, state.queue, events=state.events)
    controller.start()
    state.smtp_controller = controller
    state.smtp_running = True

    log.info(
        "msgate %s smtp://%s:%s api://%s:%s (Ctrl+C to stop)",
        __version__,
        config.smtp.bind_address,
        config.smtp.port,
        api_host,
        api_port,
    )

    if config.ews is None:
        print(
            f"\n msgate: Exchange not configured — open http://{api_host}:{api_port}/ui/settings\n",
            file=sys.stderr,
        )

    if not admin_configured(state.session_factory):
        banner = (
            "\n"
            "═══════════════════════════════════════════════════════\n"
            " msgate: No admin account yet.\n"
            f" Open http://{api_host}:{api_port}/ in your browser to set your password.\n"
            "═══════════════════════════════════════════════════════"
        )
        print(banner, file=sys.stderr)
        log.warning("No admin account — open http://%s:%s/ to create password", api_host, api_port)

    stop = False

    def _stop(*_args: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while not stop:
            time.sleep(0.2)
    finally:
        state.smtp_running = False
        controller.stop()
        state.worker.stop()
        log.info("msgate stopped")
    return 0


def _cmd_tls_probe(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    log = get_logger("cli")
    config = load_config_from_env()
    if config.ews is None:
        log.error("MSGATE_EWS_URL is required for tls-probe")
        return 2

    ews = config.ews
    host, port = endpoint_from_url(str(ews.server_url))
    mode = TlsMode(ews.tls_mode)
    print(f"endpoint={host}:{port} mode={mode.value}")
    print(f"ca_file={ews.ca_file or '(system)'} trust_self_signed={ews.trust_self_signed}")

    any_ok = False
    for profile_id in ladder_for_mode(mode):
        result = probe_profile(
            host,
            port,
            profile_id,
            ca_file=ews.ca_file,
            trust_self_signed=ews.trust_self_signed,
            timeout=args.timeout,
        )
        status = "OK" if result.ok else "FAIL"
        detail = result.negotiated or result.error or ""
        print(f"  [{status}] {profile_id.value}: {detail}")
        any_ok = any_ok or result.ok

    if args.apply_cache and any_ok:
        negotiated = prepare_ews_tls(ews, force_reprobe=True)
        print(f"cached_profile={negotiated.profile_id.value}")

    return 0 if any_ok else 1


def _cmd_admin_reset(_args: argparse.Namespace) -> int:
    return cmd_reset_password()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="msgate", description="msgate SMTP → EWS gateway")
    parser.add_argument("--version", action="version", version=f"msgate {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start SMTP + API + queue worker")
    serve.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    serve.add_argument(
        "--api-host",
        default=os.environ.get("MSGATE_API_HOST", "127.0.0.1"),
        help="API/UI bind address (env MSGATE_API_HOST; default 127.0.0.1)",
    )
    serve.add_argument(
        "--api-port",
        type=int,
        default=int(os.environ.get("MSGATE_API_PORT", "8080")),
        help="API/UI port (env MSGATE_API_PORT; default 8080)",
    )
    serve.set_defaults(func=_cmd_serve)

    probe = sub.add_parser("tls-probe", help="Probe EWS TLS profiles (no mail send)")
    probe.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    probe.add_argument("--timeout", type=float, default=10.0)
    probe.add_argument(
        "--apply-cache",
        action="store_true",
        help="Cache the first working profile from auto/legacy ladder",
    )
    probe.set_defaults(func=_cmd_tls_probe)

    admin = sub.add_parser("admin", help="Admin account management")
    admin_sub = admin.add_subparsers(dest="admin_command", required=True)
    reset = admin_sub.add_parser("reset-password", help="Reset web admin password (root only)")
    reset.set_defaults(func=_cmd_admin_reset)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        sys.exit(0)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
