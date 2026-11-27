# Veyra courier 0.2.3: native single-player candidate

Own MIT Lua source, bound to OpenMW 0.51.0 / Lua API 129. The player's existing
Morrowind data remains an external local prerequisite. This module is installed
in an isolated candidate profile first.

The adapter seeds one **synthetic** parcel, consisting of one `daedric longsword`
game-record reference and an authored letter using an existing scroll asset
reference. A disabled container stores the objects. After two game days a
finite route model tracks the player's last exterior position. A navmesh and
line-of-sight checked landing spawns an owned NPC record derived from the
local `eldafire` template. The NPC follows the player and offers the parcel.
F10 accepts both objects once they have actually arrived.

The synthetic seed is visibly described as a technical experiment in the
authored letter. It does not establish that a foreign visitor connected or
deposited anything. The future visitor receiver is separate and remains
owner-controlled.

## Isolated installation

Keep the runtime and original masters at their existing licensed locations.
Add the resolved absolute path of this module's `mod` directory and its content
registration to the isolated profile's ordinary playable configuration:

```ini
data="<absolute-path-to-workshop>/gameplay/mod"
content=veyra-courier.omwscripts
```

Use `scripts/workshop.sh plan PROFILE` first, then `play PROFILE`. An explicit
save is optional; otherwise the engine menu opens. The playable configuration
contains neither the native test fixture nor automatic teleports or exits.
Candidate saves preserve their own depot/courier state; original saves and
masters are supplied read-only as starting inputs.

## Checked scope

The public [native receipt](../docs/COURIER_NATIVE.json) binds the exact five
production source files and fourteen native checks, including disabled storage,
delayed dispatch, real NPC creation/approach, real inventory delivery and a
repeated claim without duplication. The fixture accelerates game time.

The separate [claimed reload receipt](../docs/COURIER_RELOAD_NATIVE.json) adds
five checks for restored parcel state, references, inventory and duplicate
rejection. The [hidden depot reload receipt](../docs/COURIER_DEPOT_RELOAD_NATIVE.json)
adds four checks for pre-dispatch state, two restored depot items, no premature
courier and no premature award. The same five production sources bind all three
native runs for the current save-schema-2 source. Their shared local fixture provenance is recorded separately from
the number of observed checks.

The [existing-stack observation](../docs/COURIER_STACK_NATIVE.json) adds sixteen
checks for a fully conditioned, unenchanted Daedric longsword. Its real stack
identity stayed, the count increased from one to two and a repeated claim gave
nothing. The [transfer reload](../docs/COURIER_TRANSFER_RELOAD_NATIVE.json) adds
five checks after saving during the real TRANSFERRING phase. The saved actual
pre-transfer identities, counts and item states resume the same bounded mapping.

Historical schema-1 claimed and waiting-depot saves have separate
[five-check](../docs/COURIER_CLAIMED_MIGRATION_NATIVE.json) and
[four-check](../docs/COURIER_DEPOT_MIGRATION_NATIVE.json) migration observations.
Existing references stay and no premature or repeated award occurs. These are
seven runs bound to the same five current production files; they are not
independent engine/platform confirmations.

The first implementation could hang in TRANSFERRING when inventory objects
merged into an existing stack. Its failed history and first source archive
retain that stand. Version 0.2.3 records the actual pre-transfer witness and
checks the post-transfer reference/count mapping. An old schema-1 TRANSFERRING
save without that witness stays TRANSFER_HOLD instead of inventing an award.

Other condition/charge/soul combinations, inventory mutation by other mods,
every interior/navmesh/door route, courier death recovery, multiplayer and
remote authentication remain outside the tested fixture.
Screenshots and source correctness are separate from a complete visual
acceptance or a full campaign/performance result.

The separate [field workshop](FIELDWORK.md) has its own registration and
nineteen new-job, five completed-reload and six working-reload native checks.
It extends real inventory gathering with timed growth and a ration record;
actual ration consumption and active magic effects remain a separate check.

Official versioned API references:

- [World module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
- [Types module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
- [Nearby module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_nearby.html)
- [AI interface](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/interface_ai.html)
