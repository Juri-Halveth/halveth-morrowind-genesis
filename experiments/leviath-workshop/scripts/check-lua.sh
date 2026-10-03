#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
lua=${VEYRA_TEST_LUA:-lua5.1}
count=0
while IFS= read -r -d '' source; do
 if [[ "$lua" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then
  source=$(cygpath -w "$source")
 fi
 SOURCE_TO_CHECK="$source" "$lua" -e 'assert(loadfile(os.getenv("SOURCE_TO_CHECK")))'
 count=$((count+1))
done < <(find "$ROOT/gameplay/mod" "$ROOT/presentation/mod" -type f -name '*.lua' -print0)
printf 'LUA_SOURCE_SYNTAX_PASS files=%s engine=NOT_STARTED\n' "$count"
