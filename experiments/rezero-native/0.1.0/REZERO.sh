#!/usr/bin/env bash
# MIT. Own-source asset check and local licensed-record build through Git Bash.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mode=${1:-check};(( $# == 0 )) || shift
case "$mode" in
 check) (( $# == 0 ));(cd -- "$here" && sha256sum --check --strict --quiet PAYLOAD.sha256);printf 'REZERO own assets match.\n' ;;
 build)
  (cd -- "$here" && sha256sum --check --strict --quiet PAYLOAD.sha256)
  command=${REZERO_PYTHON:-python}
  PYTHONDONTWRITEBYTECODE=1 "$command" -B "$here/tools/build-local.py" "$@"
  ;;
 *) printf 'REZERO.sh check | build --config SOURCE_OPENMW_CFG --output NEW_DIRECTORY\n' >&2;exit 2 ;;
esac
