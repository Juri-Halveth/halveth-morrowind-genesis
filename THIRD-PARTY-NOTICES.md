# Third-party and asset boundaries

The root MIT license covers original Genesis code, documentation, interface and summary text. It does not relicense referenced projects, external software, separately generated provider outputs or game assets.

| Item | Included | Terms |
| --- | --- | --- |
| Original Python, JavaScript, CSS and Lua code | Yes | MIT (`LICENSE`). |
| Original generated Scarlet LOVE banner, 0.7 astrolabe, 0.8 installer icon and format derivatives | Yes, exact owned paths only | `ASSET-LICENSE.md` and `ASSET-PROVENANCE.json`. The Windows ICO is built from the listed PNG. |
| Eight original source summaries | Yes | Our wording is MIT; each record retains its source URL, commit and source-license note. Original linked contents are not incorporated. |
| OpenMW 0.51.0 engine | Source ZIP and public Setup: no; private local Setup: yes | [Upstream source and GPLv3 terms](https://gitlab.com/OpenMW/openmw/-/tags/openmw-0.51.0). The private local Setup is not approved for public distribution pending full binary/dependency/source review. |
| Official Python 3.14.7 embeddable runtime | Source ZIP: no; both Setup variants: yes | [Python release and license](https://www.python.org/downloads/release/python-3147/); its `LICENSE.txt` is installed with the runtime. |
| Morrowind assets, books and dialogue | No | Use your own licensed game. Local indexing grants no redistribution rights. |
| Optional shader/mod packs | No | Authors' original terms apply. Download links do not change licenses. |
| Ollama/model weights | No | Obtain separately and review model-specific terms. |
| Adobe, Meshy, BytePlus/Dreamina, Blender | No | Production briefs and links only. Access, costs and export terms depend on the selected service/version. |

No Marvel artwork, voice recordings, film clips or branded franchise assets are included. Names and links are descriptive, not endorsements. Contributors must have rights to material they import.

The only permitted source-package binary files are:

- `mod/Textures/halveth/scarlet-love-banner.png`
- `mod/Textures/halveth/love-astrolabe-0.7.png`
- `installer/love-astrolabe-icon-0.8.png`
- `assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.tga`
- `assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.dds`

Other assets need a deliberate provenance/license review and release-list change before inclusion.
