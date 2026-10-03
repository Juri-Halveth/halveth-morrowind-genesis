# New owned profile from bound inputs

`scripts/provision.sh` is a Git Bash wrapper for the own Python adapter. It
creates a new destination containing `profile/`, copied `modules/`, the own
license and a private `INSTALL_RECEIPT.json`. No engine is launched by plan
or apply. Python 3.10+ and Git Bash are required for that wrapper.

The CLI accepts `plan|apply --base-profile PATH --engine PATH --destination
NEW --modules courier,hud,fieldwork[,audio]`. `--expect-plan DIGEST` can bind
apply to the exact reviewed input/destination plan. Unknown or repeated module
names and missing dependencies are rejected. Production registration is
copied separately; native probe fixtures are excluded.

The base profile supplies `play.cfg`, or `openmw.cfg` if no play configuration
is present, and `settings.cfg`. The selected executable supplies its adjacent
`openmw.cfg` bootstrap and explicitly bound resources directory. Nested base
`config=` inputs must be resolved before provisioning. Automatic startup
commands, skip-menu probes and known probe registrations are rejected.

When present, `shaders.yaml` and `input_v3.xml` are separately hashed and copied
as distinct regular files, preserving the base's shader chain and native key
bindings. Each optional input has a 256 KiB limit; links and non-files are
rejected. Missing optional inputs are allowed. Global/player storage, logs,
navmesh caches and save games are never copied automatically.

The parser keeps ordered repeated lines. It snapshots required bootstrap
fallback/content/archive/encoding inputs, anchors relative bootstrap data to
the engine directory, anchors relative base data to the base profile and
preserves the order of base content and fallback declarations. Existing base
`data-local` assets become an external read-only data reference. Fresh owned
`user-data` and `data-local` directories receive future generated data.
OpenMW path quotes and its ampersand escapes are handled explicitly;
unresolved path tokens are rejected. Windows configurations need Windows
Python; the Bash wrapper converts its three path arguments with `cygpath`.

Each copied source input, both configurations, settings and executable are
hashed in the plan, then checked before and after copying. The destination
must be new and must not overlap the base profile, engine, resources, data
inputs or this source package. Resolved directory aliases remain within that
guard. Copies are ordinary new files and never
hardlinks. On failure only a freshly created, nonce-marked staging directory
with its verified absolute anchor is cleaned up. The requested final target
and protected input directories are never recursively removed.

The HUD generator and pixel checker run only in the new module copy. The
optional audio module requires a previously generated mono PCM WAV, its exact
output receipt, pinned Kenney source/archive/license digests and the matching
original CC0 license text. It performs no download or decoder installation.

The launcher then selects this profile explicitly as `--replace config
--config PROFILE`, with its working directory set to the selected engine's
directory. Engine bootstrap files and hardlinked copies remain inputs.
Mock regression tests cover restored profile configuration on process success
and failure, an external engine with sibling profile/runtime directories,
exact explicit-save arguments, hardlink identities and spaces in paths.
Installer tests also cover repeated-line order, changed inputs, new-destination
guards, partial-copy cleanup, source-only audio rejection, local HUD generation
and the Bash wrapper's reviewed-plan mismatch.
An additional regression binds optional shader/key files, their source hardlink
identity, distinct output copies and exclusion of private storage/log/save files.

Configuration copying and mock regression passes are distinct from a native
game run. A provisioned profile reports `nativeAcceptance=NOT_RUN`; its real
engine and imported game/mod compatibility need a separately bound observation.
The [source-bound native menu observation](PROVISION_NATIVE.json) subsequently
started one new profile through the public Bash controller. Its menu was seen
at 2560x1440, a targeted own-window close produced exit 0, configuration was
restored, the lock was removed and original inputs/copied modules stayed
unchanged. Shader and key copies were present. This run loaded no save and
does not establish integrated gameplay for the selected modules.
Local plans/receipts are private because they contain exact machine paths.

Engine configuration contract:
[OpenMW 0.51.0 configuration paths](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/modding/paths.html).
