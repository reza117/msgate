#!/usr/bin/env bash
# Upgrade an existing msgate install without wiping data / config.
#
# Keeps: MSGATE_DATA_DIR (DB, logs, secret), msgate.env
# Replaces: code + venv under MSGATE_INSTALL_DIR (via install.sh)
#
# Usage (as root):
#   sudo msgate-update.sh
#   sudo msgate-update.sh --latest
#       → fetch newest GitHub release tarball, then upgrade
#   sudo msgate-update.sh --local
#       → install from this script's directory (offline / already unpacked)
#   sudo msgate-update.sh /path/to/msgate-0.0.15.tar.gz
#   sudo msgate-update.sh /path/to/unpacked-msgate-dir
#   sudo msgate-update.sh --url https://…/msgate-0.0.15.tar.gz
#
# Repo: MSGATE_GITHUB_REPO (default: msgate/msgate)
#
set -euo pipefail

INSTALL_DIR="${MSGATE_INSTALL_DIR:-/opt/msgate}"
DATA_DIR="${MSGATE_DATA_DIR:-/var/lib/msgate}"
GITHUB_REPO="${MSGATE_GITHUB_REPO:-reza117/msgate}"
TMP_ROOT=""
MODE="" # latest | local | url | path
SOURCE=""
URL=""

cleanup() {
  if [[ -n "${TMP_ROOT}" && -d "${TMP_ROOT}" ]]; then
    rm -rf "${TMP_ROOT}"
  fi
}
trap cleanup EXIT

usage() {
  cat <<EOF
Usage: sudo $0 [OPTIONS] [SOURCE]

With no arguments (or --latest): download the newest GitHub release and upgrade.

Options:
  --latest           Fetch latest release asset from GitHub (default if no SOURCE)
  --local            Use the directory containing this script (no download)
  --url URL          Download a specific tarball URL
  --force            Pass --force to install.sh
  -h, --help         Show this help

SOURCE:
  DIR                Unpacked msgate tree (must contain install.sh)
  FILE.tar.gz        Local release tarball

Environment:
  MSGATE_GITHUB_REPO   owner/repo (default: ${GITHUB_REPO})
  MSGATE_INSTALL_DIR   install prefix (default: /opt/msgate)
  MSGATE_DATA_DIR      data dir (default: /var/lib/msgate)
  MSGATE_GITHUB_TOKEN  optional token for private/rate-limited API

Never deletes DB, logs, secrets, or msgate.env.
EOF
}

download() {
  local url="$1"
  local out="$2"
  local headers=()
  if [[ -n "${MSGATE_GITHUB_TOKEN:-}" ]]; then
    headers+=(-H "Authorization: Bearer ${MSGATE_GITHUB_TOKEN}")
  fi
  headers+=(-H "Accept: application/octet-stream")
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${headers[@]}" -L "${url}" -o "${out}"
  elif command -v wget >/dev/null 2>&1; then
    if [[ -n "${MSGATE_GITHUB_TOKEN:-}" ]]; then
      wget -q --header="Authorization: Bearer ${MSGATE_GITHUB_TOKEN}" -O "${out}" "${url}"
    else
      wget -q -O "${out}" "${url}"
    fi
  else
    echo "ERROR: need curl or wget" >&2
    exit 1
  fi
}

fetch_latest_asset_url() {
  local api="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"
  local headers=()
  if [[ -n "${MSGATE_GITHUB_TOKEN:-}" ]]; then
    headers+=(-H "Authorization: Bearer ${MSGATE_GITHUB_TOKEN}")
  fi
  headers+=(-H "Accept: application/vnd.github+json")
  local json
  if command -v curl >/dev/null 2>&1; then
    json="$(curl -fsSL "${headers[@]}" "${api}")"
  elif command -v wget >/dev/null 2>&1; then
    if [[ -n "${MSGATE_GITHUB_TOKEN:-}" ]]; then
      json="$(wget -qO- --header="Authorization: Bearer ${MSGATE_GITHUB_TOKEN}" \
        --header="Accept: application/vnd.github+json" "${api}")"
    else
      json="$(wget -qO- --header="Accept: application/vnd.github+json" "${api}")"
    fi
  else
    echo "ERROR: need curl or wget for --latest" >&2
    exit 1
  fi

  python3 - "${json}" <<'PY'
import json, os, sys
data = json.loads(sys.argv[1])
tag = data.get("tag_name") or ""
assets = data.get("assets") or []
candidates = []
for a in assets:
    name = (a.get("name") or "").lower()
    url = a.get("browser_download_url") or ""
    if not url:
        continue
    if name.endswith((".tar.gz", ".tgz", ".zip")) and "msgate" in name:
        candidates.append((0, name, url, tag))
    elif name.endswith((".tar.gz", ".tgz", ".zip")):
        candidates.append((1, name, url, tag))
if candidates:
    candidates.sort(key=lambda t: (t[0], t[1]))
    _name, url, tag = candidates[0][1], candidates[0][2], candidates[0][3]
    print(f"{tag}\t{url}")
    sys.exit(0)
if not tag:
    print("ERROR: latest release has no tag_name", file=sys.stderr)
    sys.exit(2)
repo = os.environ.get("MSGATE_GITHUB_REPO", "reza117/msgate")
url = f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
print(f"{tag}\t{url}")
PY
}

