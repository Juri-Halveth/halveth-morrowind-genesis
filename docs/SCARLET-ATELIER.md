# Scarlet Atelier

Open http://127.0.0.1:18765/#atelier after starting the local companion. It displays the original banner, five provider routes, three copyable production briefs and eight source-bound design cards.

## Original banner

The generated artwork is **887 × 1774 pixels**, portrait 1:2. The production brief requested 1024 × 2048; the shipped file retains the actual output size without inventing extra detail. PNG, TGA and DDS contain the same design. Exact hashes and provenance are in `ASSET-PROVENANCE.json`; reuse terms are in `ASSET-LICENSE.md`.

The F8 dialog loads `Textures/halveth/scarlet-love-banner.png`. The optional world layer overrides `Textures/Tx_de_tapestry_02.tga` and `.dds`, changing **every occurrence of that tapestry type**. It changes no quest, NPC or economy record.

```console
python scripts/install_scarlet_banner.py apply
python scripts/prepare_profile.py --install-root "D:/Games/MyOpenMW" --profile beauty
```

Restart OpenMW to rebuild its texture view. `restore` instead of `apply` removes only this pack's manifest entries and retains unrelated changes and backups. Re-prepare the profile and restart to restore the previous world tapestry. F8 artwork is independent and remains visible.

The DDS derivative matters because [OpenMW 0.51 texture resolution](https://github.com/OpenMW/openmw/blob/openmw-0.51.0/components/misc/resourcehelpers.cpp) prefers a DDS alternative. Shipping only the TGA can leave an older DDS visible.

## Design knowledge

`data/project-knowledge.json` contains eight original paraphrases with repository, commit, source file and retrieval time. A conversation selects at most three relevant cards and at most 6,500 combined characters. These are design references, not claims about Morrowind's canonical lore. The model may still make mistakes. Local extracted game text stays in your own `.local/` database.

## Further assets

[GENERATION-PIPELINE.md](GENERATION-PIPELINE.md) maps Adobe, Meshy, Dreamina/Seedance and Blender to concrete formats. Production briefs are ready to copy. No cloud account, credits, provider output or downloaded 3D model is bundled. An exported video is a cinematic asset, not a traversable world.

This is an OpenMW mod/source release. It contains no Morrowind executable, standalone installer or Unreal runtime. Development-native observations are summarized separately from public-package checks in `PUBLIC-STATUS.json`.
