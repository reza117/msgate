#!/usr/bin/env bash
# msgate systemd uninstaller
#
# Default: stop + disable service, remove unit file. Keeps /opt/msgate and data.
#   sudo ./uninstall.sh
#
# Full wipe (code, data, system user):
#   sudo ./uninstall.sh --purge
#
set -euo pipefail

INSTALL_DIR="${MSGATE_INSTALL_DIR:-/opt/msgate}"
DATA_DIR="${MSGATE_DATA_DIR:-/var/lib/msgate}"
SERVICE_USER="${MSGATE_USER:-msgate}"
UNIT_FILE="/etc/systemd/system/msgate.service"
PURGE=0

for arg in "$@"; do
  case "${arg}" in
    --purge) PURGE=1 ;;
    -h|--help)
      echo "Usage: sudo $0 [--purge]"
      echo "  (default) stop service, disable unit, remove unit file"
      echo "  --purge   also delete ${INSTALL_DIR}, ${DATA_DIR}, and user ${SERVICE_USER}"
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      echo "Usage: sudo $0 [--purge]" >&2
      exit 1
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

echo "==> Stopping msgate"
systemctl stop msgate.service 2>/dev/null || true
systemctl disable msgate.service 2>/dev/null || true

if [[ -f "${UNIT_FILE}" ]]; then
  rm -f "${UNIT_FILE}"
  systemctl daemon-reload
  systemctl reset-failed msgate.service 2>/dev/null || true
  echo "==> Removed ${UNIT_FILE}"
else
  echo "==> No unit file at ${UNIT_FILE}"
fi

if [[ "${PURGE}" -eq 1 ]]; then
  echo "==> Purging install and data"
  rm -rf "${INSTALL_DIR}"
  rm -rf "${DATA_DIR}"
  # Legacy path from early installs that wrote under WorkingDirectory/data
  if [[ -d /opt/msgate/data && "${INSTALL_DIR}" != /opt/msgate ]]; then
    rm -rf /opt/msgate/data
  fi
  if id "${SERVICE_USER}" &>/dev/null; then
    userdel "${SERVICE_USER}" 2>/dev/null || true
    echo "==> Removed user ${SERVICE_USER}"
  fi
  echo "==> Purge complete"
else
  echo "==> Service removed. Install tree and data kept:"
  echo "    ${INSTALL_DIR}"
  echo "    ${DATA_DIR}"
  echo "    Re-run with --purge to delete those and the ${SERVICE_USER} user."
fi
echo "    (apt remove msgate is not available until a .deb package is published.)"
