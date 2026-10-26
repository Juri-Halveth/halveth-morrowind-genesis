#!/usr/bin/env bash
# MIT. Fetch one source-bound asset; never extract or execute it.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
manifest=${WORKSHOP_ASSET_MANIFEST:-$ROOT/scripts/asset-sources.tsv}
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
[[ -f "$manifest" ]] || fail 'Asset source manifest is missing'
if [[ ${1:-list} == list ]]; then
 [[ $# -le 1 ]] || fail 'list takes no other arguments'
 cat -- "$manifest"
 exit 0
fi
[[ $# -eq 3 && "$1" == fetch ]] || fail 'Usage: fetch-assets.sh list | fetch ID DESTINATION'
selected=''
while IFS=$'\t' read -r id hash url name license; do
 [[ "$id" == '#'* || -z "$id" ]] && continue
 if [[ "$id" == "$2" ]]; then
  [[ -z "$selected" ]] || fail 'Duplicate asset identifier in manifest'
  selected=$id; selected_hash=$hash; selected_url=$url; selected_name=$name; selected_license=$license
 fi
done < "$manifest"
[[ -n "$selected" ]] || fail 'Unknown asset identifier'
[[ "$selected_hash" =~ ^[0-9a-f]{64}$ && "$selected_url" == https://* ]] || fail 'Manifest requires HTTPS and a SHA-256 digest'
[[ "$selected_name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$ && "$selected_name" != *..* ]] || fail 'Invalid destination filename'
mkdir -p -- "$3"
destination=$(cd -- "$3" && pwd -P)
file="$destination/$selected_name"
[[ ! -L "$file" ]] || fail 'Destination symlink refused'
verify() { [[ $(sha256sum -- "$1" | cut -d ' ' -f 1) == "$selected_hash" ]]; }
if [[ -f "$file" ]]; then
 verify "$file" || fail 'Existing asset digest differs; retained for review'
 printf 'VERIFIED EXISTING: %s (%s)\n' "$selected" "$selected_license"
 exit 0
fi
lock="$file.download-lock"
mkdir -- "$lock" 2>/dev/null || fail 'This asset is being downloaded or a stale lock needs review'
part="$file.part.$$"
cleanup() { local result=$?; trap - EXIT; rm -f -- "$part"; rmdir -- "$lock" || return 74; return "$result"; }
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
curl_bin=${WORKSHOP_CURL:-curl}
"$curl_bin" --proto '=https' --proto-redir '=https' --fail --location --retry 2 --max-time 90 --max-filesize 67108864 "$selected_url" --output "$part"
[[ -f "$part" ]] && verify "$part" || fail 'Downloaded asset digest differs; partial file removed'
mv -- "$part" "$file"
printf 'VERIFIED DOWNLOAD: %s (%s)\n' "$selected" "$selected_license"
