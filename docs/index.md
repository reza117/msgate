---
title: msgate
description: SMTP gateway for Exchange (EWS) — docs for operators
---

# msgate

**SMTP for the OAuth era.** Clients like Zabbix speak SMTP; msgate delivers through Exchange Web Services.

## Docs

- [Install & first login](install.md)
- [Queue & blast controls](queue.md)
- [Capacity alerts](capacity.md)
- [Capacity & load test](capacity-loadtest.md)
- [Digest reports](digests.md)
- [Logs UI](logs.md)
- [SQLite vs Postgres](database.md)

## Help from the product

In the Web UI, sidebar **Help ↗** opens this site (`MSGATE_HELP_URL`, default `https://msgate.github.io/msgate/`).

## What msgate does

1. Accepts SMTP (`AUTH PLAIN` / `LOGIN`, or IP allowlist).
2. Enqueues the message (fast accept — does not wait on Exchange).
3. Worker pool sends via EWS with retry, circuit breaker, and backpressure.
4. Operators use the Web UI for settings, messages, **logs**, and capacity banners.
