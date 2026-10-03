# Townlife navigation0.1.0 / presentation0.1.2

Three prior native runs each passed32 navigation/UI-state assertions, but neither original right-positioning nor parent anchoring produced an observed right panel in the1920×1080 capture. The API and native layer reported2400×1350. Direct Win32/DWM/PMv2 reads agreed on1920×1080; a DPI capture correction is not established.

This separate candidate changes only the player panel position to(460,28), adjacent to the existing left HUD; relativePosition and anchor are removed. The four navigation production files remain byte-exact. This is a measured visual discriminator, not a demonstrated viewport scaling repair. Viewport-relative placement remains HOLD; reopen on a separately bound UI/window coordinate contract. No system GUI scaling changes. Native visibility for0.1.2 is PENDING.


Three own generated residents travel to real daily destinations beside the
bound LEVIATH Frontier Entry and Plaza: a garden visitor, trade visitor and
watch visitor. The ordinary player panel shows the actual game day, day slot,
destination, reported action and sampled horizontal walking distance.
These visits implement navigation. Harvesting, barter and an economy need
their own mechanics.

Two bounded native runs of the original source each passed 32 assertions:
three distinct dynamic residents, delayed activation, real displacement,
arrival, subsequent day-slot goals, owner disable, and native panel state
and menu hiding. The first images showed the residents but no right panel.
The second observer measured the same 1920x1080 window with and without a
DPI-aware thread context, while `ui.screenSize()` reported 2400x1350.
Visibility in a Lua snapshot did not establish visible raster text.

This separate UI candidate uses parent-relative right anchoring instead of
subtracting the panel width from `ui.screenSize()`. The four navigation
production files and all debug fixtures remain byte-identical to source
0.1.0. `UI_ONLY.diff` and `ANCHOR_PATCH_BINDING.json` bind the exact change.
The original 17-file freeze remains untouched in the previous candidate.
Native raster acceptance of the new presentation is **PENDING**.

The positioning follows the documented
[OpenMW 0.51 Widget contract](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/widgets/widget.html).
The new snapshot separates `screenX/screenY` from the actual layer size.
The 22 Lua 5.1 checks use declared engine doubles, including an independent
parent-coordinate geometry oracle for the observed viewport mismatch.
Model checks do not prove real rendering.

The source uses OpenMW 0.51.0/API129 and attaches a CUSTOM script only to its
generated dynamic NPCs. Activation requires an identity-bound handshake.
Each resident uses its own actor bounds, projects its destination onto the
loaded navmesh, checks a successful path and requests native `Travel`.
Arrival requires fresh sampled horizontal movement and target proximity;
starting at a destination reports position only. At most two stalled
replans are allowed. Pause, combat, owner disable and unloaded cells defer
travel. Save/load begins a fresh observation window; unknown saves retain
a load hold. Native save/load, combat, blocked-route and unload/reentry
coverage remains open.

Build the own white RGBA texture with `python build-assets.py`. An isolated
profile must already load the exact own Frontier and Plaza inputs in
`SOURCE_BINDING.json`, ordinary Morrowind data and OpenMW builtin scripts.

```ini
data="<absolute-path-to-this-candidate>/mod"
content=Veyra-Townlife.omwscripts
```

Ordinary play creates residents only near the named entry. It has no test
teleport, reward or original NPC script/dialogue mutation. The separate
`fixture/` and `Veyra-Townlife-Probe.omwscripts` prepare a copied test scene,
freeze/advance game time, delay activation and open/close the native menu.
Only an explicit probe may register them. Removing the production
registration does not erase generated actors already stored in a save.

Own code, documentation and generated white PNG are MIT. Engine and local
Morrowind data retain separate rights. No original game assets are bundled.
