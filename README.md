# msgate

SMTP gateway for Exchange Web Services (EWS). Clients (Zabbix, scripts, etc.) submit mail over SMTP; msgate delivers via Exchange.

## Quick start (dev)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/msgate serve --api-host 127.0.0.1 --api-port 8080
```

Open http://127.0.0.1:8080/ — set the admin password, then **Settings** → Exchange.

## Docker (optional)

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Open http://127.0.0.1:8080/ — same first-login flow as dev.  
Data persists in the `msgate-data` volume. Optional EWS seed via env in `docker/docker-compose.yml`.

Build image only:

```bash
docker build -f docker/Dockerfile -t msgate:local .
```

## Production install (systemd)

### Download latest release

Latest release: [github.com/reza117/msgate/releases/latest](https://github.com/reza117/msgate/releases/latest)

**Step 1 — Set the version tag**

Go to the [releases page](https://github.com/reza117/msgate/releases/latest), note the tag (e.g. `v0.0.16`), then:

```bash
TAG=v0.0.16   # replace with the latest tag
```

**Step 2 — Download and extract**

```bash
wget -O msgate-latest.zip \
  "https://github.com/reza117/msgate/archive/refs/tags/${TAG}.zip"
unzip msgate-latest.zip
cd "msgate-${TAG#v}/"
```

**Step 3 — Install**

```bash
sudo ./install.sh
sudo systemctl start msgate
```

Open http://&lt;server-ip&gt;:8080/ — set the admin password, then **Settings → Exchange**.

From an already-extracted tree, skip steps 1–2 and run `sudo ./install.sh` directly.

### Upgrade (keep data)

```bash
# On the server (keeps DB + msgate.env):
sudo /opt/msgate/msgate-update.sh
# same as:
sudo /opt/msgate/msgate-update.sh --latest
```

Offline / already unpacked:

```bash
sudo ./msgate-update.sh --local
sudo ./msgate-update.sh --url "https://github.com/reza117/msgate/archive/refs/tags/${TAG}.zip"
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
- In-app: sidebar **Help ↗** (`MSGATE_HELP_URL`)
