#!/usr/bin/env bash
# msgate systemd installer — single install prefix only (/opt/msgate by default).
#
# Upgrade in place: sudo ./install.sh
# Force replace if something looks wrong: sudo ./install.sh --force
#
set -euo pipefail

INSTALL_DIR="${MSGATE_INSTALL_DIR:-/opt/msgate}"
DATA_DIR="${MSGATE_DATA_DIR:-/var/lib/msgate}"
SERVICE_USER="${MSGATE_USER:-msgate}"
PYTHON="${PYTHON:-}"
UNIT_FILE="/etc/systemd/system/msgate.service"
FORCE=0

python_ok() {
  command -v "$1" &>/dev/null && "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

resolve_python() {
  if [[ -n "${PYTHON}" ]]; then
    python_ok "${PYTHON}" && return 0
    echo "ERROR: ${PYTHON} is missing or older than Python 3.11." >&2
    return 1
  fi
  local candidate
  for candidate in python3.12 python3.11 python3; do
    if python_ok "${candidate}"; then
      PYTHON="${candidate}"
      return 0
    fi
  done
  echo "ERROR: Python 3.11+ required (found: $(python3 --version 2>/dev/null || echo none))." >&2
  echo "       Ubuntu 20.04: install python3.11, then run:" >&2
  echo "         sudo env PYTHON=python3.11 $0" >&2
  return 1
}

for arg in "$@"; do
  case "${arg}" in
    --force) FORCE=1 ;;
    -h|--help)
      echo "Usage: sudo $0 [--force]"
      echo "  Installs/upgrades a single msgate at ${INSTALL_DIR}"
      echo "  --force  allow overwrite when an unexpected install is detected"
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

resolve_python || exit 1
echo "==> Using ${PYTHON} ($(${PYTHON} --version))"

# Refuse a second parallel install (different prefix while unit already exists).
if [[ -f "${UNIT_FILE}" ]]; then
  existing_wd="$(systemctl show -p WorkingDirectory --value msgate.service 2>/dev/null || true)"
  existing_exec="$(systemctl show -p ExecStart --value msgate.service 2>/dev/null || true)"
  if [[ -n "${existing_wd}" && "${existing_wd}" != "${INSTALL_DIR}" && "${FORCE}" -ne 1 ]]; then
    echo "ERROR: msgate already installed at ${existing_wd}" >&2
    echo "       Refusing second install to ${INSTALL_DIR}." >&2
    echo "       Upgrade: cd ${existing_wd} && sudo ./install.sh" >&2
    echo "       Or remove first: sudo ${existing_wd}/uninstall.sh --purge" >&2
    echo "       Or: sudo $0 --force  (overwrites unit to ${INSTALL_DIR})" >&2
    exit 1
  fi
  if [[ -n "${existing_exec}" && "${existing_exec}" != *"${INSTALL_DIR}"* && "${FORCE}" -ne 1 ]]; then
    echo "ERROR: existing msgate.service does not point at ${INSTALL_DIR}" >&2
    echo "       Remove it first or re-run with --force." >&2
    exit 1
  fi
fi

if [[ -d "${INSTALL_DIR}" && ! -f "${INSTALL_DIR}/.msgate-install" && "${FORCE}" -ne 1 ]]; then
  if [[ -d "${INSTALL_DIR}/.venv" ]] || [[ -f "${INSTALL_DIR}/pyproject.toml" ]]; then
    : # prior install without marker — treat as upgrade
  elif [[ -n "$(ls -A "${INSTALL_DIR}" 2>/dev/null || true)" ]]; then
    echo "ERROR: ${INSTALL_DIR} exists and does not look like msgate." >&2
    echo "       Empty/move it, or use --force." >&2
    exit 1
  fi
fi

echo "==> Stopping any running msgate (upgrade-safe)"
systemctl stop msgate.service 2>/dev/null || true

echo "==> Installing msgate to ${INSTALL_DIR} (single instance)"

