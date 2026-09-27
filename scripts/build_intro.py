"""Render the owned portal illustration as OpenMW's silent new-game movie.

This is a short pre-rendered transition, not a change to game-world geometry.
Requires ffmpeg on the build machine; playback requires only OpenMW.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "mod/Textures/halveth/portal-menu-2100.png"
OUTPUT = ROOT / "mod/Video/new_game.webm"
FRAMES = 96
FILTER = (
    "scale=1344:758:flags=lanczos,"
    "zoompan=z='min(zoom+0.0009,1.0864)':"
    "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
    "d=1:s=1280x720:fps=24,"
    "fade=t=in:st=0:d=0.35,fade=t=out:st=3.55:d=0.45,"
    "format=yuv420p"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Inspect the rendered movie without rewriting it")
    args = parser.parse_args()
    if not SOURCE.is_file():
        parser.error(f"Missing owned source image: {SOURCE}")
    if not args.check:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-framerate", "24", "-i", str(SOURCE),
            "-vf", FILTER, "-frames:v", str(FRAMES),
            "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "28",
            "-deadline", "good", "-cpu-used", "3", "-an",
            "-map_metadata", "-1", str(OUTPUT),
        ]
        subprocess.run(command, check=True)
    if not OUTPUT.is_file():
        parser.error(f"Missing movie: {OUTPUT}")
    details = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,nb_frames,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1", str(OUTPUT)],
        check=True, capture_output=True, text=True,
    ).stdout
    if "codec_name=vp9" not in details or "width=1280" not in details or "height=720" not in details:
        raise RuntimeError(f"Unexpected WebM video properties:\n{details}")
    print(f"HALVETH_INTRO_PASS sourceSha256={sha256(SOURCE)} "
          f"movieSha256={sha256(OUTPUT)} bytes={OUTPUT.stat().st_size}")
    print(details.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
