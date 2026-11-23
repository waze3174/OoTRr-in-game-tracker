#!/usr/bin/env bash
# Builds the Linux folder: dist/OoTRr-in-game-tracker/ (OoTRr-in-game-tracker = the window, ootr-tracker = the command line).
# Run on Linux. Needs python3 (>= 3.11) with venv and tkinter (Debian/Ubuntu: sudo apt install python3-venv python3-tk).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="${OOTR_TRACKER_VENV:-$HOME/.cache/ootr-ingame-tracker/venv-linux}"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -q -c packaging/constraints.txt -r requirements.txt pyinstaller
"$VENV/bin/python" -c "import tkinter" || { echo "tkinter is missing: sudo apt install python3-tk"; exit 1; }
"$VENV/bin/python" -m PyInstaller --noconfirm --clean --distpath "$ROOT/dist" \
    --workpath "$ROOT/build/pyinstaller-linux" packaging/ootr_tracker.spec
cp README.md LICENSE THIRD_PARTY_NOTICES.md "$ROOT/dist/OoTRr-in-game-tracker/"
chmod +x "$ROOT/dist/OoTRr-in-game-tracker/OoTRr-in-game-tracker" "$ROOT/dist/OoTRr-in-game-tracker/ootr-tracker"
echo "Built: $ROOT/dist/OoTRr-in-game-tracker/OoTRr-in-game-tracker"