if ! id "${SERVICE_USER}" &>/dev/null; then
  useradd --system --home-dir "${DATA_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

mkdir -p "${INSTALL_DIR}" "${DATA_DIR}/logs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Do not install from inside an existing tree into a different path by accident.
if [[ "${SCRIPT_DIR}" != "${INSTALL_DIR}" ]] && [[ -f "${INSTALL_DIR}/.msgate-install" ]]; then
  echo "==> Replacing previous install at ${INSTALL_DIR}"
fi

rsync -a --delete \
  --exclude .venv --exclude .git --exclude data --exclude msgate.env \
  --exclude '*.db' --exclude tls_cache.json --exclude .secret_key \
  "${SCRIPT_DIR}/" "${INSTALL_DIR}/"

# Fresh venv each install/upgrade so pip packages cannot mix across versions.
rm -rf "${INSTALL_DIR}/.venv"
cd "${INSTALL_DIR}"
${PYTHON} -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install .

VERSION="$(.venv/bin/msgate --version 2>/dev/null | awk '{print $NF}' || echo unknown)"
printf 'version=%s\ninstall_dir=%s\ndata_dir=%s\ninstalled_at=%s\n' \
  "${VERSION}" "${INSTALL_DIR}" "${DATA_DIR}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"${INSTALL_DIR}/.msgate-install"

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
# Service user must read alembic.ini / alembic/ under the install tree.
chmod -R a+rX "${INSTALL_DIR}"
# Keep venv private-ish but executable for the service user
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/.venv"

# Do not put literal ${...} in comments inside an unquoted heredoc — bash expands them
# (e.g. "${}" caused "bad substitution" and aborted before writing the unit).
# Do not set MSGATE_API_HOST here: systemd Environment= overrides EnvironmentFile=.
# Bind address/port come only from msgate.env (see msgate.env.example).
cat >"${UNIT_FILE}" <<EOF
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
Environment=MSGATE_LOG_DIR=${DATA_DIR}/logs
EnvironmentFile=-${INSTALL_DIR}/msgate.env
ExecStart=${INSTALL_DIR}/.venv/bin/msgate serve
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "${INSTALL_DIR}/msgate.env" ]]; then
  cp "${INSTALL_DIR}/msgate.env.example" "${INSTALL_DIR}/msgate.env"
  echo "==> Created ${INSTALL_DIR}/msgate.env from example (API bind 0.0.0.0)"
fi

chmod +x "${INSTALL_DIR}/install.sh" "${INSTALL_DIR}/uninstall.sh" 2>/dev/null || true

# Previous failed installs may have left a masked unit.
systemctl unmask msgate.service 2>/dev/null || true
systemctl daemon-reload
systemctl enable --now msgate.service

echo "==> Installed msgate ${VERSION} at ${INSTALL_DIR} (only one systemd instance)."
echo "    Edit ${INSTALL_DIR}/msgate.env if needed, then: sudo systemctl restart msgate"
echo "    Open http://<host>:8080/"
echo ""

# Verify UI is up (API starts even without EWS).
ok=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS -m 2 "http://127.0.0.1:8080/healthz" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 1
done

if [[ "${ok}" -eq 1 ]]; then
  echo "==> healthz OK — UI should be at http://<host>:8080/"
else
  echo "==> WARNING: healthz not responding yet. Diagnostics:" >&2
  systemctl is-active msgate.service || true
  systemctl status msgate.service --no-pager -l | head -40 || true
  echo "---- recent journal ----" >&2
  journalctl -u msgate.service -n 40 --no-pager || true
  echo "Fix, then: sudo systemctl restart msgate" >&2
  exit 1
fi

echo ""
echo "    Remove:  sudo ${INSTALL_DIR}/uninstall.sh"
echo "    Purge:   sudo ${INSTALL_DIR}/uninstall.sh --purge"
echo "    Note:    apt remove msgate is not available (no .deb package yet)."
