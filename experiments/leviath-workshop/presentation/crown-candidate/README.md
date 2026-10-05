# Dense swamp crown 0.1.0

A separate own tree form with a curved, continuous tapered trunk, eight
primary branches, thirty-two secondary twigs and thirty-six partly
overlapping crown lobes. Its 2,988 broader folded leaves include explicit
backfaces. The full model has28,716triangles:4,812wood and23,904foliage.
The preliminary26,000..29,000budget is met.

The concrete repair basis was the directly reviewed native fork and wind
images in `world-candidate/evidence/probe-20261003T022922/window-3.png` and
`window-7.png`. Those trees are visible but have sparse separate leaf clumps
and cut-looking stem ends. This candidate uses a tip radius0.38 inside the
top crown lobe, inner twig/leaf groups and a lower-to-upper crown outline.

## Additive placement and material contract

The plugin defines only one new own STAT, `veyra_swamp_crown_01`. It contains
no CELL references and no original-class overrides. Append after the bound
bark-material data directory in a separate native candidate:

```ini
data="<absolute-path-to-presentation-candidate>/crown-candidate/mod"
content=Veyra-Dense-Crown.esp
```

The root fixture can create the new STAT at the actual terrain height. Read
`PLACEMENT.json` for the bound model/plugin hashes. **Model origin is local0;
the tree500offset does not apply.** Roots have nominal centres down to-64;
the exact minimum of the solid root geometry is saved in the manifest.

The new own leaf DDS uses `Textures/veyra/crown_leaf_01.dds`,256square with
nine mip levels,43,832bytes. It leaves all old foliage textures unchanged.
The ordinary leaf Phong material has low specular and a small declared fill
emission to reduce completely dark backfaces. Native shading must decide
whether that choice is visually useful. It does not supply physically based
transmission or animated wind.

The exact preverified CC0 dependencies are:

| Relative VFS file | SHA256 |
| --- | --- |
| `Textures/veyra/swamp_bark.dds` | `76dabf30eb286fcd2cbb4f964aa45fcd2b4a63e53a4b2a611128828c20845e2d` |
| `Textures/veyra/swamp_bark_n.dds` | `33c12d7cb40671721fc22861fb45d1eb9ab8c7ab9beb8d4f659b3eedf139b722` |

Those files are read and hashed, never copied or changed. Attribution and
the source/license references are in `THIRD_PARTY_NOTICES.md`.

## Source build and verified structure

Through Git Bash, use the existing Python3.14/Pillow12.3 runtime:

```bash
python build-crown.py --master '<bound-Morrowind.esm>' \
  --materials-mod '<existing-owned-vegetation-mod>'
python check-crown.py --master '<same-master>' \
  --materials-mod '<same-material-mod>' --esmtool '<bound-esmtool.exe>'
```

The generator copies no game geometry. Its exact own MIT kernel is
`geometry-kernel.py`, digest-bound in the receipt, imported without cache
writes. The master digest/size and new own STAT namespace are checked.
This specific namespace check covers the exact master; staging against
other mods still needs the root's effective content inventory.

`check-crown.py` independently decodes the stored COLLADA arrays, finite
coordinates, unit normals, indices, nondegenerate triangles, explicit paired
leaf backfaces, bark/new-leaf material paths, exact one-STAT TES3 schema,
budget and DDS bytes/opaque alpha/mips. The tapered tip lies inside the
specified top crown ellipsoid. A repeated build matches five outputs.
The existing bound ESMTool parser accepts the new plugin with exit0.

The own `CROWN_PREVIEW.png` was reviewed in three azimuths and a top view.
It shows fuller inner crown coverage and connected leaf groups. Raster
coverage within each projected leaf bounding box is recorded as a declared
source-preview measure. It proves neither native lighting nor visual
realism, species accuracy or a complete2027/2028 graphics result.

## Root native comparison

At the previous tree comparison position/time/weather, spawn the new own
STAT with origin at the measured terrain height. Capture a full tree, close
root/ground view, a side view and a crown detail. Confirm an explicit World
ray hit on the new trunk, the actual ground anchor and complete render bounds.
Compare stem continuity, canopy mass, dark leaf backfaces and repeated
clumping. Record frame behaviour and object count before increasing density
across a forest. There is no class replacement in this first candidate.

Existing vegetation variants, Frontier, Plaza, their source profiles and
original saves remain unchanged. Own source/model/leaf image/plugin/preview
use MIT; the referenced Poly Haven bark retains its verified CC0 license.
