# Veyra Presentation 0.1.1

A small native OpenMW 0.51.0 HUD candidate. It presents the player's actual
health, magicka, fatigue, cell, game clock and carried weight. The panel adds
an explicitly noninteractive layer and updates at most ten times per second.
Existing weapons, spell selection, map, dialogue and inventory remain available.

## Integration into a separate profile

Generate the owned 22-byte texture with `python build-assets.py`, then append
these two lines to the candidate profile's `openmw.cfg` and `play.cfg`:

```ini
data="<absolute-path-to-this-package>/mod"
content=Veyra-Presentation.omwscripts
```

Use forward slashes in a Windows absolute path. The profile must use OpenMW
0.51.0 and load its ordinary game content first. No additional ESP or master
is required. Do not copy these settings into the original installed profile
until the separate native test and visual review are accepted.

The panel respects `I.UI.isHudVisible()` and hides when a menu/dialogue is open.
It changes no actor stats, inventory, movement controls, game settings or
network state. Other Lua modules can call
`I.VeyraPresentation.setEnabled(false)` / `setEnabled(true)` if they own a
documented toggle. This package does not intercept an existing key binding.

When `I.VeyraCourierPlayer.getState()` is available, the panel shows the
arrival notice and `[F10] Sendung annehmen` only while that module reports
`phase=ARRIVED`. The courier module owns F10 and its inventory operation.
Absent, failed, approaching or already claimed courier state leaves this
notice hidden. The HUD makes no change to the courier module.

`I.VeyraPresentation.getState()` returns a fresh nested snapshot containing
the displayed values, `courierArrived`, `visible`, `screen.width`,
`screen.height` and `lastReadAtGameTime`. The timestamp is OpenMW game time
in seconds; the screen dimensions come from `ui.screenSize()`. `visible`
records the requested layout state, which needs a screenshot before it can
be described as an observed visible render. When hidden, the last sampled
values and timestamp stay available. Before the first sample this interface
returns nil. Mutating the returned table cannot change the stored values.

Removing the two configuration lines removes this module. It has no save
handler, saved per-character state or effect on original game files.

## Tests and claim scope

`check-hud.lua` runs under ordinary Lua 5.1 against declared engine doubles:

```bash
VEYRA_TEST_LUA=/path/to/lua51 bash CHECK_HUD.sh
```

Twelve checks cover modified maxima, negative fatigue, bounded bar geometry,
menu/HUD visibility, strict enable input, clock wrap and cell change, resize
and load cleanup, invalid observations, an unloaded player cell, courier
arrival transitions and absent/failed optional coupling, and detached visible
screen/timestamp snapshots.

`CHECK_RECEIPT.json` records these model checks. At authoring, native rendering,
real engine API integration, actual frame cost and visual fit are pending.
Look for `VEYRA_HUD_READY` in the candidate OpenMW log; inspect a screenshot
with the panel visible, then confirm dialogue/menu hiding and an actual stat
change before calling those behaviours observed in the real engine. For the
combined courier probe, inspect `APPROACH`, `ARRIVED` and `CLAIMED` and confirm
that only `ARRIVED` shows the F10 hint. Historical 1080p screenshots do not
establish fit in the current 2560 x 1440 foundation profile.

## Sources and license

All package source and its procedurally generated white texture use the
included MIT license. No original Morrowind asset, external art, save,
private local path or network endpoint is embedded in this mod.

The implementation was bound to the API documentation shipped with the
installed OpenMW 0.51.0 runtime and checked against official references:

- [Actor dynamic stats](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_types.html)
- [UI package and layers](https://openmw.readthedocs.io/en/stable/reference/lua-scripting/openmw_ui.html)
- [UI mode and HUD visibility](https://openmw.readthedocs.io/en/stable/reference/lua-scripting/interface_ui.html)
- [Text widget](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/widgets/text.html)
- [Image widget](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/widgets/image.html)

OpenMW's source/API licensing and game content licensing remain separate.
