# World Reforged EXE Candidate 0.3.1 — Status

`CANDIDATE`, source branch only. This directory builds a native Windows
WinForms/OpenMW workshop executable; it is not the browser learning world.

| Surface | State | Bound evidence / limit |
| --- | --- | --- |
| Existing Workshop 0.2.0 | `PRESERVED` | It is never overwritten by this source tree or its builder. |
| Candidate profile | `IMPLEMENTED_SOURCE` | `world-reforged` has its own runtime, configuration, local data and save path. |
| World Reforged 1.2.0 base | `LOCAL_INPUT_REQUIRED` | Bound by `LUCINET-World-Reforged.esp` SHA-256 `9805d32df3fe67406ddae40e4ef39929d7bc149d7fac04bd462e7a4bf4f71748`. |
| World Reforged 1.2.1 corrective overlay | `LOCAL_INPUT_REQUIRED` | Every declared overlay file must match its local `MANIFEST.json`. |
| Native EXE | `BUILD_CANDIDATE` | The builder creates a new non-empty-safe destination and copies a local OpenMW runtime. |
| Game-data import | `NOT_RUN_BY_SOURCE_TEST` | It remains a separate, SHA-256-checked copy action into the candidate. |
| Isolated scene probe | `LOCAL_RUN_OBSERVED` | A World Reforged-only probe writes its own config, user data, scripts and receipt below `probes/<id>`. On 2026-10-12 it observed `MENU_INIT`, `NEW_GAME_REQUESTED` and `SCENE_RUNNING`, held the child engine for at least eight recorded wall-clock seconds, then requested close; the child exited `0` without watchdog. See `evidence/SCENE-PROBE-RUN-2026-10-12.md`. |
| Gameplay / FPS / visual acceptance | `NOT_PROVEN` | Source tests prove synthetic checks and an offscreen workshop render, not a full game session or target-machine performance. |

Historic isolated World Reforged runs remain historical finite snapshots. This
candidate does not reclassify them as a new installation or a complete visual
acceptance result.
