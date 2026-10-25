#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ ! -x .venv-mac/bin/python ]; then
    echo "Run bash 'Setup Mac.command' in this folder first. Press Return to close."
    read -r _
    exit 1
fi
trap 'echo "Game stopped with an error. Press Return to close."; read -r _' ERR
.venv-mac/bin/python main.py --windowed "$@"
