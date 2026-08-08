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

Data defaults to `/var/lib/msgate`. Configure Exchange in the Web UI; env `MSGATE_EWS_*` is optional first-boot seed only.

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

See `Private-Docs/AI-*.md` and the Help link in the UI.
