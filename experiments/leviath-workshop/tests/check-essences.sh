#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
script="$ROOT/tools/essences.sh"
mkdir -p -- "$ROOT/.local/test-work"
testroot=$(mktemp -d -- "$ROOT/.local/test-work/essence-check.XXXXXXXX")
testroot=$(realpath -- "$testroot")
[[ "$testroot" == "$ROOT/.local/test-work/essence-check."* ]]
trap '[[ "$testroot" == "$ROOT/.local/test-work/essence-check."* ]] && rm -rf -- "$testroot"' EXIT
mkdir -- "$testroot/source" "$testroot/temp-work"
printf '%s\n' 'preserved original bytes' > "$testroot/source/file with spaces.txt"
bash "$script" snapshot "$testroot/source" "$testroot/before.sha256"
bash "$script" verify "$testroot/source" "$testroot/before.sha256"
if bash "$script" snapshot "$testroot/source" "$testroot/source/self.sha256"; then exit 1; fi
bash "$script" once "$testroot/temp-work" bash -c 'printf "%s\n" marker > "$VEYRA_ONCE_DIR/marker"; test -s "$VEYRA_ONCE_DIR/marker"'
[[ -z $(find "$testroot/temp-work" -mindepth 1 -print -quit) ]]
if bash "$script" once "$testroot/temp-work" bash -c 'printf marker > "$VEYRA_ONCE_DIR/marker"; exit 17'; then exit 1; fi
[[ -z $(find "$testroot/temp-work" -mindepth 1 -print -quit) ]]
printf '%s\n' 'modified candidate bytes' > "$testroot/source/file with spaces.txt"
bash "$script" snapshot "$testroot/source" "$testroot/after.sha256"
if bash "$script" compare "$testroot/before.sha256" "$testroot/after.sha256" > "$testroot/diff.txt"; then exit 1; fi
grep -q 'file with spaces.txt' "$testroot/diff.txt"
bash "$script" pin-version 'ORACLE 1' printf 'ORACLE 1\nextra diagnostic\n'
if bash "$script" pin-version 'ORACLE 1' printf 'ORACLE 2\n'; then exit 1; fi
printf '%s\n' 'ESSENCE_CHECK_PASS: snapshot, path guard, cleanup after success/failure, retained before/after diff'
