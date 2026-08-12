---
title: Install
---

# Install & first login

## Requirements

- **Python 3.11+** for systemd install (`install.sh` creates a venv under `/opt/msgate`)
- Ubuntu 20.04: install `python3.11` from [deadsnakes](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) first

## Production (systemd)

Download the [latest release](https://github.com/reza117/msgate/releases/latest), extract, then:

```bash
sudo env PYTHON=python3.11 ./install.sh   # Ubuntu 20.04
# or: sudo ./install.sh                     # when python3 is already 3.11+
sudo systemctl start msgate
```

Data defaults to `/var/lib/msgate`. Configure Exchange in the Web UI.

## First login

1. Open the UI (e.g. `http://HOST:8080/`).
2. Create the administrator password (`admin`).
3. **Settings** → Exchange (EWS URL + credentials).
4. For Zabbix on the same host, allow `127.0.0.1` in SMTP IP allowlist; Media Type auth can be **None** if credentials live in msgate.

## Upgrade

```bash
sudo /opt/msgate/msgate-update.sh          # fetch latest GitHub release + install
sudo /opt/msgate/msgate-update.sh --local  # offline: use this unpacked tree only
```

Keeps data + `msgate.env`. Set `MSGATE_GITHUB_REPO=owner/repo` if not `reza117/msgate`.
