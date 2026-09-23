"""OpenMW 0.51 graphics presets and optional local asset-manifest support.

Engine settings are bound to OpenMW/openmw tag openmw-0.51.0:
  files/settings-default.cfg
  docs/source/reference/modding/settings/{shaders,water,shadows,terrain,video}.rst
  components/settings/shadermanager.hpp and apps/openmw/engine.cpp
https://github.com/OpenMW/openmw/tree/openmw-0.51.0

Third-party uniforms are bound to the locally installed upstream shaders:
  zesterer/openmw-ssao fa5ec4303ee557b75e3c51c02ab14ff0334271c4
  zesterer/openmw-volumetric-clouds c8830bcd2de0f6e7355f91880308426203eded3c
  wareya/OpenMW-Shaders 76e0637187cc2878575528119aed72bbbf1a12cf
No shader source or third-party game asset is redistributed by this helper.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct


GRAPHICS_SECTIONS = ("Video", "Camera", "General", "Terrain", "Fog", "Shaders", "Water", "Shadows", "Post Processing")


def load_graphics_manifest(project: Path, state: Path, explicit: Path | None = None) -> dict:
    """Paths in dataDirectories are absolute or relative to the project root.

    Schema 1: {schemaVersion: 1, dataDirectories: [path, ...], shaders: [stem, ...]}.
    shaders is an ordered complete chain; omission uses built-in bloomlinear.
    Optional visualPlugins entries bind a basename and SHA-256. Only fully
    validated TES3 + BODY record files may add a visual content entry.
    """
    candidates = [Path(explicit).expanduser()] if explicit else [
        state / "graphics" / "install.json", project / ".local" / "graphics" / "install.json",
        project / "data" / "graphics-install.json",
    ]
    path = next((p.resolve() for p in candidates if p.is_file()), None)
    if explicit and path is None:
        raise FileNotFoundError(f"Graphics manifest is unavailable: {explicit}")
    data = {} if path is None else json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or (path and data.get("schemaVersion") != 1):
        raise ValueError("Graphics manifest must be a schemaVersion 1 JSON object.")
    values = data.get("dataDirectories", [])
    if not isinstance(values, list) or len(values) > 128:
        raise ValueError("Graphics dataDirectories must be a list of at most 128 directories.")
    directories = []
    for value in values:
        if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n\x00"):
            raise ValueError("Each graphics data directory must be a non-empty path.")
        candidate = Path(value).expanduser()
        candidate = (candidate if candidate.is_absolute() else project / candidate).resolve()
        if not candidate.is_dir():
            raise FileNotFoundError(f"Graphics data directory is unavailable: {candidate}")
        if candidate not in directories:
            directories.append(candidate)
    shaders = data.get("shaders", ["bloomlinear"])
    if not isinstance(shaders, list) or len(shaders) > 32 or any(
        not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,95}", name)
        or name.lower().endswith(".omwfx") for name in shaders
    ):
        raise ValueError("Graphics shaders must contain up to 32 shader filenames without extensions.")
    if len(shaders) != len(set(name.casefold() for name in shaders)):
        raise ValueError("Graphics shader chain contains duplicates.")
    plugins = data.get("visualPlugins", [])
    if not isinstance(plugins, list) or len(plugins) > 32:
        raise ValueError("visualPlugins must be a list of at most 32 BODY-only plugins.")
    seen = set()
    for plugin in plugins:
        if (not isinstance(plugin, dict) or not isinstance(plugin.get("file"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,119}\.(?:esp|esm)", plugin["file"], re.I)
                or ".." in plugin["file"] or not isinstance(plugin.get("sha256"), str)
                or not re.fullmatch(r"[a-fA-F0-9]{64}", plugin["sha256"])):
            raise ValueError("Each visual plugin needs an ASCII .esp/.esm basename and an exact SHA-256.")
        key = plugin["file"].casefold()
        if key in seen:
            raise ValueError("visualPlugins contains duplicate filenames.")
        seen.add(key)
    return {"path": str(path) if path else None, "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path else None,
            "directories": directories, "shaders": shaders, "visual_plugins": plugins}


def validate_visual_plugin(path: Path, expected_sha256: str) -> dict:
    """Walk every TES3 record/subrecord; the only payload record type is BODY."""
    limit = 16 * 1024 * 1024
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"Visual plugin exceeds 16 MiB: {path.name}")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256.lower():
        raise ValueError(f"Visual plugin SHA-256 mismatch: {path.name}")
    offset = 0
    records = {"TES3": 0, "BODY": 0}
    header_count = None
    while offset < len(raw):
        if len(raw) - offset < 16:
            raise ValueError(f"Truncated TES3 record header: {path.name}")
        kind, size, _unknown, _flags = struct.unpack_from("<4sIII", raw, offset)
        expected_kind = b"TES3" if offset == 0 else b"BODY"
        if kind != expected_kind:
            raise ValueError(f"Visual plugin contains a non-visual record {kind!r}: {path.name}")
        end = offset + 16 + size
        if end > len(raw):
            raise ValueError(f"TES3 record exceeds file bounds: {path.name}")
        sub = offset + 16
        while sub < end:
            if end - sub < 8:
                raise ValueError(f"Truncated TES3 subrecord header: {path.name}")
            tag, sub_size = struct.unpack_from("<4sI", raw, sub)
            sub_end = sub + 8 + sub_size
            if sub_end > end or not re.fullmatch(rb"[A-Z0-9_]{4}", tag):
                raise ValueError(f"Invalid TES3 subrecord bounds/tag: {path.name}")
            if kind == b"TES3" and tag == b"HEDR":
                if header_count is not None or sub_size != 300:
                    raise ValueError(f"Visual plugin needs exactly one 300-byte HEDR: {path.name}")
                header_count = struct.unpack_from("<I", raw, sub + 8 + 296)[0]
            sub = sub_end
        records[kind.decode("ascii")] += 1
        offset = end
    if records["TES3"] != 1 or not records["BODY"] or header_count != records["BODY"]:
        raise ValueError(f"Visual plugin HEDR count does not match its BODY records: {path.name}")
    return {"file": path.name, "path": str(path), "sha256": actual, "bytes": len(raw),
            "recordCounts": records, "headerRecordCount": header_count,
            "validation": "Full file walked; TES3 header and BODY records only; SHA-256 matched."}


def resolve_visual_plugins(graphics_directories: list[Path], plugins: list[dict], later_directories: list[Path] = ()) -> list[dict]:
    result = []
    for plugin in plugins:
        candidate = None
        key = plugin["file"].casefold()
        for directory in graphics_directories:
            matches = [p for p in directory.iterdir() if p.is_file() and p.name.casefold() == key]
            if len(matches) > 1:
                raise ValueError(f"Ambiguous visual plugin filename: {plugin['file']}")
            if matches:
                candidate = matches[0]
        if candidate is None:
            raise FileNotFoundError(f"Visual plugin absent from graphics data directories: {plugin['file']}")
        if any(p.is_file() and p.name.casefold() == key for directory in later_directories for p in directory.iterdir()):
            raise ValueError(f"Visual plugin is shadowed by a later data directory: {plugin['file']}")
        result.append(validate_visual_plugin(candidate, plugin["sha256"]))
    return result


def resolve_shaders(data_directories: list[Path], names: list[str]) -> dict[str, str]:
    """Match loose VFS shaders in actual load order, including engine defaults."""
    available = {}
    for directory in data_directories:
        for child in directory.iterdir():
            if child.is_dir() and child.name.casefold() == "shaders":
                for shader in child.iterdir():
                    if shader.is_file() and shader.suffix.casefold() == ".omwfx":
                        available[shader.stem.casefold()] = shader
    missing = [name for name in names if name.casefold() not in available]
    if missing:
        raise FileNotFoundError("Requested graphics shaders are missing: " + ", ".join(missing))
    return {name: str(available[name.casefold()]) for name in names}


def recommendations(profile: str, shaders: list[str]) -> tuple[dict, dict]:
    if profile not in {"beauty", "cinematic"}:
        return {}, {}
    cinematic = profile == "cinematic"
    cloud = "clouds" in shaders
    shader_aa = any(name.casefold() in {"followeraa", "fxaa"} for name in shaders)
    settings = {
        "Video": {"resolution x": "2560", "resolution y": "1440", "antialiasing": "0" if shader_aa else "4",
                  "framerate limit": "120", "vsync mode": "1"},
        "Camera": {"viewing distance": "131072" if cinematic else "81920", "reverse z": "true"},
        "General": {"anisotropy": "16", "texture mipmap": "linear", "texture mag filter": "linear", "texture min filter": "linear"},
        "Terrain": {"distant terrain": "true", "object paging": "true", "object paging active grid": "true",
                    "vertex lod mod": "1" if cinematic else "0", "composite map resolution": "2048" if cinematic else "1024"},
        "Fog": {"use distant fog": "false" if cloud else "true", "radial fog": "true",
                "sky blending": "false" if cloud else "true", "distant land fog start": "32768" if cinematic else "16384",
                "distant land fog end": "131072" if cinematic else "81920"},
        "Shaders": {"lighting method": "shaders", "force per pixel lighting": "true", "clamp lighting": "false",
                    "max lights": "64" if cinematic else "32", "maximum light distance": "16384" if cinematic else "12288",
                    "match sunlight to sun": "true", "apply lighting to environment maps": "true",
                    "auto use object normal maps": "true", "auto use terrain normal maps": "true",
                    "auto use object specular maps": "true", "auto use terrain specular maps": "true",
                    "classic falloff": "false", "minimum interior brightness": "0.16", "soft particles": "true",
                    "antialias alpha test": "false" if shader_aa else "true"},
        "Water": {"shader": "true", "refraction": "true", "rtt size": "4096" if cinematic else "2048",
                  "reflection detail": "5" if cinematic else "4", "rain ripple detail": "2",
                  "sunlight scattering": "true", "wobbly shores": "true", "refraction scale": "1.0"},
        "Shadows": {"enable shadows": "true", "shadow map resolution": "8192" if cinematic else "4096",
                    "number of shadow maps": "3", "maximum shadow map distance": "24576" if cinematic else "16384",
                    "shadow fade start": "0.85", "actor shadows": "true", "player shadows": "true",
                    "terrain shadows": "true", "object shadows": "true", "compute scene bounds": "bounds"},
        "Post Processing": {"enabled": "true" if shaders else "false", "chain": ",".join(shaders),
                            "transparent postpass": "true", "auto exposure speed": "0.6"},
    }
    # OpenMW loads <user config>/shaders.yaml through yaml-cpp. Plain JSON is
    # valid YAML and avoids another Python dependency. Values match upstream
    # uniform types and declared ranges; all are editable via the F2 menu.
    uniforms = {
        "ssao": {"cfg_samples": 48 if cinematic else 30, "cfg_intensity": 3.5, "cfg_radius": 100.0,
                 "cfg_temporal_filtering": 0.75, "cfg_blur_factor": 1.0},
        "clouds": {"sampling_quality": 1.5 if cinematic else 0.0, "cloud_detail": 3,
                   "mist_density": 0.18 if cinematic else 0.12, "interior_mist": 0.025, "point_glow_intensity": 0.2,
                   "replace_skybox": False},
        "bloomlinear": {"uStrength": 0.12 if cinematic else 0.08, "uThreshold": 0.5, "uRadius": 0.4},
        "hdr_linear": {"neutral_point": 0.335, "sensitivity": 0.11, "max_exposure": 1.25},
        "FollowerAA": {"uRange": 6.0 if cinematic else 5.0, "uMSAACompatibilityHack": 0.0},
    }
    return settings, {name: uniforms[name] for name in shaders if name in uniforms}
