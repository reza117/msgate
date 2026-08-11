---
title: Database
---

# SQLite vs Postgres

## Default: SQLite

No extra packages. Data file under `MSGATE_DATA_DIR` (default `/var/lib/msgate/msgate.db`). WAL + `busy_timeout` enabled.

**Stay on SQLite when:** single VM, modest Zabbix volume, queue drains after storms, no sustained high defer rate.

## Optional: Postgres

```bash
/opt/msgate/.venv/bin/pip install 'msgate[postgres]'
```

In `msgate.env`:

```bash
MSGATE_DATABASE_URL=postgresql+psycopg://msgate:SECRET@127.0.0.1:5432/msgate
```

Then `systemctl restart msgate` (migrations run on start).

**Switch when:** after a storm, queue age stays high **and** you see SMTP `452` / DB lock pressure; or you want stronger concurrent INSERT + UPDATE headroom.

Redis is **not** required for Phase 5.5 throughput.
