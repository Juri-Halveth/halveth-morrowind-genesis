#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${VEYRA_TEST_LUA:?Set VEYRA_TEST_LUA to an ordinary Lua5.1 executable}"
"$VEYRA_TEST_LUA" "$here/check-audio.lua" "$here/mod/scripts/veyra/spatial_audio.lua"
