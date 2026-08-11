---
title: Digest reports
---

# Digest reports

Account → **Digest reports** sends a daily and/or weekly PDF to the **admin alert email**.

## Contents

- Sent / failed counts for the window
- Pending / retrying at report time
- Max delivery delay (message id + why)
- Top failure reasons
- Short notable / critical notes

PDF is always attached via EWS `FileAttachment` (works for plain-text and HTML clients). Optional short text body.

## Settings

| Setting | Meaning |
| --- | --- |
| Daily / Weekly | Enable scheduled digests |
| Subject template | Placeholders `{period}`, `{from}`, `{to}` |
| Hour (UTC) | Earliest hour to send |
| Weekly weekday | Monday=0 … Sunday=6 |
| Include short body | Text part in addition to PDF |

**Send digest now** emails a manual (last-24h) report immediately — needs admin email + Exchange credentials.

Scheduler runs in the msgate process (no cron required).
