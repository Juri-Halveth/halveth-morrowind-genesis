# Sculpted visuals 1.0.0

This additive visual pass runs inside OpenMW's renderer. It slightly lifts dark
midtones, warms lit surfaces, and adds restrained, depth-aware local detail. Sky,
underwater views, and near-clip pixels are excluded. It does not create a 3D mesh
from a picture, replace a face model, or add a browser overlay.

The original MIT shader is `mod/shaders/halveth_sculpted.omwfx`. When it is present
in an OpenMW data directory, add `halveth_sculpted` before `bloomlinear` in the
post-processing chain. The recommended starting values are strength 0.65,
detail 0.22 and warmth 0.12. All three are adjustable in OpenMW's shader menu.
With the supported Zesterer SSAO, Scarlet Beauty now recommends 24 samples,
intensity 2.2 and radius 65 to keep small facial and clothing details readable.
Existing saved settings are preserved until a graphics profile is deliberately
updated; copying the source alone does not activate a shader.

`scripts/Apply-VisualRefresh.ps1` updates five explicitly listed application
files in an existing Genesis 1.0.6-preview installation. First run with `-DryRun`,
then use its `planSha256` with `-Apply -ExpectedPlanSha256`. The game and companion
must be closed. The patch checks managed preimages, saves verified originals,
updates the installed file manifest, and rolls back its own partial writes if
an application step fails. It does not register downloaded assets or change
the player's graphics settings. Do not confuse this source patch with a new
standalone setup executable.

## Head-replacer compatibility

A pluginless head pack normally replaces vanilla mesh paths. An existing
Better Heads adapter can redirect those paths elsewhere. Loading both packs
without checking the selected model can therefore leave the old head visible.

`scripts/build_selective_head_adapter.py` can build a private replacement for
an existing visual-only BODY adapter. Supply the original masters in order,
the existing adapter, the downloaded pack's data root, and a new output folder.
Only a head or hair record whose vanilla mesh actually exists in the new pack
is redirected. Non-matching mappings remain unchanged. NPC records, quests,
inventory, stats, and saves are outside this operation. The result still needs
texture-dependency checks and an in-game visual check before activation.

Third-party packs, generated binary adapters, game masters, private graphics
manifests, screenshots, and saves are excluded from the public source archive.
Download credits and licenses belong to their respective authors.

## Verified scope

The original shader was compiled and enabled by OpenMW 0.51.0 in a fresh
2560-by-1440 Seyda Neen scene. A second run loaded the shader from the installed
application and exited without reported shader or Lua errors. No existing save
was opened for these checks. Frame callbacks under concurrent desktop work are
not a sustained performance benchmark or a guarantee for every scene.
