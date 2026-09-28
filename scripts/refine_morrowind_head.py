"""Refine a rigid Morrowind head and every facial morph with identical stencils.

Optional offline authoring tool: PyFFI 2.2.3 is required, not bundled with the
game. This supports only NIF 4.0.0.2, a single unskinned NiTriShape and its
NiGeomMorpherController. A new private output file is required. Boundary
vertices stay pinned so the neck and UV seams keep their original positions.
This is bounded subdivision, not automatic character reconstruction.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import time


def topology(vertex_count, triangles, strength):
    """Return convex Loop stencils, linear UV stencils and split triangles."""
    if not 0 <= strength <= 1 or not math.isfinite(strength):
        raise ValueError("Strength must be finite and within 0..1.")
    edges, neighbors = defaultdict(list), [set() for _ in range(vertex_count)]
    seen = set()
    for a, b, c in triangles:
        if len({a, b, c}) != 3 or not all(0 <= i < vertex_count for i in (a, b, c)):
            raise ValueError("Degenerate triangle or out-of-range vertex.")
        key = tuple(sorted((a, b, c)))
        if key in seen:
            raise ValueError("Duplicate triangle.")
        seen.add(key)
        for i, j, opposite in ((a, b, c), (b, c, a), (c, a, b)):
            edges[tuple(sorted((i, j)))].append(opposite)
            neighbors[i].add(j)
            neighbors[j].add(i)
    if any(len(v) > 2 for v in edges.values()):
        raise ValueError("Non-manifold edge.")
    boundary = {i for edge, opposite in edges.items() if len(opposite) == 1 for i in edge}
    stencils, uv_stencils = [], []
    for i, adjacent in enumerate(neighbors):
        if i in boundary or len(adjacent) < 3:
            stencil = {i: 1.0}
        else:
            n = len(adjacent)
            beta = (3 / 16 if n == 3 else 3 / (8 * n)) * strength
            stencil = {i: 1 - n * beta, **{j: beta for j in sorted(adjacent)}}
        stencils.append(stencil)
        uv_stencils.append({i: 1.0})
    indices = {}
    for (a, b), opposite in sorted(edges.items()):
        indices[a, b] = len(stencils)
        linear = {a: 0.5, b: 0.5}
        curved = dict(linear)
        if len(opposite) == 2:
            curved = {a: 0.5 - strength / 8, b: 0.5 - strength / 8}
            for o in opposite:
                curved[o] = curved.get(o, 0) + strength / 8
        stencils.append(curved)
        uv_stencils.append(linear)
    refined = []
    for a, b, c in triangles:
        ab, bc, ca = (indices[tuple(sorted(edge))] for edge in ((a, b), (b, c), (c, a)))
        refined.extend(((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)))
    if len(stencils) > 65535 or len(refined) > 65535:
        raise ValueError("Subdivision exceeds Morrowind's 16-bit geometry counts.")
    return stencils, uv_stencils, refined, len(boundary)


def interpolate(values, stencils):
    if not values or any(not math.isfinite(v) for row in values for v in row):
        raise ValueError("Vertex attributes must be finite.")
    return [tuple(sum(values[i][axis] * weight for i, weight in stencil.items())
                  for axis in range(len(values[0]))) for stencil in stencils]


def sculpt_point(point, brushes):
    """Apply bounded smooth ellipsoid displacement brushes in model space.

    Weights use the unchanged rest point; brush order has no effect. Outside
    each ellipsoid the displacement and its first derivative are both zero.
    """
    result = list(point)
    for brush in brushes:
        q = sum(((point[i] - brush['center'][i]) / brush['radius'][i]) ** 2 for i in range(3))
        weight = max(0.0, 1.0 - q) ** 2
        for i in range(3):
            result[i] += weight * brush['displacement'][i]
    return tuple(result)


def validate_brushes(plan, source_hash):
    if (not isinstance(plan, dict) or set(plan) != {'schemaVersion', 'sourceSha256', 'brushes'}
            or plan['schemaVersion'] != 1 or plan['sourceSha256'] != source_hash):
        raise ValueError('Sculpt plan must bind this exact source.')
    brushes = plan['brushes']
    if not isinstance(brushes, list) or not 1 <= len(brushes) <= 16:
        raise ValueError('Use one to sixteen bounded sculpt brushes.')
    for brush in brushes:
        if not isinstance(brush, dict) or set(brush) != {'center', 'radius', 'displacement'}:
            raise ValueError('Invalid sculpt brush.')
        for key, vector in brush.items():
            if (not isinstance(vector, list) or len(vector) != 3 or any(
                    type(v) not in (int, float) or not math.isfinite(v) for v in vector)):
                raise ValueError('Brush vectors need three finite numbers.')
        if any(r <= 0 or r > 20 for r in brush['radius']):
            raise ValueError('Brush radii must be within 0..20 model units.')
        if sum(d * d for d in brush['displacement']) > 1:
            raise ValueError('Each brush is limited to one model unit of displacement.')
    return brushes


def sculpt_rest(vertices, normals, brushes):
    """Change the rest shape; transform normals by the inverse-transpose Jacobian."""
    def cross(a, b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    transformed, normal_result = [], []
    for point, normal in zip(vertices, normals):
        transformed.append(sculpt_point(point, brushes))
        columns = []
        for axis in range(3):
            lo, hi = list(point), list(point)
            lo[axis] -= .001
            hi[axis] += .001
            a, b = sculpt_point(lo, brushes), sculpt_point(hi, brushes)
            columns.append(tuple((b[i]-a[i])/.002 for i in range(3)))
        cofactors = [cross(columns[1], columns[2]), cross(columns[2], columns[0]), cross(columns[0], columns[1])]
        determinant = sum(columns[0][i]*cofactors[0][i] for i in range(3))
        if not .25 < determinant < 4:
            raise ValueError('Sculpt folds or excessively stretches the mesh.')
        value = tuple(sum(normal[j]*cofactors[j][i] for j in range(3)) for i in range(3))
        length = math.sqrt(sum(v*v for v in value))
        if length < 1e-8:
            raise ValueError('Sculpt produces an invalid normal.')
        normal_result.append(tuple(v/length for v in value))
    return transformed, normal_result


def _nif_type(dependencies):
    if dependencies:
        sys.path.insert(0, str(dependencies.resolve(strict=True)))
    # Compatibility for the optional legacy authoring dependency on Python 3.8+.
    if not hasattr(time, "clock"):
        time.clock = time.perf_counter
    import pyffi
    from pyffi.formats.nif import NifFormat
    if pyffi.__version__ != "2.2.3":
        raise ValueError("This authoring adapter is bound to PyFFI 2.2.3.")
    if not getattr(NifFormat.NiTriShapeData, "_halveth_uv_compat", False):
        original = NifFormat.NiTriShapeData.read

        def read(self, stream, data):
            if data.version == 0x04000002:
                # The legacy XML declares the same field twice with different
                # widths. Select its version-specific type before reading.
                for field in self._get_filtered_attribute_list(data):
                    if field.name == "num_uv_sets":
                        self._num_uv_sets_value_ = field.type_()
            return original(self, stream, data)

        NifFormat.NiTriShapeData.read = read
        NifFormat.NiTriShapeData._halveth_uv_compat = True
    return NifFormat


def serialized(value, data):
    stream = io.BytesIO()
    value.write(stream, data)
    return stream.getvalue()


def export(source, output, expected_hash, iterations=1, strength=0.65, dependencies=None, sculpt_plan=None):
    if iterations not in (1, 2):
        raise ValueError("Use one or two bounded refinement passes.")
    source, output = source.resolve(strict=True), output.resolve()
    receipt_path = output.with_suffix(".receipt.json")
    if output.exists() or receipt_path.exists() or source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Use a new output path and a source below 16 MiB.")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_hash:
        raise ValueError("Source hash differs from the bound input.")
    N = _nif_type(dependencies)
    data = N.Data()
    data.read(io.BytesIO(raw))
    if data.version != 0x04000002:
        raise ValueError("Only Morrowind NIF 4.0.0.2 is supported.")
    unchanged = io.BytesIO()
    data.write(unchanged)
    if unchanged.getvalue() != raw:
        raise ValueError("The parser did not preserve the original bytes exactly.")
    blocks = [block for block in data.get_global_iterator() if block is not data]
    shapes = [b for b in blocks if isinstance(b, N.NiTriShape)]
    if len(shapes) != 1 or shapes[0].skin_instance is not None:
        raise ValueError("Expected one rigid, unskinned head shape.")
    shape = shapes[0]
    if not isinstance(shape.controller, N.NiGeomMorpherController) or shape.controller.next_controller:
        raise ValueError("Expected a single facial morph controller.")
    geometry, morph = shape.data, shape.controller.data
    if (not geometry.has_normals or geometry.has_vertex_colors or geometry.num_match_groups
            or geometry.num_uv_sets != 1 or not geometry.has_uv):
        raise ValueError("Unsupported head vertex attributes.")
    if morph.num_vertices != geometry.num_vertices or not morph.num_morphs:
        raise ValueError("Morph and geometry vertex counts differ.")
    immutable = [(block, serialized(block, data)) for block in blocks
                 if block is not geometry and block is not morph]
    morph_keys = [(m.num_keys, m.interpolation, b"".join(serialized(k, data) for k in m.keys))
                  for m in morph.morphs]
    vertices = [tuple(getattr(v, axis) for axis in ("x", "y", "z")) for v in geometry.vertices]
    normals = [tuple(getattr(v, axis) for axis in ("x", "y", "z")) for v in geometry.normals]
    uvs = [(v.u, v.v) for v in geometry.uv_sets[0]]
    morphs = [[tuple(getattr(v, axis) for axis in ("x", "y", "z")) for v in m.vectors]
              for m in morph.morphs]
    triangles = list(geometry.get_triangles())
    before = {"vertices": len(vertices), "triangles": len(triangles), "morphs": len(morphs)}
    sculpt_hash = None
    if sculpt_plan:
        plan_raw = Path(sculpt_plan).read_bytes()
        brushes = validate_brushes(json.loads(plan_raw), digest)
        if any(abs(a-b) > 1e-6 for p, q in zip(vertices, morphs[0]) for a, b in zip(p, q)):
            raise ValueError('Sculpt requires an explicitly matching rest/base morph.')
        vertices, normals = sculpt_rest(vertices, normals, brushes)
        # Keep expression deltas and keyframes. Only the base/rest target moves.
        morphs[0] = list(vertices)
        sculpt_hash = hashlib.sha256(plan_raw).hexdigest()
    for _ in range(iterations):
        masks, uv_masks, triangles, boundary = topology(len(vertices), triangles, strength)
        vertices = interpolate(vertices, masks)
        # Deltas and base positions share the same linear transformation. Zero
        # deltas remain zero; key times and weights are not reinterpreted.
        morphs = [interpolate(values, masks) for values in morphs]
        uvs = interpolate(uvs, uv_masks)
        normals = interpolate(normals, uv_masks)
        normals = [tuple(x / max(math.sqrt(sum(y * y for y in v)), 1e-12) for x in v) for v in normals]
    geometry.num_vertices = morph.num_vertices = len(vertices)
    geometry.vertices.update_size()
    geometry.normals.update_size()
    geometry.uv_sets.update_size()
    for array, values, fields in ((geometry.vertices, vertices, ("x", "y", "z")),
                                  (geometry.normals, normals, ("x", "y", "z")),
                                  (geometry.uv_sets[0], uvs, ("u", "v"))):
        for target, value in zip(array, values):
            for field, number in zip(fields, value):
                setattr(target, field, number)
    for target, values in zip(morph.morphs, morphs):
        target.arg = len(vertices)
        target.vectors.update_size()
        for vertex, value in zip(target.vectors, values):
            vertex.x, vertex.y, vertex.z = value
    geometry.set_triangles(triangles)
    geometry.update_center_radius()
    if any(serialized(block, data) != original for block, original in immutable):
        raise ValueError("A block outside the geometry/morph data changed.")
    if morph_keys != [(m.num_keys, m.interpolation, b"".join(serialized(k, data) for k in m.keys))
                      for m in morph.morphs]:
        raise ValueError("Facial animation keyframes changed.")
    encoded = io.BytesIO()
    data.write(encoded)
    result = encoded.getvalue()
    reread = N.Data()
    reread.read(io.BytesIO(result))
    check = io.BytesIO()
    reread.write(check)
    if check.getvalue() != result or source.read_bytes() != raw:
        raise ValueError("Output roundtrip or source preservation failed.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as temporary:
        temporary.write(result)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.rename(output)
    finally:
        temporary_path.unlink(missing_ok=True)
    receipt = {"schemaVersion": 1, "recordedAt": datetime.now(timezone.utc).isoformat(),
               "operator": "bounded-loop-head-1", "inputSha256": digest,
               "outputSha256": hashlib.sha256(result).hexdigest(),
               "iterations": iterations, "strength": strength, "before": before,
               "after": {"vertices": len(vertices), "triangles": len(triangles), "morphs": len(morphs)},
               "lastPassPinnedBoundaryVertices": boundary, "animationKeys": "BYTE_IDENTICAL",
               "otherBlocks": "BYTE_IDENTICAL", "outputRoundtrip": "BYTE_IDENTICAL",
               "state": "BUILT_REQUIRES_NATIVE_REVIEW"}
    if sculpt_hash:
        receipt['sculpt'] = {'operator': 'rest-ellipsoid-displacement-1', 'planSha256': sculpt_hash,
                            'expressionDeltas': 'PRESERVED_BEFORE_SUBDIVISION'}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--strength", type=float, default=0.65)
    parser.add_argument("--dependencies", type=Path)
    parser.add_argument("--sculpt-plan", type=Path, help='Optional source-bound rest-shape brush plan.')
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output, args.sha256, args.iterations,
                            args.strength, args.dependencies, args.sculpt_plan), indent=2))


if __name__ == "__main__":
    main()
