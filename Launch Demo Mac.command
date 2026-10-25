#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
bash "Launch Mac.command" --demo "$@"
