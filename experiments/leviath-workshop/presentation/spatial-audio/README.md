# Veyra Spatial Audio 0.1.0

This isolated OpenMW 0.51/API129 candidate adds a short spatial bell to the
actual arriving courier. It reads `I.VeyraCourier.status()` and waits for
`phase=ARRIVED`, a valid courier ID and that enabled actor in
`world.activeActors`. It requests one non-looping 3D sound on that actor,
with volume 0.30 and pitch 1.0. Save/load retains the last requested courier
ID so that the same delivery does not repeat its bell on reload.

The module has no inventory operation, actor mutation, external connection,
key binding or music replacement. A missing courier module stays a usable
optional dependency. Muted/disabled audio, pause and inactive courier defer
the request. An invalid saved audio state remains `LOAD_HOLD`, including
after another save; it is not silently replayed.

## Separate profile integration

Load the courier module first, then append these lines to the isolated
candidate profile's `openmw.cfg` and `play.cfg`:

```ini
data="<absolute-path-to-presentation-candidate>/spatial-audio/mod"
content=Veyra-Spatial-Audio.omwscripts
```

Use forward slashes in Windows paths. The generated WAV must exist at
`mod/Sound/veyra/courier_bell_mono.wav`. Removing these two lines disables
this audio adapter. The courier mechanic remains a separate module.

The script uses the global context because OpenMW's local sound API can
attach 3D sound only to `self`. `I.VeyraSpatialAudio.getState()` returns a
detached snapshot with the request count, current courier phase/ID,
`lastReadAtGameTime`, requested game time and the engine playback query.
`PLAY_REQUESTED` records a successful API call; `PLAYING` records the
engine's `isSoundFilePlaying` result. Both are distinct from audible output.

## Rebuild without another download

`build-audio.py` takes an existing local Kenney source archive and an
existing FFmpeg executable. It rejects an archive, selected OGG or license
whose SHA256 differs from its pinned contract. Source extraction is limited
to those two named members. A temporary decoder input/output is removed
after conversion. No source files or other sound directories change.

```bash
python build-audio.py --archive /path/to/kenney_impact-sounds.zip \
  --ffmpeg /path/to/ffmpeg
```

The stereo source is downmixed as `0.5*left + 0.5*right` to mono PCM16 at
44.1 kHz; mono permits positional playback. There is no normalization.
`ASSET_RECEIPT.json` binds the source archive/member/license, generator,
decoder executable/version, resulting WAV and measured PCM format. The
local result has 65,276 frames, duration 1.480181 seconds and no samples at
the PCM16 clipping limits. This does not prove listening quality.

## Checks and audible acceptance points

`check-audio.lua` contains eleven Lua5.1 model checks. They cover exact
arrival gating, actual actor attachment, once-per-courier behaviour,
saved deduplication, a later courier, disabled/inactive defer, pause,
optional source failures, decoder failure, detached snapshots and invalid
save hold. They use declared engine doubles. The separate
[native audio receipt](../../docs/AUDIO_NATIVE.json) binds the same production
source to engine playback on the actual arriving courier. Eleven distinct
assertion names produced 22 PASS log lines, including repeated HUD polls.
It observed one request, `isSoundFilePlaying`, no repeat after playback,
actual item claiming and the arrival-footer transition. A coordinating-agent
image review saw the readable footer and 40/40 health. Human audition and
native saved-arrival deduplication remain pending.

```bash
VEYRA_TEST_LUA=/path/to/lua51 bash CHECK_AUDIO.sh
```

For an isolated native delivery, verify these specific observations:

1. `APPROACH` has no bell request. `ARRIVED` has exactly one
   `VEYRA_AUDIO|kind=PLAY_REQUESTED` log entry for that courier ID.
2. An immediate following probe can observe `PLAYING` while the 1.48-second
   sample runs. This brief window needs a poll faster than the sample.
3. Listen at arrival with the courier off-centre, then repeat with an
   identical isolated fixture on the other side. Check that the sound
   position follows the courier and that the level is comfortable against
   footsteps/music. Turn the camera during the cue if the sample permits.
4. Saving/reloading that arrival must not request another bell; claiming
   the gift changes no audio or music settings.

The soundtrack, voices, ambient water and general NPC animation remain
separate improvement branches. The already inspected Kenney Nature Kit
contains models rather than water recordings; it is not presented here as
a source for an unobserved water sound.

## Sources and license

- [Kenney Impact Sounds, publisher page and CC0 license](https://kenney.nl/assets/impact-sounds)
- [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)
- [OpenMW 0.51 core sound API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_core.html)
- [OpenMW 0.51 active actor API](https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html)

The Lua, Bash and Python source uses the parent package's MIT license,
also copied to `LICENSE`. The derived audio remains CC0; the archive's
original `KENNEY-LICENSE.txt` is preserved. Credit: Kenney, Impact Sounds
1.0, `impactBell_heavy_000.ogg`. Game data and game licensing remain separate.
