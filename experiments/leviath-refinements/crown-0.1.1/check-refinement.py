#!/usr/bin/env python3
"""MIT. Decode actual new assets, compare unchanged wood and rebuild separately."""
from pathlib import Path
import argparse, hashlib, json, math, struct, subprocess, sys
import xml.etree.ElementTree as ET
from PIL import Image

BASE = Path(__file__).resolve().parent
NS = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def records(data):
    cursor = 0; result = []
    while cursor < len(data):
        kind, size, unused, flags = struct.unpack_from('<4sIII', data, cursor); cursor += 16
        assert unused == flags == 0 and cursor + size <= len(data)
        result.append((kind, data[cursor:cursor + size])); cursor += size
    assert cursor == len(data); return result

def subs(data):
    cursor = 0; result = []
    while cursor < len(data):
        kind, size = struct.unpack_from('<4sI', data, cursor); cursor += 8
        assert cursor + size <= len(data); result.append((kind, data[cursor:cursor + size])); cursor += size
    assert cursor == len(data); return result

def decode(geometry):
    mesh = geometry.find('c:mesh', NS); arrays = {}
    for source in mesh.findall('c:source', NS):
        array = source.find('c:float_array', NS); accessor = source.find('c:technique_common/c:accessor', NS)
        values = [float(v) for v in array.text.split()]; stride = int(accessor.get('stride'))
        assert len(values) == int(array.get('count')) == int(accessor.get('count')) * stride
        assert all(math.isfinite(v) for v in values)
        arrays[source.get('id')] = [tuple(values[i:i + stride]) for i in range(0, len(values), stride)]
    prefix = geometry.get('id'); positions = arrays[prefix + 'p']; normals = arrays[prefix + 'n']; uvs = arrays[prefix + 'uv']
    assert len(positions) == len(normals) == len(uvs)
    assert all(abs(sum(v * v for v in n) - 1) < 2e-6 for n in normals)
    triangle_node = mesh.find('c:triangles', NS); count = int(triangle_node.get('count'))
    indices = [int(v) for v in triangle_node.findtext('c:p', namespaces=NS).split()]
    assert len(indices) == count * 9 and all(0 <= v < len(positions) for v in indices)
    triangles = []
    for i in range(0, len(indices), 9):
        points = [positions[indices[i + j]] for j in (0, 3, 6)]
        a = [points[1][k] - points[0][k] for k in range(3)]; b = [points[2][k] - points[0][k] for k in range(3)]
        cross = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
        assert sum(v * v for v in cross) > 1e-8
        triangles.append(points)
    return count, positions, normals, uvs, triangles

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--parent-crown', type=Path, required=True)
    parser.add_argument('--bark-closure', type=Path, required=True); parser.add_argument('--scene-plan', type=Path, required=True)
    parser.add_argument('--esmtool', type=Path, required=True); args = parser.parse_args()
    build = json.loads((BASE / 'BUILD_RECEIPT.json').read_text()); checks = []
    doc = ET.parse(BASE / 'mod/Meshes/veyra/veyra_swamp_crown_refined_011.dae')
    parent_doc = ET.parse(args.parent_crown / 'mod/Meshes/veyra/veyra_swamp_crown_01.dae')
    assert doc.findtext('c:asset/c:up_axis', namespaces=NS) == 'Z_UP'
    geometries = doc.findall('c:library_geometries/c:geometry', NS); assert len(geometries) == 2
    assert ET.tostring(geometries[0]) == ET.tostring(parent_doc.find("c:library_geometries/c:geometry[@id='g0']", NS))
    checks.append('EXACT_SERIALIZED_WOOD_STEM_ROOT_GEOMETRY_PARENT_MATCH')
    assert ET.tostring(doc.find("c:library_effects/c:effect[@id='m0-effect']", NS)) == ET.tostring(parent_doc.find("c:library_effects/c:effect[@id='m0-effect']", NS))
    checks.append('EXACT_BARK_MATERIAL_PARENT_MATCH')
    decoded = [decode(g) for g in geometries]
    assert [p[0] for p in decoded] == [4812, 23904] and sum(p[0] for p in decoded) == 28716
    checks.append('SERIALIZED_FINITE_NONDEGENERATE_NORMALIZED_28716_TRIANGLES_DELTA_ZERO')
    leaf_count, positions, normals, uvs, triangles = decoded[1]
    assert leaf_count == 5976 * 4
    for i in range(0, leaf_count, 2):
        assert triangles[i] == list(reversed(triangles[i + 1]))
    assert all(0 <= u <= 1 and 0 <= v <= 1 for u, v in uvs)
    checks.append('ALL5976_SLIM_FOLDED_LEAVES_EXACT_REVERSED_BACKFACES_UV_BOUND')
    lengths = [math.dist(triangles[i][0], triangles[i][2]) for i in range(0, leaf_count, 4)]
    assert min(lengths) > 43 and max(lengths) < 79
    checks.append('ACTUAL_SERIALIZED_LEAF_LENGTH43_TO79_VERSUS_OLD78_TO115')
    all_positions = decoded[0][1] + decoded[1][1]
    bounds = [[min(p[i] for p in all_positions) for i in range(3)], [max(p[i] for p in all_positions) for i in range(3)]]
    assert all(abs(a - b) < .001 for axis, expected in zip(bounds, build['checks']['bounds']) for a, b in zip(axis, expected))
    assert -72 < bounds[0][2] < 0 and 1900 < bounds[1][2] < 2350
    checks.append('ROOT_ORIGIN_ZERO_BURIED_ROOT_EXTENT_AND_CROWN_BOUNDS')
    textures = {n.findtext('c:init_from', namespaces=NS) for n in doc.findall('c:library_images/c:image', NS)}
    assert textures == {'textures/veyra/swamp_bark.dds', 'textures/veyra/crown_leaf_refined_011.dds'}
    texture = BASE / 'mod/Textures/veyra/crown_leaf_refined_011.dds'
    data = texture.read_bytes(); assert data[:4] == b'DDS ' and data[84:88] == b'DXT1'
    assert struct.unpack_from('<III', data, 12)[:2] == (256, 256) and struct.unpack_from('<I', data, 28)[0] == 9
    image = Image.open(texture); image.load(); assert image.size == (256, 256)
    checks.append('OWN_TEXTURE_DXT1_256SQUARE_ALL9MIPS_DECODE_AND_EXACT_PATHS')
    esp = BASE / 'mod/Veyra-Crown-Refinement-011.esp'; rr = records(esp.read_bytes()); assert [r[0] for r in rr] == [b'TES3', b'STAT']
    header = subs(rr[0][1]); assert [s[0] for s in header] == [b'HEDR', b'MAST', b'DATA']
    assert header[1][1] == b'Veyra-Dense-Crown.esp\0' and struct.unpack('<Q', header[2][1])[0] == (args.parent_crown / 'mod/Veyra-Dense-Crown.esp').stat().st_size
    stat = dict(subs(rr[1][1])); assert stat == {b'NAME': b'veyra_swamp_crown_01\0', b'MODL': b'veyra/veyra_swamp_crown_refined_011.dae\0'}
    checks.append('ONE_OWN_STAT_MODEL_OVERRIDE_ONLY_PARENT_MASTER_NO_CELL_OR_REF_RECORD')
    result = subprocess.run([str(args.esmtool), '-q', '-C', 'dump', str(esp)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    checks.append('ESMTOOL_NATIVE_FORMAT_PARSE_EXIT0_NOT_ENGINE')
    binding = json.loads((BASE / 'bark-closure/SOURCE_BINDING.json').read_text())
    assert sha(BASE / 'bark-closure/CC0-1.0.txt') == binding['licenseTextSha256']
    assert binding['derivativeHashes'] == build['barkTextureDependencies']
    checks.append('COMPLETE_RETAINED_CC0_TEXT_AND_BOUND_BARK_DERIVATIVES_NO_NEW_DOWNLOAD')
    output_files = [p for p in BASE.rglob('*') if p.is_file() and p.name not in ('CHECK_RECEIPT.json', 'FREEZE_RECEIPT.json')]
    before = {p.relative_to(BASE).as_posix(): sha(p) for p in output_files}
    subprocess.run([sys.executable, str(BASE / 'build-refinement.py'), '--parent-crown', str(args.parent_crown), '--bark-closure', str(args.bark_closure)], check=True, capture_output=True)
    assert before == {p.relative_to(BASE).as_posix(): sha(p) for p in output_files}
    checks.append('SECOND_BUILD_ALL_ALREADY_GENERATED_FILES_EXACT_DIGEST_REPRODUCTION')
    # New private probe fixture: only two exact config substitutions, all other bytes copied.
    source = args.scene_plan / 'mod'; dest = BASE / 'native-fixture'; dest.mkdir(exist_ok=True)
    fixture_diffs = {}
    for file in sorted(source.rglob('*')):
        if not file.is_file(): continue
        relative = file.relative_to(source); raw = file.read_bytes(); new = raw
        if relative.as_posix() == 'scripts/veyra_scene/config.lua':
            old_path = b'["crownModel"]="meshes/veyra/veyra_swamp_crown_01.dae"'
            new_path = b'["crownModel"]="meshes/veyra/veyra_swamp_crown_refined_011.dae"'
            old_list = b'["requiredOwnContent"]={'
            assert raw.count(old_path) == raw.count(old_list) == 1
            new = raw.replace(old_path, new_path).replace(old_list, b'["requiredOwnContent"]={"Veyra-Crown-Refinement-011.esp",')
            assert new.replace(new_path, old_path).replace(b'["requiredOwnContent"]={"Veyra-Crown-Refinement-011.esp",', old_list) == raw
        target = dest / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(new)
        fixture_diffs[relative.as_posix()] = {'parentSha256': sha(file), 'candidateSha256': sha(target), 'changed': raw != new}
    assert sum(p['changed'] for p in fixture_diffs.values()) == 1
    checks.append('PRIVATE_SAME_SCENE_ORACLE_ONLY_MODEL_PATH_AND_REQUIRED_OWN_ESP_CONFIG_DELTA')
    freeze = json.loads((args.parent_crown / 'FREEZE_RECEIPT.json').read_text())
    assert all(sha(args.parent_crown / name) == wanted['sha256'] for name, wanted in freeze['files'].items())
    checks.append('ALL15_PARENT_FROZEN_FILES_REMAIN_EXACT')
    receipt = {'schema': 'veyra.crown-refinement-check.v1', 'status': 'STATIC_ASSET_CODEC_AND_REBUILD_PASS_NATIVE_PENDING',
               'checks': checks, 'checkCount': len(checks), 'checkerSha256': sha(Path(__file__)),
               'buildReceiptSha256': sha(BASE / 'BUILD_RECEIPT.json'), 'leafLengthUnits': {'min': min(lengths), 'max': max(lengths)},
               'bounds': bounds, 'pluginParseExit': result.returncode, 'esmtoolSha256': sha(args.esmtool),
               'fixtureDiffs': fixture_diffs, 'nativeEngineStarted': False,
               'claimCeiling': 'Own encoded assets, equal wood geometry and model-only override; material appearance and full crown physics pending coordinated native comparison.'}
    (BASE / 'CHECK_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'checks': len(checks), 'checkReceiptSha256': sha(BASE / 'CHECK_RECEIPT.json'), 'leafLengths': receipt['leafLengthUnits'], 'fixtureFiles': len(fixture_diffs)}, indent=2))

if __name__ == '__main__': main()
