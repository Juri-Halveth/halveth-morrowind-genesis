# LEVIATH field workshop

Own MIT gameplay source for OpenMW 0.51.0 / Lua API 129. F4 opens the native
field workshop; activating its own plot or workbench opens the same panel.
An optional existing `HALVETHFieldcraft` collection atlas can remain connected.

Place creates two own activator records in a dry exterior area: a saltrice
plot and a field workbench, using model references supplied by the player's
existing local game. It replaces no original plant or table. The production
module gives no free seeds or ingredients.

- Plant two saltrice; after 24 game hours harvest four saltrice.
- Process two saltrice and one comberry; after six game hours receive one own
  LEVIATH field ration.
- The ration is an actual Potion record declaring Restore Fatigue at two points
  per second for 15 seconds. Native record creation and inventory delivery are
  checked; consumption and the resulting active effect are a separate open test.

One job runs at a time. Ingredients move into an own disabled engine depot.
Work begins after their actual inventory debit is observed. Collection needs
readiness and a distance of at most 450 game units from the relevant own
activator. It awards an output once, observes the actual inventory quantity and
consumes stored ingredients. A duplicate collection gives no further output.
Normal waiting and travel advance the OpenMW game time used by these recipes.

## Install only in an isolated profile

Register the existing `gameplay/mod` directory, then add this production content
entry to the isolated playable profile. If courier already registered that data
directory, keep the single existing data line and add only fieldwork content.

```ini
data="<absolute-path-to-workshop>/gameplay/mod"
content=veyra-fieldwork.omwscripts
```

`scripts/workshop.sh plan PROFILE` checks the selected profile without launching
a game; `play PROFILE` opens its normal engine menu. An explicitly selected
save is optional. The public source package contains no automated farm probe,
free test ingredients, accelerated test clock or native fixture registration.

The F4 panel provides Place, Plant, Process, Collect and the optional collection
atlas. It changes no profile keybindings; F9 remains normal OpenMW QuickLoad.

## Three native observations

The [initial receipt](../docs/FIELDWORK_NATIVE.json) binds 19 finite checks:
two real activators, no free production inputs, real ingredient debit,
23/24-hour growth, readiness, distance, four real harvest items, duplicate
rejection, 5/6-hour processing and one actual ration record/item.
The [done reload](../docs/FIELDWORK_DONE_RELOAD_NATIVE.json) adds five checks
for restored objects, consumed depot, ration and counters without duplication.
The [working reload](../docs/FIELDWORK_WORKING_RELOAD_NATIVE.json) adds six
checks for restored seeds, early rejection, maturity and one-time harvest.
All three exit successfully and bind the same four production source hashes.
They share the same local engine and fixture provenance. Fourteen bound
original files retain their digests in each separate run.

The fixture calls the same native panel interface; a physical F4 press remains
open. The UI screenshot is distinct from complete visual acceptance. Recipe
timers define game rules; the crop has no animated growth stages or irrigation.
The ration's actual consumption and active magic effect remain open.

Inventory deltas bind interchangeable local quantities. They do not establish
external provenance. A conflicting mod changing the same inventory quantity
during a transaction can stall it; this module invents no replacement yield.
Multiplayer, other inventories, climate, NPC labor and unrestricted building
require additional implementations and observations.

## Engine contracts and license

- [Inventory and GameObject operations](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html)
- [Activator, Container and Potion record drafts](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
- [World creation and game time](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)
- [Save, load, activate and key handlers](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/engine_handlers.html)

Own code is MIT. Engine and locally supplied game resources keep their own
rights. Game saves, source resources and generated engine records are absent
from the public source bundle.
