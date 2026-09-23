# Graphics profiles and optional packs

The source release includes profile helpers and one original banner, not the developer's installed texture, head or shader packs. Local graphics state is discovered from `.local/graphics/install.json`.

| Profile | Viewing distance | Shadows | Water render target |
| --- | ---: | --- | ---: |
| Original | Existing source settings | Existing settings | Existing settings |
| Beauty | 81,920 OpenMW units | 4,096 resolution | 2,048 |
| Cinematic | 131,072 OpenMW units | 8,192 resolution | 4,096 |

Beauty and Cinematic target different GPU budgets. These values are presets, not measured performance guarantees. Model inference can also use GPU memory. Without extra shader packages, preparation uses the engine's built-in effects.

`--reset-settings` backs up existing Genesis profile settings before applying recommendations. It preserves gameplay, input and audio preferences. Normal preparation preserves existing graphics choices. Paths, backups and copied saves remain local.

The optional original banner is enabled with `python scripts/install_scarlet_banner.py apply`; run profile preparation and restart OpenMW afterwards. `restore` disables only that pack. See [SCARLET-ATELIER.md](SCARLET-ATELIER.md).

## Optional external shaders

`scripts/install_shaders.py` downloads fixed source snapshots only when you run it. Review its source pins and each author's terms before use. It does not include, download or activate character/landscape/head packages.

- [Zesterer SSAO](https://github.com/zesterer/openmw-ssao/tree/fa5ec4303ee557b75e3c51c02ab14ff0334271c4)
- [Zesterer clouds](https://github.com/zesterer/openmw-volumetric-clouds/tree/c8830bcd2de0f6e7355f91880308426203eded3c)
- [Wareya shaders](https://github.com/wareya/OpenMW-Shaders/tree/76e0637187cc2878575528119aed72bbbf1a12cf)

The installer validates pinned archive hashes and preserves unrelated manifest entries. Those upstream files retain their original terms and remain outside this repository. Existing packages are not automatically made distributable by installation.

F2 opens OpenMW shader controls. Profile guidance and settings are bound to [OpenMW 0.51 settings](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/files/settings-default.cfg) and [postprocessing documentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/modding/settings/postprocessing.html). A declared shader chain still requires in-engine compilation and a visual check on your hardware.
