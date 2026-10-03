# LEVIATH Workshop for an existing Morrowind world

Own Bash and gameplay additions for OpenMW 0.51.0. Your existing locally played
Morrowind world is the first world. This package contains source code and tests.
Morrowind game data, save games, downloaded asset archives and native runtimes
remain supplied separately by the player.

The rule model includes owner-controlled reception, a colosseum admission rule,
plain text mail, item deliveries kept in a hidden depot, a courier that follows
the owner's position over game days, and one-time acceptance of a delivery.
Its caller role values are declarations. Its tests do not prove authentication,
network reception or a complete engine integration.

## Git Bash commands

From this directory:

```bash
bash scripts/workshop.sh check
python -m unittest discover -s tests -v
bash scripts/workshop.sh plan "/path/to/your/isolated/profile"
bash scripts/workshop.sh play "/path/to/your/isolated/profile"
bash scripts/workshop.sh play "/path/to/your/isolated/profile" "/path/to/manual.omwsave"
```

`play` opens the engine menu unless an explicit save is given. It omits the
scripted native probes. The isolated profile must contain its own `runtime`
directory, `openmw.cfg`, `play.cfg`, and `settings.cfg`. The launcher restores
the previous configuration when the selected engine exits, including an engine
failure. A retained lock is reviewed manually after an abnormal OS shutdown.
The launcher does not choose a save from its modification time.

`WORKSHOP_PYTHON` chooses a Python 3.10+ executable. `WORKSHOP_ENGINE` chooses
an engine executable explicitly; the ordinary default is the selected profile's
own `runtime/openmw.exe` or `runtime/openmw`. `WORKSHOP_BASH` selects Bash for
the Python controller tests.

## Source-bound asset fetches

```bash
bash scripts/fetch-assets.sh list
bash scripts/fetch-assets.sh fetch kenney-impact .local/assets
```

The source manifest pins exact archive bytes by SHA-256. A changed download is
rejected for review. The fetcher does not extract archives, import a model,
install a package, or execute a downloaded file. The `.local` directory is
excluded from Git. Source files retain their own licenses; see
[source bindings](docs/SOURCE_BINDINGS.md).

## Evidence limits

Controller tests use mock engine and mock HTTP executables and never start a
game or contact a server. Native Lua/visual additions, when included, carry
their own engine-version bindings and finite test receipts. A declared API
test and a real native run are recorded separately. The work targets a more
modern experience; a complete 2027/2028 game overhaul is a continuing project.

Own source is MIT-licensed. The OpenMW engine and original game remain separate
works. The player's imported game data and saves do not enter this source bundle.

## Presentation module and Bash essences

`gameplay/` contains the own native courier adapter. In an isolated profile it
seeds one clearly identified synthetic parcel, keeps its weapon and own letter
in a disabled depot, dispatches a path-checked NPC after game days, and transfers
the parcel into the player's real inventory on F10 after arrival. Fourteen
native checks are recorded in [COURIER_NATIVE.json](docs/COURIER_NATIVE.json).
Remote visitor reception is a separate future adapter; the synthetic parcel is
not evidence of a remote visitor. Its own README explains installation and scope.

`presentation/` contains the own noninteractive player HUD, a procedural one-pixel
texture generator, and a Lua 5.1 harness with declared engine doubles. Generate
the texture with `python presentation/build-assets.py` before installing that
module. The generated texture remains a local build output. Register
`presentation/mod` as an OpenMW data directory and
`Veyra-Presentation.omwscripts` as content in an isolated profile.
The module's README records its own native and visual test scope.
The combined finite checks are listed in [NATIVE_SCOPE.md](docs/NATIVE_SCOPE.md).

`presentation/vegetation/` contains own deterministic tree geometry generation
and serialized mesh/plugin checks. Its bark input is separately licensed CC0
from Poly Haven. The source package includes only generator/checker/docs and
generic configuration examples; the input textures, original master and
generated model/plugin binaries remain local. See its README for dependencies,
additive placement first, and the wider scope of the optional static-class
override. Native appearance/collision acceptance is recorded separately.

`tools/essences.sh` supplies bounded temporary work, exact file snapshots,
verification, retained before/after differences, and saved-script pipelines.
`pin-version` binds an exact version command's first line before a build.
These are own implementations extracted as operating ideas. The package
contains no source bytes from deleted project archives or the recycle bin.

```bash
bash tests/check-essences.sh
VEYRA_TEST_LUA=lua5.1 bash presentation/CHECK_HUD.sh
python scripts/package.py
```
