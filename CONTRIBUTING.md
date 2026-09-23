# Contributing

Keep changes focused. Pull requests should explain the player-visible result, affected files and checks.

Use Python 3.11 or later; runtime code and unit tests need only the standard library:

```console
python -m unittest discover -s tests -v
python scripts/build_release.py --check
```

Tests use temporary directories and synthetic events, with no game, account, model download or paid API. Lua/graphics/transport changes also need a separately described disposable-scene check against OpenMW 0.51.0.

Submit only material you have the right to contribute. Original code/docs contributions use MIT unless explicitly agreed otherwise. New assets need origin, rights and exact release paths. Existing banner terms are separate.

Keep `.local/`, saves, logs, profile paths, conversation databases, extracted game text, credentials, model weights and downloaded packs out of commits. The packaging whitelist does not replace review of commit contents.

Model text remains text. New game actions need explicit parameters and a game receipt; do not execute model-generated console strings or shell commands. Keep fictional design references separate from actual game state.

`python scripts/build_release.py` writes a checked source ZIP and SHA-256 to ignored `dist/`. Keep version, notes and status aligned. A ZIP is not a game installer, native test or hosted CI result.

Use repository issues for sanitized reproduction details. Do not upload game archives, save files, conversations or tokens. New player features belong inside TES III Morrowind/OpenMW. The companion may run invisibly in the background; normal gameplay must not depend on a browser panel or a separate game.
