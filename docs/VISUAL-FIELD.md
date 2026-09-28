# Native graphics field

The optional OpenMW development scene compares existing game objects on one
continuous floor. Individual square platforms were removed. Its first page has
three generated study NPCs with native travel AI, followed by thirteen visual
objects. Existing quest actors and saved characters are not loaded or changed.

The spacing starts at 2200 game units and can be changed from 1600 to 10000.
Static records are paged sixteen at a time. The number of pages depends on the
locally loaded game data; the inspected installation supplied 3563 entries.
This is bounded paging, not infinite geometry or a claim that every object has
been redesigned.

The three study actors walk across former display positions. An independent
branch diagram progresses through four visible growth steps at eight-second
intervals. These diagrams illustrate deterministic branching and geometric
reflection. They do not rewrite character meshes, represent physical roots or
establish any relationship between hashes and biology.

Clickable native controls above the scene switch the camera, select objects,
orbit, change spacing, advance pages and grow the branch diagrams. The same
operations have keyboard alternatives:

- N: overall view or selected object; the close camera follows study actors.
- Arrow keys: select an object.
- Q/E: orbit the selection.
- Plus/minus: increase/decrease spacing.
- Page Up/Page Down: object page.
- G: manually advance the branch diagram. T and F10 retain their native roles.

`scripts/preview_visual_field.py` takes an installed engine root and an explicit
local graphics manifest. Its default run lasts 90 seconds and verifies all
four growth stages, three moving actors, sixteen created objects and a clean
engine exit. `--interactive` leaves the field open without a timer. Each run
uses a fresh `--tag` so previous observations remain available. Use the ordinary
Morrowind shortcut for the actual game.

The Lua modules under `tools/visual_field` and generated display geometry are
original source. Third-party character meshes, textures, game masters and
private runtime receipts stay outside the public source package.

Native observation on OpenMW 0.51: all three study actors travelled farther than
one initial 2200-unit interval, all four growth stages appeared, and the engine
exited without a Lua or shader error. This verifies the comparison scene; it is
not a full-world visual or performance assessment.
