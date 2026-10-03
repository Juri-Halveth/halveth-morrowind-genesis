# Veyra courier: native single-player candidate

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

Existing inventory-stack merging, every interior/navmesh/door route, courier
death recovery, multiplayer and remote authentication are outside that fixture.
Save/reload evidence is recorded separately from this first frozen receipt.
Screenshots and source correctness are separate from a complete visual
acceptance or a full campaign/performance result.

Official versioned API references:

- [World module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
- [Types module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
- [Nearby module](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_nearby.html)
- [AI interface](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/interface_ai.html)
