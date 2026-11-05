#!/usr/bin/env bash
# MIT. Controller for one explicitly selected, isolated OpenMW profile.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
python_bin() {
 if [[ -n ${WORKSHOP_PYTHON:-} ]]; then printf '%s\n' "$WORKSHOP_PYTHON"; return; fi
 local p
 for p in python3 python; do if command -v "$p" >/dev/null 2>&1; then command -v "$p"; return; fi; done
 fail 'Python 3.10+ is required; set WORKSHOP_PYTHON to its executable.'
}
usage() {
 cat <<'USAGE'
Usage: workshop.sh check | plan PROFILE | play PROFILE [SAVE]
  check         Run the pure rule model tests; no engine is started.
  plan PROFILE  Inspect a local isolated profile before playing.
  play PROFILE  Load play.cfg using the selected runtime, restoring its
                previous openmw.cfg afterwards. SAVE is optional and explicit.
PROFILE contains play.cfg, openmw.cfg and settings.cfg. Without WORKSHOP_ENGINE,
runtime/openmw.exe (or runtime/openmw) is selected below PROFILE.
A PROFILE/play.lock directory prevents concurrent use.
Set WORKSHOP_ENGINE only when testing or explicitly choosing another engine.
USAGE
}
command=${1:-help}
case "$command" in
 check)
  [[ $# -eq 1 ]] || fail 'check takes no further arguments'
  (cd -- "$ROOT/rules" && "$(python_bin)" check_policy.py)
  ;;
 plan|play)
  [[ $# -ge 2 && $# -le 3 ]] || fail 'Provide PROFILE and optionally one SAVE'
  [[ "$command" != plan || $# -eq 2 ]] || fail 'plan takes only PROFILE'
  [[ -d "$2" ]] || fail 'Profile directory is missing'
  profile=$(cd -- "$2" && pwd -P)
  [[ -f "$profile/openmw.cfg" && -f "$profile/play.cfg" && -f "$profile/settings.cfg" ]] || fail 'Profile requires openmw.cfg, play.cfg and settings.cfg'
  [[ ! -L "$profile/openmw.cfg" && ! -L "$profile/play.cfg" ]] || fail 'Configuration symlinks require a separate profile'
  # The playable configuration must omit the automated test harness.
  if grep -Eiq '^[[:space:]]*(content[[:space:]]*=[[:space:]]*([^#]*probe[^#]*|world-test\.omwscripts)|script-run[[:space:]]*=|skip-menu[[:space:]]*=[[:space:]]*(true|1))' "$profile/play.cfg"; then
   fail 'play.cfg contains an automated probe/startup command; use an ordinary playable configuration'
  fi
  engine=${WORKSHOP_ENGINE:-}
  if [[ -z "$engine" ]]; then
   if [[ -f "$profile/runtime/openmw.exe" ]]; then engine="$profile/runtime/openmw.exe"; else engine="$profile/runtime/openmw"; fi
  fi
  [[ -f "$engine" && -x "$engine" ]] || fail 'Selected OpenMW executable is missing or not executable'
  engine=$(cd -- "$(dirname -- "$engine")" && pwd -P)/$(basename -- "$engine")
  engine_directory=$(dirname -- "$engine")
  [[ $# -lt 3 || -f "$3" ]] || fail 'Explicit SAVE file does not exist'
  if [[ "$command" == plan ]]; then
   printf 'Profile ready: %s\nEngine: %s\nConfig mode: play.cfg\nSave choice: explicit or engine menu\n' "$profile" "$engine"
   exit 0
  fi
  lock="$profile/play.lock"
  mkdir -- "$lock" 2>/dev/null || fail 'Profile is running or a stale lock needs manual review'
  backup_ready=0
  child=''
  cleanup() {
   local result=$?
   trap - EXIT
   if [[ "$backup_ready" == 1 ]]; then
    if ! cp -- "$lock/previous.cfg" "$profile/openmw.cfg"; then
     printf 'ERROR: restore failed; preserved backup: %s\n' "$lock/previous.cfg" >&2
     return 74
    fi
   fi
   rm -f -- "$profile/openmw.cfg.next.$$" "$lock/pid" "$lock/previous.cfg"
   rmdir -- "$lock" || return 74
   return "$result"
  }
  interrupt() {
   trap - INT TERM HUP
   if [[ -n "$child" ]] && kill -0 "$child" 2>/dev/null; then
    kill -TERM "$child" 2>/dev/null || true
    wait "$child" 2>/dev/null || true
   fi
   exit 130
  }
  trap cleanup EXIT
  trap interrupt INT TERM HUP
  printf '%s\n' "$$" > "$lock/pid"
  cp -- "$profile/openmw.cfg" "$lock/previous.cfg"
  backup_ready=1
  cp -- "$profile/play.cfg" "$profile/openmw.cfg.next.$$"
  mv -f -- "$profile/openmw.cfg.next.$$" "$profile/openmw.cfg"
  selected_profile=$profile
  if [[ "$engine" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then selected_profile=$(cygpath -w "$selected_profile"); fi
  args=(--replace config --config "$selected_profile" --no-grab)
  if [[ $# -eq 3 ]]; then
   save_file=$(cd -- "$(dirname -- "$3")" && pwd -P)/$(basename -- "$3")
   if [[ "$engine" == *.exe ]] && command -v cygpath >/dev/null 2>&1; then save_file=$(cygpath -w "$save_file"); fi
   args+=(--load-savegame "$save_file")
  fi
  cd -- "$engine_directory"
  "$engine" "${args[@]}" &
  child=$!
  wait "$child"
  ;;
 help|--help|-h) usage ;;
 *) usage >&2; exit 2 ;;
esac
