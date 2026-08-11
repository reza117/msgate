# msgate

SMTP gateway for Exchange Web Services (EWS). Clients (Zabbix, scripts, etc.) submit mail over SMTP; msgate delivers via Exchange.

## Quick start (dev)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/msgate serve --api-host 127.0.0.1 --api-port 8080
```

Open http://127.0.0.1:8080/ — set the admin password, then **Settings** → Exchange.

## Production install (systemd)

From a release tarball or git checkout:

```bash
sudo ./install.sh
# msgate.env created from example if missing (MSGATE_API_HOST=0.0.0.0)
sudo systemctl start msgate
```

### Upgrade (keep data)

```bash
# On the server (uses GitHub latest release tarball; keeps DB + msgate.env):
sudo /opt/msgate/msgate-update.sh
# same as:
sudo /opt/msgate/msgate-update.sh --latest
```

Requires a **`.tar.gz` asset** on the GitHub Release (not only “Source code”).  
Repo default: `msgate/msgate` — override with `MSGATE_GITHUB_REPO=owner/repo`.

Offline / already unpacked:

```bash
sudo ./msgate-update.sh --local
sudo ./msgate-update.sh /tmp/msgate-0.0.15.tar.gz
sudo ./msgate-update.sh --url https://…/msgate-0.0.15.tar.gz
```

Data defaults to `/var/lib/msgate`. Configure Exchange in the Web UI; env `MSGATE_EWS_*` is optional first-boot seed only.

### Database

- **Default:** SQLite (`MSGATE_DATA_DIR/msgate.db`).
- **Optional Postgres:** `pip install 'msgate[postgres]'` then set  
  `MSGATE_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/msgate` in `msgate.env`.

Queue / blast knobs (`MSGATE_QUEUE_*`, circuit breaker) are documented in `Private-Docs/AI-14.md` and commented in `msgate.env.example` (restart required; not in Web UI yet).

### Uninstall

```bash
sudo /opt/msgate/uninstall.sh          # stop service, remove unit; keep files
sudo /opt/msgate/uninstall.sh --purge  # also delete install dir, data, user
```

`apt remove msgate` is **not** available yet (no `.deb`). Only one install prefix is supported (`/opt/msgate`); `install.sh` upgrades in place and recreates the venv.

## EWS URL

Pattern:

```text
https://<your-exchange-host>/EWS/Exchange.asmx
```

`<your-exchange-host>` is typically your OWA / Client Access hostname. Ask your Exchange admin for the EWS endpoint if unsure. Quick reachability check:

```bash
curl -k -I "https://<host>/EWS/Exchange.asmx"
```

Ship no site-specific hosts or credentials in config examples — use placeholders (`mail.example.com`, `DOMAIN\svc.msgate`).

## Docs

- Public (GitHub Pages): [`docs/`](docs/) → [msgate.github.io/msgate](https://msgate.github.io/msgate/)
- Internal phase notes: `Private-Docs/AI-*.md`
- In-app: sidebar **Help ↗** (`MSGATE_HELP_URL`)
