# Setup on your own computer

## Background companion

Python 3.11+ with SQLite runs the local companion. Normal launch starts it in the background and opens Morrowind directly. F6 opens the native character/inventory/magic/encounter view, F7 the knowledge journal, and F8 conversations. A clickable bar in the normal inventory and dialogue also opens these views. Ollama is optional: model conversations require an already installed model, while native inspection, books, spells and learning continue offline. No dependency or model downloads happen automatically. `python launcher.py --companion-only` starts the configured background service without opening a browser or game window.

## Installation layout

The profile helper was designed for a HALVETH-style OpenMW bundle:

```text
<install-root>/
  engine/openmw.exe       (engine/openmw on Linux)
  engine/resources/
  profiles/<source-profile>/openmw.cfg
  profiles/<source-profile>/settings.cfg
```

Use OpenMW 0.51.0 with its matching runtime resources and your own configured Morrowind data. The profile helper preserves the source configuration's content order. The source `openmw.cfg` must have valid `data=` paths; `?user?` and other unresolved OpenMW path tokens are not supported by this helper. Use absolute paths or paths relative to the source profile. A `user-data=` path is needed only for opt-in save copying.

If your existing OpenMW installation has a different layout, first create a separate bundle directory using your own installed runtime and a copy of your own configuration, then adapt the copied data paths. Do not move your existing installation or overwrite its configuration. Automatic discovery/import of every standard Steam/GOG/OpenMW layout is not implemented in this release.

An alternative for experienced modders is to add the repository's absolute `mod/` folder and `content=halveth.omwscripts` to a separate OpenMW configuration. Ensure `mod/bridge/inbox.json` exists as `{"sequence":0,"sessionId":""}` before startup. Redirect that game's stdout to a local file and point the companion's `--log` at the same file; see the direct launch example below.

## Native launcher

```console
python launcher.py --play --install-root "D:/Games/MyOpenMW" --source-profile max --model hermes3:8b --save-config
```

This stores only installation, source profile and model choices in ignored `local-config.json`. Later `START.cmd` / `python launcher.py` uses them and starts the game directly. Save copying is **off by default**. Add `--copy-saves` deliberately for a run to copy existing saves once; this choice is never persisted. The launcher imports neither Tk nor a browser. It retains the Windows process check; native Linux gameplay is not claimed tested.

On Windows, `scripts/build_native_entry.py` can extend an existing HALVETH native Workshop source checkout containing `Core.cs`, `Workshop.cs` and `app.manifest`. Pass its directory with `--native-source`. The helper uses the installed .NET compiler and Framework references; alternate locations can be supplied with `--compiler` and `--framework`. This public package includes `GenesisEntry.cs`, not a complete bundled engine or the legacy Workshop sources. A successful build creates an isolated candidate EXE and local path configuration under ignored `.local/native-entry-candidate/`; it does not replace the installed launcher or shortcuts. `--check-genesis beauty` checks that candidate's bound local entry files without starting the game; `--genesis beauty` invokes the direct game route. Runtime and configuration files remain separate on disk behind the single visible entry.

Close a manually started companion on port 18765 before using the launcher's companion startup: the launcher reuses an already running service, so an unrelated log/model configuration will not change automatically.

## Direct CLI route

Prepare the separate profile, enable the original banner if wanted, and index your own game data:

```console
python scripts/install_scarlet_banner.py apply
python scripts/prepare_profile.py --install-root "D:/Games/MyOpenMW" --source-profile max --profile beauty
python scripts/import_lore.py --config .local/profiles/beauty/openmw.cfg --state-dir .local
```

Start the companion in terminal A:

```console
python server.py --log .local/profiles/beauty/openmw.stdout.log --model hermes3:8b
```

Launch the game in terminal B:

```console
python scripts/prepare_profile.py --install-root "D:/Games/MyOpenMW" --source-profile max --profile beauty --launch
```

The direct helper uses `.local/profiles/beauty/openmw.stdout.log`; the native launcher uses `.local/game.stdout.log`. The companion and game must refer to the same log. Both use `mod/bridge/inbox.json` by default. Only one active game/companion pair should use a mailbox at a time.

## Functional tests with your own game

`python -m unittest discover -s tests -v` needs neither game nor model. A fresh isolated in-engine check is separate:

```console
python scripts/prepare_profile.py --install-root "D:/Games/MyOpenMW" --source-profile max --profile beauty --smoke
```

Smoke mode uses a disposable scene and cannot be combined with `--copy-saves`. Native scripts in `tests/integration_*.py`, `graphics_preview.py` and `scarlet_preview.py` are developer tools for configured local installations. Inspect their CLI options and installation assumptions before running them. Public CI does not launch a game or call a paid service.
