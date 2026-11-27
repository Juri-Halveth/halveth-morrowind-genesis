# Source and engine bindings

Snapshot date: 2026-10-03. The existing project is
[halveth-morrowind-genesis](https://github.com/Juri-Halveth/halveth-morrowind-genesis).
The package is intended for `experiments/leviath-workshop/` in that repository.

| Component | Bound source | License | Verification scope |
| --- | --- | --- | --- |
| Own Bash controller | `scripts/workshop.sh` | MIT | Mock process, isolated configuration restoration, explicit save arguments, probe exclusion |
| Own profile provisioner | `scripts/provision.sh`, `scripts/provision.py` | MIT | Ordered bound configurations, external runtime inputs, new own copies and generated HUD asset; no game execution |
| Own field workshop | `gameplay/mod/scripts/veyra_fieldwork/` | MIT | Four source files bound to nineteen new-job, five completed-reload and six working-reload native checks |
| Own asset fetcher | `scripts/fetch-assets.sh` | MIT | Mock HTTP, digest comparison, partial cleanup, existing-byte preservation |
| Own delivery rule model | `rules/policy.py`, version 0.2.0 | MIT | Pure declared-input state transitions; no sockets or engine calls |
| Own courier | `gameplay/mod/scripts/veyra_courier/`, version 0.2.3 / save schema 2 | MIT | Five source files bound to seven native runs: new parcel, existing stack, transfer reload, two current reloads and two historical migrations |
| Own HUD | `presentation/mod/scripts/veyra/hud.lua`, version 0.1.3 | MIT | OpenMW 0.51.0/API129 stats and UI; Lua 5.1 doubles and separately bound native observations |
| Own spatial bell adapter | `presentation/spatial-audio/` | MIT own code; CC0 audio input/derivative | Arrival-gated global sound attachment; generator pins archive, selected member and license member independently |
| OpenMW | [0.51.0 release](https://openmw.org/2026/openmw-0-51-0-released/) | Separate upstream engine license | Existing native engine version; not redistributed in this bundle |
| Kenney Impact Sounds | [Source page](https://kenney.nl/assets/impact-sounds) | CC0 | Download digest pinned; license inspected in original source archive |
| Kenney Nature Kit | [Source page](https://kenney.nl/assets/nature-kit) | CC0 | Download digest pinned; license inspected in original source archive |
| Joth Fantasy Orchestral Theme | [Source page](https://opengameart.org/content/fantasy-orchestral-theme) | CC0 | Source page license and downloaded bytes bound; music direction still open |
| Poly Haven Bark Brown 02 | [Rob Tuytel source page](https://polyhaven.com/a/bark_brown_02), [license](https://polyhaven.com/license) | CC0 | Existing input bound by source metadata and hashes; only own generator is distributed |

SHA-256 binds downloaded bytes. It does not independently authenticate a creator,
prove license ownership or establish the suitability of a model for a game rig.
The downloader's filename is separate from its content type. Downloaded asset
archives are local inputs and are excluded from the public source manifest.

Native Lua additions bind OpenMW 0.51.0 / Lua API 129 where declared by their
source modules. Engine calls are checked against official versioned
[Lua API documentation](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/interface_ai.html).
An upstream API contract is distinct from a native run observed with this exact
module. Probe code is registered separately from playable code.
