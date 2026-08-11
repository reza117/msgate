---
title: Install
---

# Install & first login

## Production (systemd)

```bash
sudo ./install.sh
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

Keeps data + `msgate.env`. Release must include a `msgate-*.tar.gz` asset.  
Set `MSGATE_GITHUB_REPO=owner/repo` if not `msgate/msgate`. Do not use `uninstall.sh --purge` for upgrades.