resolve_tree() {
  local src="$1"
  if [[ -d "${src}" ]]; then
    if [[ ! -f "${src}/install.sh" ]]; then
      echo "ERROR: ${src} has no install.sh (not a msgate release tree)" >&2
      exit 1
    fi
    printf '%s\n' "${src}"
    return
  fi
  if [[ -f "${src}" ]]; then
    case "${src}" in
      *.tar.gz|*.tgz)
        if [[ -z "${TMP_ROOT}" ]]; then
          TMP_ROOT="$(mktemp -d /tmp/msgate-update.XXXXXX)"
        fi
        local extract_dir="${TMP_ROOT}/extract"
        mkdir -p "${extract_dir}"
        echo "==> Extracting ${src}"
        tar -xzf "${src}" -C "${extract_dir}"
        local top
        top="$(find "${extract_dir}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
        if [[ -n "${top}" && -f "${top}/install.sh" ]]; then
          printf '%s\n' "${top}"
        elif [[ -f "${extract_dir}/install.sh" ]]; then
          printf '%s\n' "${extract_dir}"
        else
          echo "ERROR: tarball does not contain install.sh" >&2
          exit 1
        fi
        return
        ;;
      *.zip)
        if [[ -z "${TMP_ROOT}" ]]; then
          TMP_ROOT="$(mktemp -d /tmp/msgate-update.XXXXXX)"
        fi
        local extract_dir="${TMP_ROOT}/extract"
        mkdir -p "${extract_dir}"
        echo "==> Extracting ${src}"
        unzip -q "${src}" -d "${extract_dir}"
        local top
        top="$(find "${extract_dir}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
        if [[ -n "${top}" && -f "${top}/install.sh" ]]; then
          printf '%s\n' "${top}"
        elif [[ -f "${extract_dir}/install.sh" ]]; then
          printf '%s\n' "${extract_dir}"
        else
          echo "ERROR: zip does not contain install.sh" >&2
          exit 1
        fi
        return
        ;;
      *)
        echo "ERROR: unsupported file (want .tar.gz, .zip, or a directory): ${src}" >&2
        exit 1
        ;;
    esac
  fi
  echo "ERROR: source not found: ${src}" >&2
  exit 1
}

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --latest)
      MODE="latest"
      ;;
    --local)
      MODE="local"
      ;;
    --url)
      shift
      URL="${1:-}"
      if [[ -z "${URL}" ]]; then
        echo "ERROR: --url requires a URL" >&2
        exit 1
      fi
      MODE="url"
      ;;
    --force)
      export MSGATE_UPDATE_FORCE=1
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      SOURCE="$1"
      MODE="path"
      ;;
  esac
  shift || true
done

if [[ -z "${MODE}" ]]; then
  MODE="latest"
fi

case "${MODE}" in
  latest)
    echo "==> Looking up latest release for ${GITHUB_REPO}"
    meta="$(fetch_latest_asset_url)"
    tag="${meta%%$'\t'*}"
    URL="${meta#*$'\t'}"
    echo "    Tag: ${tag}"
    echo "    Asset: ${URL}"
    TMP_ROOT="$(mktemp -d /tmp/msgate-update.XXXXXX)"
    if [[ "${URL}" == *.zip ]]; then
      archive="${TMP_ROOT}/msgate-release.zip"
    else
      archive="${TMP_ROOT}/msgate-release.tar.gz"
    fi
    echo "==> Downloading"
    download "${URL}" "${archive}"
    TREE="$(resolve_tree "${archive}")"
    ;;
  url)
    TMP_ROOT="$(mktemp -d /tmp/msgate-update.XXXXXX)"
    if [[ "${URL}" == *.zip ]]; then
      archive="${TMP_ROOT}/msgate-release.zip"
    else
      archive="${TMP_ROOT}/msgate-release.tar.gz"
    fi
    echo "==> Downloading ${URL}"
    download "${URL}" "${archive}"
    TREE="$(resolve_tree "${archive}")"
    ;;
  local)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    TREE="$(resolve_tree "${SCRIPT_DIR}")"
    ;;
  path)
    TREE="$(resolve_tree "${SOURCE}")"
    ;;
  *)
    echo "ERROR: internal mode=${MODE}" >&2
    exit 1
    ;;
esac

if [[ ! -f "${TREE}/install.sh" ]]; then
  echo "ERROR: no install.sh in ${TREE}" >&2
  exit 1
fi

OLD_VER="unknown"
if [[ -x "${INSTALL_DIR}/.venv/bin/msgate" ]]; then
  OLD_VER="$("${INSTALL_DIR}/.venv/bin/msgate" --version 2>/dev/null || true)"
  OLD_VER="${OLD_VER:-unknown}"
fi

echo "==> Updating msgate at ${INSTALL_DIR}"
echo "    From tree: ${TREE}"
echo "    Previous:  ${OLD_VER}"
echo "    Data kept: ${DATA_DIR} (DB/logs/secrets) + ${INSTALL_DIR}/msgate.env"
echo

INSTALL_ARGS=()
if [[ "${MSGATE_UPDATE_FORCE:-0}" == "1" ]]; then
  INSTALL_ARGS+=(--force)
fi

( cd "${TREE}" && bash ./install.sh "${INSTALL_ARGS[@]+"${INSTALL_ARGS[@]}"}" )

NEW_VER="unknown"
if [[ -x "${INSTALL_DIR}/.venv/bin/msgate" ]]; then
  NEW_VER="$("${INSTALL_DIR}/.venv/bin/msgate" --version 2>/dev/null || true)"
  NEW_VER="${NEW_VER:-unknown}"
fi

echo
echo "==> Update finished: ${OLD_VER} → ${NEW_VER}"
echo "    Check: systemctl status msgate"
echo "    UI:    confirm version in the sidebar"
