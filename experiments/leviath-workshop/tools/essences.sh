#!/usr/bin/env bash
# Veyra code essences, MIT. Own implementation of observed operating patterns.
# Original trash sources are private, unexecuted, and not copied into this file.
# Requires Git Bash tools: realpath, mktemp, find, sort, sha256sum, cmp, diff.
set -euo pipefail
umask 077

fail() { printf '%s\n' "$*" >&2; return 1; }

# Temporary work stays inside one explicitly chosen directory. One shell owns
# creation, absolute-path verification, use and removal; no cross-shell deletion.
with_temp() (
    local base=${1:?work directory}; shift
    [[ $# -gt 0 ]] || { fail 'Command required'; exit 2; }
    mkdir -p -- "$base"
    base=$(realpath -- "$base")
    [[ "$base" != / && "$base" != /c && "$base" != /c/Users ]] || { fail 'Work directory too broad'; exit 2; }
    local temp
    temp=$(mktemp -d -- "$base/veyra-once.XXXXXXXX")
    temp=$(realpath -- "$temp")
    [[ "$temp" == "$base"/veyra-once.* ]] || { fail 'Temporary path escaped work root'; exit 2; }
    trap '[[ "$temp" == "$base"/veyra-once.* ]] && rm -rf -- "$temp"' EXIT
    export VEYRA_ONCE_DIR="$temp"
    "$@"
)

# Exact byte snapshots of caller-selected regular files; links are not followed.
snapshot() {
    local source=${1:?source directory} output=${2:?new external manifest}
    source=$(realpath -- "$source")
    output=$(realpath -m -- "$output")
    [[ -d "$source" && ! -e "$output" && "$output" != "$source"/* ]] || { fail 'Invalid snapshot paths'; return 2; }
    (cd -- "$source"; find . -type f -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum --) > "$output"
}

# Forward check asks whether the observed files match an earlier byte snapshot.
verify() {
    local source=${1:?source directory} manifest=${2:?manifest}
    manifest=$(realpath -- "$manifest")
    (cd -- "$source"; sha256sum --check --strict -- "$manifest")
}

# Reverse review retains both immutable manifests; a difference is an observation,
# not automatic causality. The command exits 1 when changes are found.
compare() { diff -u -- "${1:?before manifest}" "${2:?after manifest}"; }

# Bound tool versions before the same oracle is used for a build or comparison.
# The caller supplies an exact expected first line, not an inferred version label.
pin_version() {
    local expected=${1:?expected version line}; shift
    [[ $# -gt 0 ]] || { fail 'Version command required'; return 2; }
    local observed
    observed=$("$@")
    observed=${observed%%$'\n'*}
    [[ "$observed" == "$expected" ]] || { fail 'Tool version does not match the bound oracle'; return 2; }
    printf '%s\n' "$observed"
}

# Fail-fast pipeline prevents a dependent build step after a failed check.
pipeline() {
    local root=${1:?project directory}; shift
    [[ -d "$root" && $# -gt 0 ]] || { fail 'Project and saved script required'; return 2; }
    (cd -- "$root"; bash -- "$@")
}

case "${1:-help}" in
    once) shift; with_temp "$@" ;;
    snapshot) shift; snapshot "$@" ;;
    verify) shift; verify "$@" ;;
    compare) shift; compare "$@" ;;
    pin-version) shift; pin_version "$@" ;;
    pipeline) shift; pipeline "$@" ;;
    help) printf '%s\n' 'once WORK_DIRECTORY COMMAND [ARGS]' 'snapshot SOURCE NEW_EXTERNAL_MANIFEST' 'verify SOURCE MANIFEST' 'compare BEFORE_MANIFEST AFTER_MANIFEST' 'pin-version EXPECTED_FIRST_LINE COMMAND [ARGS]' 'pipeline PROJECT SAVED_BASH_SCRIPT [ARGS]' ;;
    *) fail 'Unknown action'; exit 2 ;;
esac
