# REZERO native presentation 0.1.0

New native inventory, main menu, loading graphics and authored world models for
OpenMW 0.51.0. The world module replaces the model fields of 39 original records;
the icon module replaces 40 original item icons. Existing cells, positions,
quests and item properties supply the logical game world.

The inventory shows actual quantities, equipment, weight, value, weapon damage
and magic effects. Hover preview is separate from the selected action target.
Inventory simulation continues while this interface is open.

## Local build

Requires Git Bash, Python 3.10+ and a flat source OpenMW config pointing to the
user's licensed original masters. This config must explicitly start with
`replace=config`, `replace=data` and `replace=content`, before its source entries.
Includes and subsequent resets are rejected. `data-local` has the highest
priority regardless of its line position. Use a fresh output directory outside
the source package, config directory and game data roots:

```bash
bash REZERO.sh check
bash REZERO.sh build --config /path/to/original/openmw.cfg --output /path/to/new-build
```

The build creates local master-dependent plugins and a `CONTENT.list`. Add the
resulting `mod` directory last in a fresh OpenMW profile and add those three
content entries in that order. Set `Fonts_Font_0`, `Fonts_Font_1` and
`Fonts_Font_2` to `DejaVuLGCSansMono`; use the runtime's existing font, plus this
package's descriptor. Set `[GUI] stretch menu background = true` for the native
main menu. Use the physical display observation for presentation dimensions;
the Lua layout derives its geometry from the actual UI layer.

This source package is an opt-in experiment. It does not replace the repository's
existing installer or launcher. The local rebuild profile uses fresh settings;
the public builder creates assets/plugins and does not import a prior graphics
profile or change a source installation.

## Native coverage

On the bound OpenMW 0.51.0 source, the combined local integration completed with
zero failed assertions, zero engine/Lua errors and no source/save changes.
Coverage includes 40 actual inventory items, icon records, original room model
references, an advancing inventory simulation, preview/selection separation,
page two, search/reset, magic, attributes, the native main menu and three fixed
original-room views. The UI transitions were invoked through a private Lua
fixture. Direct mouse/text delivery is still pending; those calls are not
claimed as physical-input acceptance.

This is not a full game remake or a Dune-quality graphics claim. Existing NPC
bodies/clothing, many world records and other native interfaces remain to be
replaced. The figure pane currently exposes eight attributes and dynamic stats,
not a full character editor. Indoor candle shadows are not physically complete;
the tested profile disables the legacy indoor projected-shadow path.

## Source and licensing

Own Lua, Python, Bash, vector art and authored COLLADA geometry are MIT. Source
SVGs and native artwork builders are included under `art-source` and `tools`;
the artwork builders require Node.js and `sharp`. `geometry.py` supplies the
own primitive/export toolkit. COLLADA source models are directly editable.

Material photographs from Poly Haven are CC0: [Oak Veneer 05](https://polyhaven.com/a/oak_veneer_05),
[Grey Plaster](https://polyhaven.com/a/grey_plaster) and
[Stone Tiles](https://polyhaven.com/a/stone_tiles), under its
[asset license](https://polyhaven.com/license). They are adapted to OpenMW's
classic diffuse/normal/specular material path. This package does not introduce
a PBR or path-tracing renderer.

Bethesda masters, retained original record bodies, saves, private recordings,
Dune packages and engine executables are absent. The local builder keeps those
licensed record bodies local; its generated plugins are outside this public
source package.
