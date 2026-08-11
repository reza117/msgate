#!/usr/bin/env python3
"""SMTP burst / load harness for msgate (Zabbix-like fan-in).

Example (IP allowlist, same host as msgate):

  python scripts/load_test_smtp.py --host 127.0.0.1 --port 2525 --count 200 --concurrency 20

With AUTH PLAIN:

  python scripts/load_test_smtp.py --user 'DOMAIN\\\\svc' --password secret --count 100
"""

from __future__ import annotations

import argparse
import smtplib
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from email.message import EmailMessage


@dataclass
class Result:
    ok: int = 0
    deferred: int = 0  # 4xx
    failed: int = 0
    duration_s: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _one(
    *,
    host: str,
    port: int,
    index: int,
    mail_from: str,
    rcpt_to: str,
    user: str | None,
    password: str | None,
    subject_prefix: str,
) -> tuple[str, float, str]:
    t0 = time.perf_counter()
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = rcpt_to
    msg["Subject"] = f"{subject_prefix} #{index}"
    msg.set_content(f"msgate load test message {index}\n")
    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            if user is not None:
                smtp.login(user, password or "")
            smtp.send_message(msg)
        ms = (time.perf_counter() - t0) * 1000
        return "ok", ms, ""
    except smtplib.SMTPResponseException as exc:
        ms = (time.perf_counter() - t0) * 1000
        code = int(exc.smtp_code)
        detail = f"{code} {exc.smtp_error!r}"
        if 400 <= code < 500:
            return "deferred", ms, detail
        return "failed", ms, detail
    except Exception as exc:  # noqa: BLE001 — harness must not die on one client
        ms = (time.perf_counter() - t0) * 1000
        return "failed", ms, str(exc)


def run_burst(args: argparse.Namespace) -> Result:
    result = Result()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futs = [
            pool.submit(
                _one,
                host=args.host,
                port=args.port,
                index=i,
                mail_from=args.mail_from,
                rcpt_to=args.rcpt_to,
                user=args.user,
                password=args.password,
                subject_prefix=args.subject,
            )
            for i in range(args.count)
        ]
        for fut in as_completed(futs):
            status, ms, err = fut.result()
            result.latencies_ms.append(ms)
            if status == "ok":
                result.ok += 1
            elif status == "deferred":
                result.deferred += 1
                if len(result.errors) < 10:
                    result.errors.append(err)
            else:
                result.failed += 1
                if len(result.errors) < 10:
                    result.errors.append(err)
    result.duration_s = time.perf_counter() - t0
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="msgate SMTP load / burst harness")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=25)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=10)
    p.add_argument("--mail-from", default="zabbix@example.com")
    p.add_argument("--rcpt-to", default="ops@example.com")
    p.add_argument("--user", default=None, help="SMTP AUTH username (optional)")
    p.add_argument("--password", default=None)
    p.add_argument("--subject", default="msgate-loadtest")
    args = p.parse_args(argv)

    print(
        f"burst host={args.host}:{args.port} count={args.count} "
        f"concurrency={args.concurrency}",
        flush=True,
    )
    result = run_burst(args)
    duration = result.duration_s
    rate = result.ok / duration if duration > 0 else 0.0
    print(f"ok={result.ok} deferred_4xx={result.deferred} failed={result.failed}")
    print(f"wall_seconds={duration:.2f} accept_rate_ok_per_s={rate:.1f}")
    if result.latencies_ms:
        print(
            "latency_ms "
            f"p50={statistics.median(result.latencies_ms):.0f} "
            f"max={max(result.latencies_ms):.0f} "
            f"mean={statistics.mean(result.latencies_ms):.0f}"
        )
    for err in result.errors:
        print(f"sample_error: {err}")
    if result.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
