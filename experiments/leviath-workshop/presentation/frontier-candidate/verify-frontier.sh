#!/usr/bin/env bash
# MIT. Run through actual Git Bash on Windows with PYTHON bound to Python3.14.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  printf '%s\n' 'Usage: PYTHON=<python.exe> bash verify-frontier.sh <bound-openmw.cfg> <OpenMW0.51-esmtool.exe>' >&2
  exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${PYTHON:-python}" "$script_dir/verify-frontier.py" --base-config "$1" --esmtool "$2"
