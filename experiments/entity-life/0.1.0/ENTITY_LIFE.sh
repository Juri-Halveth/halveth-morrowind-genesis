#!/usr/bin/env bash
# MIT. Decision and propagation prototype in Bash; the binary catalogue uses Python.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mode=${1:-demo}; (( $# == 0 )) || shift
case "$mode" in
 catalogue|find|bind-demo)
  task_python=${ENTITY_PYTHON:-python}
  exec "$task_python" -B "$here/registry.py" "$mode" "$@"
  ;;
 demo) ;;
 *) printf 'ENTITY_LIFE.sh demo [connected|visual-only] [bold|bright|contemplative]\nENTITY_LIFE.sh catalogue --config CFG --output NEW --assets OWN_ASSETS\nENTITY_LIFE.sh find --registry FILE --query TEXT [--limit 8]\n' >&2; exit 2 ;;
esac
policy=${1:-connected};signal=${2:-bright}
(( $# <= 2 )) || { printf 'Too many arguments\n' >&2;exit 2; }
case "$policy" in connected|visual-only) ;; *) printf 'Invalid policy\n' >&2;exit 2;; esac
case "$signal" in bold) bias=0;; bright) bias=1;; contemplative) bias=2;; *) printf 'Invalid declared player signal\n' >&2;exit 2;; esac
hash_text() { printf '%s' "$1" | sha256sum | cut -d ' ' -f 1; }
actor_id="e_$(hash_text 'HALVETH-OWN-DEMO|actor')";actor_name='Velora-Funke'
dagoth_id="e_$(hash_text 'HALVETH-OWN-DEMO|story-endpoint')";dagoth_name='Nerion-Stern'
cup_id="e_$(hash_text 'HALVETH-OWN-DEMO|cup-instance')";cup_name='Avela-Welle'
binding='OWN_SYNTHETIC_FIXTURE'
registry_dir=${ENTITY_REGISTRY_DIR:-"$here/../entity-life-catalogue-0.1.0"}
if [[ -f "$registry_dir/DEMO_ENTITIES.tsv" ]]; then
 declare -A seen_roles=()
 while IFS=$'\t' read -r role identity name; do
  # LF and CRLF are the two declared line-ending formats of this TSV file.
  name=${name%$'\r'}
  [[ "$identity" =~ ^e_[0-9a-f]{64}$ && "$name" =~ ^[A-Za-z0-9-]+$ ]] || { printf 'Invalid entity binding\n' >&2;exit 2; }
  [[ -z "${seen_roles[$role]+present}" ]] || { printf 'Duplicate role\n' >&2;exit 2; }
  seen_roles[$role]=1
  case "$role" in actor) actor_id=$identity;actor_name=$name;;dagoth) dagoth_id=$identity;dagoth_name=$name;;cup) cup_id=$identity;cup_name=$name;;*) printf 'Unknown role\n' >&2;exit 2;;esac
 done < "$registry_dir/DEMO_ENTITIES.tsv"
 [[ ${#seen_roles[@]} == 3 && -n "${seen_roles[actor]+present}" && -n "${seen_roles[dagoth]+present}" && -n "${seen_roles[cup]+present}" ]] || { printf 'Incomplete role binding\n' >&2;exit 2; }
 binding='LOCAL_SOURCE_IDS; RULES_ARE_DECLARED_PROTOTYPE_DESIGN'
fi
run=$(mktemp -d "${TMPDIR:-/tmp}/entity-life.XXXXXXXX")
history="$run/history.tsv";printf 'sequence\tentity_id\tevent\tvalue\tstate_sha256\tprevious_event_sha256\tevent_sha256\n' > "$history"
sequence=0;previous='GENESIS';rumor=0;house=0;dagoth='unaware'
hair='unselected';presentation='unselected';hue=0;state=''
actor_before=$actor_id
append_event() {
 local entity=$1 event=$2 value=$3 snapshot=$4 record event_hash
 sequence=$((sequence+1));record=$(printf '%s\t%s\t%s\t%s\t%s\t%s' "$sequence" "$entity" "$event" "$value" "$snapshot" "$previous")
 event_hash=$(hash_text "$record")
 printf '%s\t%s\n' "$record" "$event_hash" >> "$history"
 previous=$event_hash
}
printf 'BINDING: %s\nPOLICY: %s; PLAYER SIGNAL: %s (explicit input)\n' "$binding" "$policy" "$signal"
printf 'ACTOR: %s [%s]\nCUP: %s [%s]\nSTORY ENDPOINT: %s [%s]\n' "$actor_name" "$actor_id" "$cup_name" "$cup_id" "$dagoth_name" "$dagoth_id"
styles=(cropped braided flowing);presentations=(feminine masculine androgynous)
preference=$((16#${actor_id:2:2}))
for tick in 0 1 2; do
 # A deterministic agent policy chooses a candidate; the ID remains stable.
 # Candidate grammar is finite and visible, not an unrestricted generative model.
 hair=${styles[$(((preference+bias+tick)%3))]}
 presentation=${presentations[$(((preference+2*bias+tick)%3))]}
 hue=$(((preference*31+bias*71+tick*47)%360))
 state=$(hash_text "id=$actor_id|hair=$hair|presentation=$presentation|hue=$hue")
 append_event "$actor_id" 'AGENT_APPEARANCE_CHOICE' "$hair/$presentation/hue-$hue" "$state"
 printf 't=%s CHOICE: %s, %s, hue=%s; SAME ID; state=%s\n' "$tick" "$hair" "$presentation" "$hue" "${state:0:16}"
 if [[ "$policy" == connected ]]; then
  rumor=$((rumor+1));append_event "$actor_id" 'RUMOR_RULE' "visible-change-$rumor" "$state"
  house=$((house+1));append_event "$actor_id" 'HOUSE_NOTICE_RULE' "notice-$house" "$state"
  dagoth='reassess';append_event "$dagoth_id" 'DAGOTH_RESPONSE_RULE' "$dagoth" "$(hash_text "id=$dagoth_id|strategy=$dagoth|notice=$house")"
 fi
done
[[ "$actor_before" == "$actor_id" ]] || { printf 'Identity changed unexpectedly\n' >&2;exit 1; }
if [[ "$policy" == visual-only ]]; then
 [[ "$rumor" == 0 && "$house" == 0 && "$dagoth" == unaware ]] || exit 1
fi
printf 'RESULT: ID stable; history=%s events; rumor=%s; house=%s; story-endpoint=%s\n' "$sequence" "$rumor" "$house" "$dagoth"
printf 'HISTORY: %s\nSCOPE: Bash logic prototype; native appearance/story adapter is pending.\n' "$history"
