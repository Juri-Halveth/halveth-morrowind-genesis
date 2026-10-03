#!/usr/bin/env bash
set -euo pipefail
candidate_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lua_binary="${VEYRA_TEST_LUA:-lua}"
"$lua_binary" "$candidate_root/check-hud.lua" "$candidate_root/mod/scripts/veyra/hud.lua"
