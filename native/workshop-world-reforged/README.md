# HALVETH Morrowind Workshop — World Reforged Candidate 0.4.1

This is a **native Windows EXE candidate** for the actual
Morrowind/OpenMW workshop. It is deliberately separate from the browser
learning world and from the preserved Workshop 0.2.0 installation.

The candidate creates an independent root with:

- a copied, hash-checked local OpenMW runtime;
- a `world-reforged` profile with its own configuration, runtime, local data
  and save directory;
- a local pointer to a World Reforged base patch and its corrective overlay;
- validation of the base plugin, the world shader and every manifest-bound
  overlay file before the profile is prepared or launched.
- the separately verified own HALVETH gameplay extension: knowledge, worldlife,
  perspective, authored books and spells, plus the atmosphere filter.

The public source tree contains **no** Bethesda game data, saves, OpenMW
binaries, texture packs, World Reforged assets, local absolute paths or
credentials. `LICENSE.txt` applies to this Workshop source. OpenMW and game
data retain their own licences and must be obtained and used lawfully.

## Build a local candidate

Run from this directory after installing a local OpenMW 0.51.0 runtime and
obtaining the locally held World Reforged inputs:

```powershell
python .\build_candidate.py `
  --output "$env:USERPROFILE\Games\HALVETH-Morrowind-Native\candidates\0.4.1-world-reforged-genesis" `
  --engine-source "$env:ProgramFiles\OpenMW 0.51.0" `
  --world-reforged-base "<LOCAL_WORLD_REFORGED_BASE_PATCH_DIR>" `
  --world-reforged-overlay "<LOCAL_WORLD_REFORGED_CORRECTIVE_OVERLAY_DIR>"
```

The output directory must be new or empty. This protects existing installs.
The generated `world-reforged-source.json` is local-only and contains local
input paths; do not commit it.

## Prepare the separate game profile

After the candidate exists, select `Morrowind.esm` from a complete data source
that you may use. The import creates a new checked data copy in the candidate:

```powershell
.\Morrowind-Workshop-WorldReforged.exe --import "<LOCAL_DATA_FILES_DIR>\Morrowind.esm"
.\Morrowind-Workshop-WorldReforged.exe --verify-world-reforged
.\Morrowind-Workshop-WorldReforged.exe --prepare world-reforged
.\Morrowind-Workshop-WorldReforged.exe --validate-profile world-reforged
.\Morrowind-Workshop-WorldReforged.exe --launch world-reforged
```

`--verify-world-reforged` proves only the declared local file binding. It does
not prove gameplay correctness, visual completeness or an FPS result.

## Bounded local scene probe

The optional scene probe creates a fresh folder below `probes/`, uses its own
OpenMW configuration, user data and local data, then starts a menu script that
requests a new game. A second global script observes player creation. After
that runtime marker appears, the local probe controller holds the engine open
for at least eight wall-clock seconds and asks its own child process to close. It is
intended to produce a narrow transition record, not a game benchmark:

```powershell
.\Morrowind-Workshop-WorldReforged.exe --probe-scene world-reforged 25
```

The resulting receipt records the process outcome plus the three runtime markers
`MENU_INIT`, `NEW_GAME_REQUESTED` and `SCENE_RUNNING`, if they were actually
seen in local probe logs. A status ending in
`_CONTROLLER_CLOSED` means that the controller observed `SCENE_RUNNING`, held
the child process for the recorded at-least-eight-second dwell and then requested its
close; it does not mean that Lua or OpenMW self-terminated. The watchdog
records a stop as a watchdog outcome; it is never treated as a successful scene
transition. A marker-complete record does not establish visual acceptance,
collision, save correctness, or an FPS measurement.

## Source checks

```powershell
python .\test_candidate.py
```

This compiles synthetic Core tests and renders the WinForms workshop offscreen.
It neither starts OpenMW nor reads a game data source, a save, or an asset pack.

## Candidate boundary

The candidate may become a separately reviewed local build after its source
checks and local input verification pass. It is not an installer, a release,
an overwrite of Workshop 0.2.0, or proof that every in-game placement, shader,
collision, quest, performance or visual surface is correct.
