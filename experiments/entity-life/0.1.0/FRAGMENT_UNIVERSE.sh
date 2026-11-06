#!/usr/bin/env bash
# MIT. An isolated state namespace with a retained parent and typed return.
set -euo pipefail
(( $# == 0 )) || { printf 'This bounded demo takes no arguments.\n' >&2;exit 2; }
digest() { printf '%s' "$1" | sha256sum | cut -d ' ' -f 1; }
parent_id="e_$(digest 'HALVETH-OWN-FRAGMENT|retained-parent')"
child_id="e_$(digest "HALVETH-OWN-FRAGMENT|child-of=$parent_id|branch=1")"
parent_state='hue=30;story=unresolved'
parent_before=$(digest "$parent_state")
child_state='hue=30;story=unresolved'
printf 'PARENT: %s\nCHILD NAMESPACE: %s\n' "$parent_id" "$child_id"
child_state='hue=171;story=exploring'
printf 'CHILD CHANGE: %s; state=%s\n' "$child_state" "$(digest "$child_state")"
# The invalid candidate is retained as an observation, rather than silently
# normalized into a usable state or forwarded to the parent.
invalid_candidate='hue=???;story=unknown'
printf 'INVALID CANDIDATE RETAINED: state=%s; return=REJECTED_BY_BOUND_TYPE\n' "$(digest "$invalid_candidate")"
[[ $(digest "$parent_state") == "$parent_before" ]] || exit 1
request_type='APPEARANCE_HUE_REQUEST';request_value=171
[[ "$request_type" == APPEARANCE_HUE_REQUEST && "$request_value" =~ ^[0-9]+$ && "$request_value" -le 359 ]] || exit 1
printf 'RETURN EVENT: %s value=%s; target=%s\n' "$request_type" "$request_value" "$parent_id"
printf 'RESULT: parent retained; child identity stable; one typed request produced.\n'
printf 'SCOPE: authored Bash state model; request is uncommitted; no native world or human effect.\n'
