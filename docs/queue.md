---
title: Queue & blast controls
---

# Queue & blast controls

All variables live in **`msgate.env`** (or the process environment). **Restart** the service after changes. These are **not** in the Web UI yet.

| Variable | Default | Meaning |
| --- | --- | --- |
| `MSGATE_QUEUE_WORKERS` | `2` | Parallel outbound send threads (1–32) |
| `MSGATE_QUEUE_MAX_PENDING` | `5000` | Max queued/retrying; over → SMTP `452` |
| `MSGATE_CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `MSGATE_CIRCUIT_COOLDOWN_SECONDS` | `60` | Seconds before a half-open probe |
| `MSGATE_SMTP_REJECT_ON_CIRCUIT` | `true` | Circuit open → SMTP `451` |

## Behaviour

1. SMTP **DATA** enqueues and returns `250` (unless backpressure).
2. Workers claim rows and send via EWS; failures retry with backoff.
3. Too many failures → circuit **open** (workers pause; optional SMTP defer).
4. Queue too deep → SMTP **452** so the client can retry later.

Prometheus (`/metrics`): `msgate_queue_pending`, `msgate_in_flight`, `msgate_smtp_deferred_total`, `msgate_circuit_open`, send latency gauges.
