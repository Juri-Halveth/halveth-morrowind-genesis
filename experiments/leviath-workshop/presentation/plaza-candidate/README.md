# LEVIATH Plaza 0.1.0

Owned additive arrival, approach and arena geometry for the already owned
Frontier. This is a bounded architecture candidate. Its meshes, reference
structure, repeated build bytes and existing native TES3 parser pass;
OpenMW scene appearance, collision and player movement remain pending the
coordinated root probe.

The original Foundation profile, saves and Frontier bytes are read-only
inputs. The new ESP defines three own STATs and places three new references
into two owned Frontier cells. It adds no scripts, portal, NPC or network
service. It does not alter Bethesda CELLs or replace original models.

## Exact dependencies and configuration

Required Frontier ESP SHA256:
`7484682d663d62a22dfe59c01d3dbce862a2e1897f66e1b563b5b455cb2a75ad`.
Required own stone DDS SHA256:
`d54f2025d173e9ade36d1e011c20b0f2e4667e2afe353013a5f05cff1b0bad31`
from the separate texture-only candidate. The mesh material path is
`textures/veyra/frontier/frontier_stone.dds`; no texture is duplicated here.

The candidate profile needs the frozen Frontier content and the separate
texture data layer, then:

```ini
data="<absolute-path-to-presentation-candidate>/plaza-candidate/mod"
content=LEVIATH-Plaza.esp
```

`cfg-additive.txt` supplies those lines. The ESP explicitly depends on
`Morrowind.esm` followed by `LEVIATH-Frontier.esp`. Removing this own add-on
restores the plain owned Frontier when starting from a clean candidate save.
Persisted game state and source rollback remain separate observations.

## Models and exact placement

`PLACEMENTS.json` binds the actual serialized float32 positions. Unlike the
tree prototypes, these models use their own origin at the terrain height320
and local foundation base -64. There is no500unit tree anchoring offset.
Floor tops are local8, giving world328. The small foundation depth reaches
below the existing terrain rather than floating on a visible plane.

| Record ID | Own ref | Cell | Position |
| --- | --- | --- | --- |
| `veyra_plaza_arrival` | `0x00000101` | `(65,-63)` | `(536576,-512000,320)` |
| `veyra_plaza_approach` | `0x00000102` | `(65,-63)` | `(537563.3125,-511012.65625,320)` |
| `veyra_plaza_arena` | `0x00000103` | `(66,-62)` | `(540672,-507904,320)` |

All three reference IDs are unique across the entire ESP and have high byte0,
marking new local references. Two CELL headers are from the owned Frontier;
their region/water flags are preserved. The architecture adds references to
those cells and changes no LAND, region or material records.

The architecture totals13168triangles across three COLLADA meshes. The arena
has radius1900floor, eight seating terraces between radii1900and2800, an
outer wall to radius3000, two gateway pylons and a north ramp rising256over900
units (15.9degrees). Its north rim is taller; the southwest entrance stays
open. Segment snapping widens the outer opening above the planned720units.
It is simple owned geometry, not a photorealistic or complete colosseum.

The landing is conservatively512x512 instead of the earlier900x900 plan,
so every corner fits inside the decoded6200radius flat pad. Approach and
arena vertices also remain in that pad. The implementation narrowing is
recorded in `BUILD_RECEIPT.json`; the earlier plan remains a design record.

## Build and file-level acceptance

Run `build-plaza.py --base-config <bound-foundation/openmw.cfg>` through
Git Bash using the existing Python3.14/Pillow runtime. It imports only the
digest-bound own Frontier base-reader module, rescans the bound sixteen
Foundation ESM/ESP inputs and checks its own STAT namespace before writing.
Changed master/config/material bytes stop the build. No source profile or
save is written and no native engine is started.

Then run `check-plaza.py --base-config <same-cfg> --esmtool <bound-esmtool.exe>`.
The independent decoder checks serialized COLLADA arrays, indices, finite
coordinates, triangle areas, winding/normal agreement, geometric edge parity,
material links, TES3 master sizes, two own CELL coordinates and three exact
reference transforms. A second build matches six outputs. The existing
ESMTool1.3 parser browses all new CELL references and returns0.

`PLAZA_GEOMETRY_PREVIEW.png` was reviewed in two views. It is an author-space
geometry preview, not an OpenMW image or a collision pass. No special
collision-node contract is invented: the candidate uses ordinary visible
solid geometry. Native ray hits and player movement decide whether the
engine actually treats it as usable collision geometry.

## Decisive native scene

Root's prior Frontier probe already observed terrain height320 and a walk
across the four-cell junction. That source-grounding is a prerequisite, not
a collision proof for these new meshes. Stage this candidate separately and
bind the new ESP/material/placement digests.

First arrive at `(536576,-512000,576)`. Observe landing on the own platform,
a downward World ray explicitly hitting `veyra_plaza_arrival` near height328,
and actual `isOnGround` after the fall. Follow the approach toward the
southwest gateway and arena. At least one World ray must explicitly hit each
own model, rather than merely report a generic ground hit. The terrain-only
HeightMap ray should remain320 at the flat pad.

Inside the arena, observe floor contact, perimeter movement and the north
ramp. Test the four-cell junction and both sides of the gateway. Inspect a
southwest view, the taller north silhouette, a close floor/step view and a
boundary crossing. Compare original-save/source hashes after the run.
Wall penetration, a snag, a missing face or an inaccessible route remains
a concrete repair target; a file/parser pass does not close those cases.

Own code, geometry, source preview and the included license are MIT.
The dependency material is separately owned MIT. No Bethesda or commercial
game mesh, image, music or source code is copied into this unit.
