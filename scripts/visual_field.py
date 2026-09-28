"""Bounded, native OpenMW visual field. Reuses licensed assets at runtime only.

Produces an empty interior, original display meshes and Lua preview scripts in a
new directory. It never edits a master, game save or normal launch profile.
Roots are a geometric reflection; SHA-256 is used only to identify output bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
CELL = "HALVETH Visual Field"
PAGE_SIZE = 16


def layout(index: int, gap: float = 2200) -> tuple[float, float, float]:
    if type(index) is not int or not 0 <= index < PAGE_SIZE:
        raise ValueError("Index must be an integer in 0..15")
    if not math.isfinite(gap) or not 1600 <= gap <= 10000:
        raise ValueError("Gap must be finite and in 1600..10000 game units")
    return ((index % 4 - 1.5) * gap, (index // 4 - 1.5) * gap, 0)


def time_projection(t: float, mode: str) -> float:
    if not math.isfinite(t) or not 0 <= t <= 1:
        raise ValueError("Time position must be in 0..1")
    if mode == "linear":
        return t
    if mode == "log":
        return math.log1p(15 * t) / math.log(16)
    raise ValueError("Unknown time projection")


def branches(seed: int, stage: int):
    """Finite deterministic model; paired crown/root segments, never negative hashes."""
    if type(seed) is not int or not 0 <= seed <= 15:
        raise ValueError("Seed must be in 0..15")
    if type(stage) is not int or not 0 <= stage <= 4:
        raise ValueError("Stage must be in 0..4")
    crown = []
    def grow(p, length, yaw, lean, level):
        q = (p[0] + math.sin(yaw) * length * math.sin(lean),
             p[1] + math.cos(yaw) * length * math.sin(lean),
             p[2] + length * math.cos(lean))
        crown.append((p, q))
        if level < stage:
            for side in (-1, 1):
                grow(q, length * .72, yaw + side * (.53 + seed * .011),
                     min(1.1, lean + .23), level + 1)
    grow((0, 0, 0), 100, seed * .37, .05, 0)
    roots = [(tuple((x, y, -z)), tuple((u, v, -w)))
             for ((x, y, z), (u, v, w)) in crown]
    return crown, roots


def mesh(vertices, triangles, color):
    coords = " ".join(f"{v:.5f}" for point in vertices for v in point)
    faces = " ".join(str(v) for tri in triangles for v in tri)
    rgba = " ".join(str(v) for v in (*color, 1))
    return f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><created>2026-09-28T00:00:00Z</created><modified>2026-09-28T00:00:00Z</modified><unit meter="1" name="gameunit"/><up_axis>Z_UP</up_axis></asset>
<library_effects><effect id="fx"><profile_COMMON><technique sid="common"><lambert><emission><color>{rgba}</color></emission><diffuse><color>{rgba}</color></diffuse></lambert></technique></profile_COMMON></effect></library_effects>
<library_materials><material id="material"><instance_effect url="#fx"/></material></library_materials>
<library_geometries><geometry id="shape"><mesh><source id="positions"><float_array id="coords" count="{len(vertices)*3}">{coords}</float_array><technique_common><accessor source="#coords" count="{len(vertices)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source><vertices id="verts"><input semantic="POSITION" source="#positions"/></vertices><triangles count="{len(triangles)}" material="surface"><input semantic="VERTEX" source="#verts" offset="0"/><p>{faces}</p></triangles></mesh></geometry></library_geometries>
<library_visual_scenes><visual_scene id="scene"><node id="object"><instance_geometry url="#shape"><bind_material><technique_common><instance_material symbol="surface" target="#material"/></technique_common></bind_material></instance_geometry></node></visual_scene></library_visual_scenes><scene><instance_visual_scene url="#scene"/></scene></COLLADA>'''


def branch_mesh(seed, stage):
    vertices, triangles = [], []
    for a, b in sum(branches(seed, stage), []):
        # Crossed narrow strips have visible area from every azimuth. These are
        # diagram guides in the development cell, not replacements for flora.
        for axis in (0, 1):
            base = len(vertices)
            for point, side in ((a, -1), (a, 1), (b, 1), (b, -1)):
                p = list(point); p[axis] += side * 1.6; vertices.append(p)
            triangles.extend([(base, base+1, base+2), (base, base+2, base+3),
                              (base+2, base+1, base), (base+3, base+2, base)])
    return mesh(vertices, triangles, (.22, .46, .4))


def ground_mesh():
    """One continuous floor, with no per-object walls, boxes or raised platforms."""
    segments = 128
    vertices = [(0, 0, -2)] + [
        (5600 * math.cos(i*2*math.pi/segments),
         5600 * math.sin(i*2*math.pi/segments), -2) for i in range(segments)]
    triangles = [(0, i+1, (i+1) % segments+1) for i in range(segments)]
    return mesh(vertices, triangles, (.24, .28, .3))


def record(tag, subrecords):
    payload = b"".join(struct.pack("<4sI", k, len(v)) + v for k, v in subrecords)
    return struct.pack("<4sIII", tag, len(payload), 0, 0) + payload


def build(output: Path):
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Choose a fresh output directory; earlier fields are preserved")
    output.mkdir(parents=True)
    models = output / "meshes/halveth/visual_field"
    models.mkdir(parents=True)
    (models / "ground.dae").write_text(ground_mesh(), encoding="utf-8")
    for seed in range(16):
        for stage in range(5):
            (models / f"branch-{seed}-{stage}.dae").write_text(branch_mesh(seed,stage),encoding="utf-8")
    header = record(b"TES3", [(b"HEDR", struct.pack("<fI32s256sI", 1.3, 0,
        b"HALVETH", b"Isolated native graphics field. Original geometry. No save edits.", 1))])
    cell = record(b"CELL", [(b"NAME", CELL.encode()+b"\0"),
        (b"DATA", struct.pack("<III",1,0,0)),
        (b"AMBI", struct.pack("<IIIf",0x0098a0a8,0x00a8b4c0,0x00403a34,.001))])
    (output / "HALVETH-Visual-Field.esp").write_bytes(header+cell)
    scripts = output / "scripts/halveth_visual_field"
    scripts.mkdir(parents=True)
    for name in ("global.lua", "player.lua", "actor.lua"):
        shutil.copyfile(ROOT / "tools/visual_field" / name, scripts / name)
    (output / "halveth-visual-field.omwscripts").write_text(
        "GLOBAL: scripts/halveth_visual_field/global.lua\nPLAYER: scripts/halveth_visual_field/player.lua\nCUSTOM: scripts/halveth_visual_field/actor.lua\n",encoding="utf-8")
    files = [{"file":p.relative_to(output).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(output.rglob("*")) if p.is_file()]
    receipt={"schema":1,"cell":CELL,"capacity":16,"files":files,
        "nativeRuntime":"NOT_RUN", "scope":"Separate fresh profile; references existing game assets at runtime",
        "layout":"Shared continuous floor; no per-object platforms", "defaultGap":2200,
        "actorMotion":"Generated study actors only; cross-field paths",
        "timeViews":["linear","log"],"rootOperator":"(x,y,z) -> (x,y,-z)",
        "sources":["https://algorithmicbotany.org/papers/abop/abop-ch2.pdf",
                   "https://openmw.readthedocs.io/en/openmw-0.51.0/reference/lua-scripting/openmw_world.html"]}
    (output / "field-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    result=build(parser.parse_args().output)
    print(json.dumps({"cell":result["cell"],"files":len(result["files"]),"capacity":16}))
