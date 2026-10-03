# Finite validation scope

This source package records distinct finite checks:

1. Eleven Python rule tests bind the declared local reception/depot/courier
   model. Caller strings are declared roles; no network endpoint is present.
2. Fourteen controller/download tests run with fake engine and fake HTTP
   executables. They check spaces in paths, original configuration restoration
   after successful and failed starts, restoration after a failed configuration
   copy, known probe exclusion, explicit saves, retained stale locks, pinned
   download bytes, failure cleanup, external engine selection and unchanged
   hardlinked bootstrap inputs. The current fourteen passed in Linux Bash and
   native Windows Git Bash. They do not measure game frame rates or render a scene.
3. Thirteen Lua 5.1 HUD tests use declared engine packages. Native HUD rendering and
   API integration are a separate observation, recorded when a real engine run
   with the exact source digest is available.
4. Eleven Lua 5.1 spatial-audio tests use declared engine packages. They bind
   arrival gating, one request per courier, save-backed deduplication, inactive
   and paused deferral, failure handling and detached snapshots. They do not
   measure emitted sound or human listening quality.
5. The procedural PNG checker binds complete white RGBA pixels, dimensions,
   chunk order, CRCs and the generator's exact output. A valid PNG structure
   does not itself prove successful native texture loading.
6. Eight provisioning tests use disposable profile/runtime fixtures. They bind
   ordered repeated configuration lines, preserved input bytes and hardlink
   identity, new destination guards, changed-input refusal, staged copy cleanup,
   source-only audio refusal, HUD generation in an own copy, Bash path quoting
   and distinct optional shader/key copies with private storage/log/save exclusion.
   No real engine is launched by those tests.

The separate [native profile menu run](PROVISION_NATIVE.json) starts the actual
engine through the public Bash controller with an explicit newly provisioned
profile. A coordinating-agent image review saw its real menu at 2560x1440.
One own-window close ended with exit 0, restored the configuration and removed
the profile lock. Fourteen original input files and all copied modules retained
their digests; the exact controller/provisioner source stayed unchanged.
The run opened no save and makes no integrated gameplay claim. An earlier
monitor mistook the engine's own crash-monitor child for a second main process;
that partial observation remains a separate historical record.

The Bash essence harness checks file snapshots/verification, a rejected nested
manifest, temporary cleanup after successful and failed commands, retained
before/after differences, and exact tool-version first-line binding.

The source packaging tool checks an explicit own-source allowlist and bounded
text patterns. ZIP construction checks exact source-byte roundtrips and CRCs.
Six synthetic publication-boundary tests check omitted game/private files,
rejected machine paths, rejected key/token strings, rejected binary bytes,
refusal to release a package missing a registered production module and
refusal to bind an old native receipt to changed production source.
Those checks bind file content and declared contracts. They do not constitute
a complete system audit, authentication proof or production equivalence.

The [courier receipt](COURIER_NATIVE.json) records fourteen native checks in
OpenMW 0.51.0: a disabled depot, delayed dispatch, real NPC creation/approach,
the actual inventory transfer of both items, and an ignored duplicate claim.
The fixture uses accelerated game time and a single synthetic parcel. Its five
production module files are bound by exact source digests.

The separate [claimed reload receipt](COURIER_RELOAD_NATIVE.json) records five
native checks: restored claimed state, depot and courier references, the actual
inventory item, and rejection of a duplicate award after reload. The separate
[depot reload receipt](COURIER_DEPOT_RELOAD_NATIVE.json) records four native
checks: restored pre-dispatch state, two actual disabled-depot items, no early
courier and no early award. All three observations bind the same five production
source files of version 0.2.3, OpenMW 0.51.0/API129 and one synthetic parcel. They share the same
local engine and fixture provenance; they are separate runs within that scope.

The [existing-stack observation](COURIER_STACK_NATIVE.json) records sixteen
checks with a retained fully conditioned, unenchanted Daedric longsword stack:
the real stack identity stayed, its count grew from one to two and a duplicate
claim gave nothing. The [transfer reload](COURIER_TRANSFER_RELOAD_NATIVE.json)
records five checks after saving during the actual TRANSFERRING phase. The
saved pre-transfer identities, quantities and item states resumed the stack
mapping after reload. These tests bind the repaired version 0.2.3; the prior
version's TRANSFERRING hang remains a historical failed run.

Separate [claimed migration](COURIER_CLAIMED_MIGRATION_NATIVE.json) and
[depot migration](COURIER_DEPOT_MIGRATION_NATIVE.json) record five and four
checks when opening schema-1 saves with the current schema-2 implementation.
Actual references stayed and premature/repeated claims awarded no item.
An old schema-1 TRANSFERRING save without a pre-transfer witness retains
TRANSFER_HOLD rather than inventing an unobserved inventory mapping.

HUD 0.1.3 uses the own 32x32 PNG introduced in 0.1.2 and checks paused-frame
UI hiding even when the update delta is zero. The historical TGA
run failed the native loader with code 1 after the HUD initialization message.
The original source ZIP and first freeze record are retained. The current
[combined native receipt](PRESENTATION_NATIVE.json) binds HUD 0.1.3 and its PNG
to seventeen real engine checks with exit 0: actual stat reads and changes,
visible-state snapshots, paused menu hiding, restoration and a prototype tree
pair at the same specimen position. Subsequent coordinating-agent screenshot
review observed readable 39/40 health and the panel hidden in the native menu
at 1920x1080. This is distinct from user approval or universal screen-size fit.
The tree was decoded and visible and had a named one-ray collision observation.
Ground contact, world-wide overrides and additional variants remain unproven.
The older nine-check PNG run timed out in its paused-menu fixture; it remains
a historical partial run, distinct from the completed current source observation.

The field workshop's [new job](FIELDWORK_NATIVE.json),
[completed reload](FIELDWORK_DONE_RELOAD_NATIVE.json) and
[in-progress reload](FIELDWORK_WORKING_RELOAD_NATIVE.json) bind nineteen, five
and six native checks to the same four production files. The engine created
the plot/workbench, debited seed/input inventory, advanced game-time jobs,
awarded the expected crop/ration record once and retained job state on reload.
The ration's consumption and active magic effect remain untested.

Arbitrary item condition/charge/soul combinations, interference by other mods
during transfer, all navigation meshes/interiors, long-run frame pacing,
complete campaigns, visitor networking
and cross-server authentication require their own checks.
