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

**Requirements:** Linux with **Python 3.11+** (Ubuntu 22.04+ includes it; Ubuntu 20.04 needs an extra package — see below).

### Step 0 — Python 3.11 (Ubuntu 20.04 only)

Skip this if `python3.11 --version` already works.

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv
python3.11 --version
```

This installs Python 3.11 **alongside** system Python 3.8 — it does not replace it (safe for Zabbix and other services).

### Step 1 — Download the latest release

Latest release page: [github.com/reza117/msgate/releases/latest](https://github.com/reza117/msgate/releases/latest)

Resolve the tag automatically (no hardcoded version):

```bash
TAG=$(wget -qO- --header="Accept: application/vnd.github+json" \
  "https://api.github.com/repos/reza117/msgate/releases/latest" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])")

echo "Downloading ${TAG}..."
wget -O "msgate-${TAG}.zip" \
  "https://github.com/reza117/msgate/archive/refs/tags/${TAG}.zip"
unzip "msgate-${TAG}.zip"
cd "msgate-${TAG#v}/"
```

Or pick a specific tag manually from the [releases page](https://github.com/reza117/msgate/releases/latest) and set `TAG=v0.0.20` before the `wget` line.

### Step 2 — Install

`install.sh` creates `/opt/msgate`, a Python venv, and the systemd unit.  
On Ubuntu 20.04, pass Python explicitly (`sudo` does not keep `PYTHON=` from the shell):

```bash
sudo env PYTHON=python3.11 ./install.sh
```

On hosts where `python3` is already 3.11+:

```bash
sudo ./install.sh
```

```bash
sudo systemctl start msgate
```

### Step 3 — Configure

Open `http://<server-ip>:8080/` — set the admin password, then **Settings → Exchange**.

**Behind a reverse proxy** (e.g. `https://host/msgate/` → port 8080), set in `/opt/msgate/msgate.env`:

```bash
MSGATE_ROOT_PATH=/msgate
```

Then `sudo systemctl restart msgate`. All UI links and API calls will use the `/msgate` prefix.

### Upgrade (keep data)

```bash
sudo /opt/msgate/msgate-update.sh          # pulls latest from GitHub
sudo /opt/msgate/msgate-update.sh --local  # already-unpacked tree
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

For contributors or local testing only. Requires the source tree (clone or extracted zip) and **Python 3.11+**.

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

- Public docs: [`docs/`](docs/) on GitHub → [github.com/reza117/msgate/tree/main/docs](https://github.com/reza117/msgate/tree/main/docs)
- In-app: sidebar **Help ↗** → `/ui/help` (works behind proxy subpath)
