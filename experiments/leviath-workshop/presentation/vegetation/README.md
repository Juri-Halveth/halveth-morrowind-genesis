# Veyra Swamp Tree 0.1.0

An isolated, authored static-tree candidate for OpenMW 0.51.0. It has a curved
trunk, seven root flares, ten main branches, thirty finer ends and 930 folded
individual leaves. Every leaf has explicit backfaces. This creates branching
groups and smaller irregular gaps instead of the previous large pointed
Quiver crowns. Native visual acceptance remains pending.

The build has 14,416 triangles: 3,256 wood and 11,160 foliage. Its own geometry,
generator and leaf texture use MIT. The existing Poly Haven bark input uses CC0;
see `THIRD_PARTY_NOTICES.md`. No new asset download was needed.

## Build from source

Requires Python with Pillow (authoring run: Python 3.14 / Pillow 12.3.0), the
existing Bark Brown 02 folder including `files.json`, the local authorized
`Morrowind.esm`, and previous corrected `.dae` inputs to bind their preserved
hashes. These inputs remain read-only.

```bash
python build-vegetation.py \
  --bark-source /path/to/polyhaven/bark_brown_02 \
  --master '/path/to/Data Files/Morrowind.esm' \
  --base-mesh /path/to/corrected/quiver_tree_01.dae \
  --base-mesh /path/to/corrected/quiver_tree_02.dae
```

`BUILD_RECEIPT.json` binds the generator SHA256, input textures and source
metadata, master and target STAT digest, previous mesh digests, all output
digests, finite positions, unit normals, index bounds and mesh bounds. Source
bytes must match the local download metadata; these structural checks are
separate from a native render/collision/anchoring result.

## First native pass: additive placement

Append `cfg-additive.txt`, with its absolute path placeholder resolved, to a
new test profile's `openmw.cfg` and `play.cfg`. This plugin adds only
`veyra_swamp_tree_01`; it overrides no existing STAT, CELL, actor or landscape.

From the **test profile's global Lua fixture**, create a specimen with:

```lua
local world = require('openmw.world')
local util = require('openmw.util')
local specimen = world.createObject('veyra_swamp_tree_01')
specimen:teleport('Seyda Neen', util.vector3(-8000, -68800, 900),
    {rotation=util.transform.rotateZ(0), onGround=true})
```

This is a fixture proposal, not an observed placement. The root coordinator
must choose a clear location, bind actual resulting position/terrain, and
point the camera at the specimen. `onGround` and the model's base need a real
engine observation. The inherited coordinate envelope is approximately
`Z=-507..990`; no world-wide grounding equivalence is claimed.

Create a `flora_bc_tree_02` specimen for the corrected previous mesh in the
same fixture. Compare each specimen at the **same actual position and
rotation**, with the same camera, game clock, current weather and transition.
Do not show both enabled at the same position. Global Lua may set the created
specimens' `enabled` fields; it must leave original placed objects intact.
Log clock/weather/transition for both views. Visual QA covers the crown and
bark, root contact, visible backfaces, illumination and collision/occlusion.
Restore any temporary game-time scale change before the probe ends.

The fixture belongs only to a disposable test profile. Its experimental
objects must not be carried into the copied manual-play save.

## Second native pass: optional class override

Only after the additive anchoring/collision pass, append
`cfg-tree02-override.txt` **after** `LUCINET-World-Reforged.esp`. This replaces
one static class, `flora_bc_tree_02`, with `veyra/swamp_tree_01.dae` in the
separate candidate. The existing master has **105 references** to that class,
including five in Seyda Neen. The effect therefore follows this class across
the candidate world; it is not limited to one cell.

The additive plugin may remain loaded during development, but it is not
required for the class override. Removing the override content line restores
the previous loaded STAT definition. Both plugins contain no CELL records.

## Current result and preview

`SILHOUETTE_PREVIEW.png` contains three technical orthographic views rendered
by the authoring code. It was inspected for shape and holes; it is not an
OpenMW screenshot. The bark maps are 1024×1024 with mipmaps. The complete mod
is about 5.3 MB, mostly the COLLADA text and two bark maps.

**Current:** source and structure checks passed; five input hashes unchanged.
**Pending:** native loading, texture binding, root/terrain contact, collision,
camera comparison, repeated world instances and frame cost.

The requested 2027/2028 or GTA-style visual quality remains a design target.
One candidate tree does not fulfill that whole-game target.
