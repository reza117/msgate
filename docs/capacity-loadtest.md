---
title: Capacity & load test
---

# Capacity & load test

## Harness

```bash
# from msgate checkout / install tree
python3 scripts/load_test_smtp.py \
  --host 127.0.0.1 --port 25 \
  --count 500 --concurrency 25
```

Optional AUTH: `--user 'DOMAIN\\svc' --password '…'`

Reports: `ok`, `deferred_4xx` (452/451), `failed`, wall time, accept rate, latency p50/max.

Automated smoke: `pytest tests/test_load_burst.py` (in-process burst + mocked EWS).

## Starting targets (single VM, defaults)

Documented **design targets** for operators (tune with `MSGATE_QUEUE_*`):

| Scenario | Target | Notes |
| --- | --- | --- |
| Burst accept | **≥ 100 msg/s** SMTP DATA accept (enqueue) on localhost allowlist | Clients should not see 5xx if under `MSGATE_QUEUE_MAX_PENDING` |
| Sustained drain | **≈ workers × Exchange RTT capacity** | Default `MSGATE_QUEUE_WORKERS=2`; raise carefully |
| Default pending cap | **5000** | Over → SMTP **452** (client retries later) |
| Circuit | **5** failures / **60s** cooldown | Open → optional SMTP **451** |

These are **starting points**, not a warranty. Measure on your VM with the harness while watching `/metrics` (`msgate_queue_pending`, `msgate_smtp_deferred_total`, `msgate_circuit_open`) and the capacity banner.

## Pass criteria (blast)

1. Concurrent clients complete without unexpected **5xx**.
2. Queue drains after the storm (pending → 0) with mocked or healthy EWS.
3. Exchange is not flooded beyond worker count (in-flight ≈ workers).
4. If deferred: only **4xx** backpressure, and clients can retry.

## When to scale

- Sustained **452** / growing oldest age → raise workers **or** move to Postgres (`MSGATE_DATABASE_URL`).
- Circuit often open → fix Exchange / credentials before raising concurrency.
