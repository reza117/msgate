---
title: Logs UI
---

# Logs UI

Search on-disk msgate log files from the Web UI (**Logs** in the sidebar).

## Requirements

- File logging enabled (default): `MSGATE_FILE_LOGGING` not set to `false`.
- Log directory: `MSGATE_LOG_DIR`, or `{MSGATE_DATA_DIR}/logs`.
- Files named `msgate-YYYYMMDD.log` (daily).

## Filters

| Field | Meaning |
| --- | --- |
| Search | Substring match on the full log line (message id, peer IP, error text, …) |
| Level | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| Logger contains | e.g. `smtp`, `queue`, `ews` |
| Day | `YYYYMMDD` — only that day’s file |
| Limit | Max rows (1–2000, default 200) |

Newest matching lines first. Unparsed lines still appear (message = raw text).

## Tips

- After a Zabbix storm, filter `ERROR` or search a known `message_id`.
- Retention: `MSGATE_LOG_RETENTION_DAYS` (default 14). Older files are purged on start.
- Digests (daily/weekly PDF) are a separate Phase 5.5 item; Logs UI is for live investigation.
