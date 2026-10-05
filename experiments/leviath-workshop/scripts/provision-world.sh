#!/usr/bin/env bash
# MIT. Provision owned profile copies; this command never launches OpenMW.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
python=${WORKSHOP_PYTHON:-}
if [[ -z "$python" ]]; then
 for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then python=$(command -v "$candidate");break;fi
 done
fi
[[ -n "$python" ]] || { printf 'Python3.10+ required; set WORKSHOP_PYTHON\n' >&2;exit 2; }
args=("$@")
if [[ "$python" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then
 for ((index=0;index<${#args[@]};index++)); do
  case "${args[index]}" in
   --base-profile|--engine|--destination)
    ((index+1<${#args[@]})) || { printf 'Missing path argument\n' >&2;exit 2; }
    args[index+1]=$(cygpath -m -- "${args[index+1]}")
    ;;
  esac
 done
fi
"$python" "$here/provision-world.py" "${args[@]}"
