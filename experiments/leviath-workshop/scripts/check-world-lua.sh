#!/usr/bin/env bash
# MIT. Parse the exact selected own-module roots; no engine or module execution.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
lua=${VEYRA_TEST_LUA:-lua5.1}
count=0
roots=(gameplay/mod presentation/mod presentation/spatial-audio/mod
       gameplay/portal/mod gameplay/construction/mod gameplay/townlife/mod
       gameplay/panels/mod presentation/hud014/mod prototypes/wildlife-source-only/mod)
for folder in "${roots[@]}"; do
 [[ -d "$ROOT/$folder" ]] || { printf 'Missing own module root: %s\n' "$folder" >&2;exit 2; }
 while IFS= read -r -d '' source; do
  if [[ "$lua" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then source=$(cygpath -w "$source");fi
  SOURCE_TO_CHECK="$source" "$lua" -e 'assert(loadfile(os.getenv("SOURCE_TO_CHECK")))'
  count=$((count+1))
 done < <(find "$ROOT/$folder" -type f -name '*.lua' -print0)
done
printf 'OWN_WORLD_LUA_SYNTAX_PASS files=%s engine=NOT_STARTED\n' "$count"
