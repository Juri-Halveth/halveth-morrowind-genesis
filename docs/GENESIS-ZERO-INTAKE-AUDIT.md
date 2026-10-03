# Genesis Zero intake audit

## Existing Genesis path: observed reads

The earlier Morrowind companion had several automatic inheritance paths:

1. `launcher.py` called `scripts/prepare_profile.py` with `source_profile="max"`.
2. `prepare_profile.py` read `profiles/max/openmw.cfg` and `settings.cfg`, preserved the content/data load order, and optionally copied the source `user-data` saves. Its new graphics profile also searched the state directory and project for `graphics/install.json`, then resolved its data folders and shader chain. It could copy `shaders.yaml` from the source profile.
3. `launcher.py` indexed books, dialogue, and actor definitions from the generated content list into `.local/universe.sqlite3` the first time that store was empty.
4. `graphics_status.py` read `.local/graphics/install.json`, each existing profile's `settings.cfg`, and local graphics verification receipts.
5. The desktop installer had a source-profile path that copied `openmw.cfg` and `settings.cfg` into its package. A separate `--game-data` path authored a small config but still bound Bethesda masters.
6. `scripts/build_head_adapter.py` read the `max` profile to find data directories.

These are real intake routes in the existing Morrowind companion. The new directory below does not call them. This audit does not claim those old routes have already been removed from the existing companion or installer.

## Genesis Zero boundary

`genesis-zero/` is a fresh, standalone browser scene. Its runtime inputs are its own HTML, CSS, JavaScript, WebGL 2 implementation, the current display size, pointer/keyboard input, and an optional locally synthesized Web Audio tone bed. It has no Morrowind/OpenMW package reference, imported game text, texture, shader, saved profile, graphics manifest, launcher receipt, analytics call, remote font, or external runtime dependency.

## Preserved source state

No Morrowind master, save, original Data Files tree, or installed profile was deleted by this change. The existing game assets are still the only complete local game source, while Genesis Zero is only a small independent visual/play slice. A full standalone game still needs independently authored world data, story, characters, animation, sound design, UI, and a distributable runtime. Until those exist, deleting the licensed source would leave no complete playable Morrowind or replacement game.
