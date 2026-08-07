#!/usr/bin/env bash
# Build single-file binary with PyInstaller (optional Phase 5 deliverable).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install pyinstaller
pyinstaller --onefile --name msgate \
  --collect-all exchangelib \
  --hidden-import msgate.ui.render \
  src/msgate/__main__.py
echo "Binary: dist/msgate"
