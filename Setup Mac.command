#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
trap 'echo "Setup failed. Read the error above, then press Return."; read -r _' ERR
if [ "$(uname -s)" != Darwin ]; then
    echo "Use Setup CHRONO ARENA.cmd on Windows."
    exit 1
fi
if [ "$(sw_vers -productVersion | cut -d. -f1)" -lt 13 ]; then
    echo "macOS 13 Ventura or newer is required by the bundled OpenCV version."
    echo "Press Return to close."
    read -r _
    exit 1
fi
if ! command -v python3.11 >/dev/null 2>&1; then
    echo "Install Python 3.11 for macOS from https://www.python.org/downloads/release/python-3119/"
    echo "Then run this setup again. Press Return to close."
    read -r _
    exit 1
fi
python3.11 -c 'import sys; assert sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32, "Python 3.11 64-bit required"'
# A Windows .venv cannot be reused on macOS. Keep Mac dependencies separate.
if [ ! -x .venv-mac/bin/python ]; then
    python3.11 -m venv .venv-mac
fi
.venv-mac/bin/python -m pip install --upgrade pip
.venv-mac/bin/python -m pip install -r requirements.txt
.venv-mac/bin/python scripts/download_models.py
.venv-mac/bin/python -m pip check
chmod +x "Setup Mac.command" "Launch Mac.command" "Launch Demo Mac.command"
echo "Ready! Run Launch Mac.command for webcam play or Launch Demo Mac.command."
echo "Allow Terminal camera access when macOS asks. Press Return to close."
read -r _
