#!/usr/bin/env bash
# msgate systemd installer
set -euo pipefail

INSTALL_DIR="${MSGATE_INSTALL_DIR:-/opt/msgate}"
DATA_DIR="${MSGATE_DATA_DIR:-/var/lib/msgate}"
SERVICE_USER="${MSGATE_USER:-msgate}"
PYTHON="${PYTHON:-python3}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

echo "==> Installing msgate to ${INSTALL_DIR}"

if ! id "${SERVICE_USER}" &>/dev/null; then
  useradd --system --home-dir "${DATA_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

mkdir -p "${INSTALL_DIR}" "${DATA_DIR}/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rsync -a --exclude .venv --exclude .git --exclude data \
  "${SCRIPT_DIR}/" "${INSTALL_DIR}/"

cd "${INSTALL_DIR}"
if [[ ! -d ".venv" ]]; then
  ${PYTHON} -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install .

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"

cat >/etc/systemd/system/msgate.service <<EOF
[Unit]
Description=msgate SMTP gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment=MSGATE_DATA_DIR=${DATA_DIR}
EnvironmentFile=-${INSTALL_DIR}/msgate.env
ExecStart=${INSTALL_DIR}/.venv/bin/msgate serve --api-host 127.0.0.1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable msgate.service

echo "==> Installed. Copy ${INSTALL_DIR}/msgate.env.example to msgate.env and run:"
echo "    systemctl start msgate"
