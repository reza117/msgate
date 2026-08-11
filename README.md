# msgate

SMTP gateway for Exchange Web Services (EWS). Clients (Zabbix, scripts, etc.) submit mail over SMTP; msgate delivers via Exchange.

## Install options

| Scenario | Section |
|---|---|
| Production server (recommended) | [Production install (systemd)](#production-install-systemd) |
| Docker | [Docker](#docker-optional) |
| Local development / contributing | [Dev setup](#dev-setup) |

---

## Production install (systemd)

### Step 1 — Download the latest release

Go to the [releases page](https://github.com/reza117/msgate/releases/latest), note the tag (e.g. `v0.0.16`), then run on your server:

```bash
TAG=v0.0.16   # replace with the tag you see on the releases page

wget -O "msgate-${TAG}.zip" \
  "https://github.com/reza117/msgate/archive/refs/tags/${TAG}.zip"
unzip "msgate-${TAG}.zip"
cd "msgate-${TAG#v}/"
```

### Step 2 — Install

```bash
sudo ./install.sh
sudo systemctl start msgate
```

`install.sh` creates `/opt/msgate`, sets up a Python venv, installs the service unit, and starts msgate on boot.

### Step 3 — Configure

Open `http://<server-ip>:8080/` — set the admin password, then **Settings → Exchange**.

### Upgrade (keep data)

```bash
sudo /opt/msgate/msgate-update.sh          # pulls latest from GitHub
sudo /opt/msgate/msgate-update.sh --local  # already-unpacked tree
sudo /opt/msgate/msgate-update.sh --url "https://github.com/reza117/msgate/archive/refs/tags/${TAG}.zip"
```

DB and `msgate.env` are preserved across upgrades.

### Uninstall

```bash
sudo /opt/msgate/uninstall.sh          # stop service, remove unit; keep files
sudo /opt/msgate/uninstall.sh --purge  # also delete install dir, data, user
```

### Database

- **Default:** SQLite (`/var/lib/msgate/msgate.db`) — no setup needed.
- **Optional Postgres:** `pip install 'msgate[postgres]'` then set  
  `MSGATE_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/msgate` in `msgate.env`.

---

## Docker (optional)

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Open http://127.0.0.1:8080/ — same first-login flow as production.  
Data persists in the `msgate-data` volume.

Build image only:

```bash
docker build -f docker/Dockerfile -t msgate:local .
```

---

## Dev setup

For contributors or local testing only. Requires the source tree (clone or extracted zip).

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/msgate serve --api-host 127.0.0.1 --api-port 8080
```

Open http://127.0.0.1:8080/ — set the admin password, then **Settings → Exchange**.

---

## EWS URL

Pattern:

```text
https://<your-exchange-host>/EWS/Exchange.asmx
```

`<your-exchange-host>` is typically your OWA / Client Access hostname. Ask your Exchange admin if unsure. Quick reachability check:

```bash
curl -k -I "https://<host>/EWS/Exchange.asmx"
```

## Docs

- Public (GitHub Pages): [`docs/`](docs/) → [msgate.github.io/msgate](https://msgate.github.io/msgate/)
- In-app: sidebar **Help ↗** (`MSGATE_HELP_URL`)
