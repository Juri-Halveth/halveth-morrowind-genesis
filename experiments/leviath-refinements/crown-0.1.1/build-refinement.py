#!/usr/bin/env python3
"""MIT. Source-bound leaf refinement; old crown, stem and placement stay unchanged."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, random, struct, sys
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
MOD = BASE / 'mod'
NS = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
PARENT_BUILDER = '60ab6ade224610cdead3761cef4f8426e95cc3fed112a42a042e3e14bfe86c3b'
PARENT_MESH = '8fb613ab60740892f33c4094f817a45098e1fc9d12c9c873b5ba9b596a51c683'
PARENT_PLUGIN = 'e6aebdbcd627357cbc5fec6a2e4bc0b7d2ca90da7fd5cde9af257dd0dd1f7665'
MODEL = 'Meshes/veyra/veyra_swamp_crown_refined_011.dae'
TEXTURE = 'Textures/veyra/crown_leaf_refined_011.dds'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def load_parent(path):
    assert sha(path / 'build-crown.py') == PARENT_BUILDER
    assert sha(path / 'mod/Meshes/veyra/veyra_swamp_crown_01.dae') == PARENT_MESH
    assert sha(path / 'mod/Veyra-Dense-Crown.esp') == PARENT_PLUGIN
    freeze = json.loads((path / 'FREEZE_RECEIPT.json').read_text())
    assert all(sha(path / name) == value['sha256'] for name, value in freeze['files'].items())
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('frozen_crown_010', path / 'build-crown.py')
    parent = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent)
    return parent, freeze

def slim_pair(part, k, center, direction, length, width, tilt):
    direction = k.unit(direction); u, v = k.basis(direction)
    transverse = k.add(k.mul(u, math.cos(tilt)), k.mul(v, math.sin(tilt)))
    normal = k.unit(k.cross(transverse, direction))
    jitter = math.sin(center[0] * .017 + center[1] * .011 + center[2] * .007)
    for side, scale, breadth in ((-1, .68, .46), (1, .56, .40)):
        axis = k.unit(k.add(direction, k.add(k.mul(transverse, side * (.21 + jitter * .06)), k.mul(normal, .08))))
        cross_axis = k.unit(k.cross(axis, normal))
        base = k.add(center, k.add(k.mul(transverse, side * width * .18), k.mul(direction, length * .08)))
        tip = k.add(base, k.mul(axis, length * scale))
        left = k.add(base, k.add(k.mul(axis, length * scale * .44), k.add(k.mul(cross_axis, width * breadth * .50), k.mul(normal, -width * breadth * .11))))
        right = k.add(base, k.add(k.mul(axis, length * scale * .39), k.add(k.mul(cross_axis, -width * breadth * .43), k.mul(normal, -width * breadth * .08))))
        part.triangle(base, left, tip, (.5, 0), (1, .44), (.5, 1), double=True)
        part.triangle(base, tip, right, (.5, 0), (.5, 1), (0, .39), double=True)

def texture(k):
    image = Image.new('RGB', (256, 256)); px = image.load(); rng = random.Random(2026100351 + 111)
    for y in range(256):
        for x in range(256):
            edge = abs(x - 128) / 128
            vein_phase = (y + abs(x - 128) * .60) % 28
            vein = math.exp(-((min(vein_phase, 28 - vein_phase)) / 1.3) ** 2) * 7
            midrib = math.exp(-((x - 128) / 2.7) ** 2) * 11
            organic = math.sin(x * .071 + y * .019) * 3 + math.sin(y * .047) * 4
            noise = rng.uniform(-1.7, 1.7)
            px[x, y] = tuple(int(max(0, min(255, b + vein * f + midrib * f + organic + noise - edge ** 1.8 * 11)))
                             for b, f in ((102, .65), (140, 1), (65, .43)))
    target = MOD / TEXTURE; target.parent.mkdir(parents=True, exist_ok=True); k.dds(image, target)
    image.resize((768, 768), Image.Resampling.NEAREST).save(BASE / 'LEAF_TEXTURE_PREVIEW.png')

def preview(old_parts, new_parts):
    image = Image.new('RGB', (1920, 1120), (228, 232, 223)); draw = ImageDraw.Draw(image)
    draw.text((20, 12), 'OWN SOURCE GEOMETRY COMPARISON / SAME PROJECTION / NOT ENGINE', fill=(30, 44, 33))
    for row, parts in enumerate((old_parts, new_parts)):
        for panel, angle in enumerate((0, math.pi / 2, math.pi * .75)):
            triangles = []
            for part in parts:
                for offset in range(0, len(part.indices), 3):
                    vertices = [part.positions[j] for j in part.indices[offset:offset + 3]]
                    projected = [(p[0] * math.cos(angle) + p[1] * math.sin(angle), p[2], -p[0] * math.sin(angle) + p[1] * math.cos(angle)) for p in vertices]
                    triangles.append((sum(p[2] for p in projected) / 3, projected, part.material))
            for depth, points, material in sorted(triangles, key=lambda t: t[0]):
                screen = [(320 + panel * 640 + p[0] * .20, 510 + row * 535 - p[1] * .20) for p in points]
                draw.polygon(screen, fill=(90, 72, 51) if material == 0 else ((65, 102, 43) if row == 0 else (102, 140, 65)))
            draw.text((panel * 640 + 18, 530 + row * 535), ('0.1.0 broad leaves' if row == 0 else '0.1.1 paired slim folded leaves') + ' / view ' + str(panel + 1), fill=(31, 44, 34))
    image.save(BASE / 'CROWN_COMPARISON_PREVIEW.png')

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--parent-crown', type=Path, required=True)
    parser.add_argument('--bark-closure', type=Path, required=True); args = parser.parse_args()
    parent, freeze = load_parent(args.parent_crown); k = parent.kernel()
    binding = json.loads((args.bark_closure / 'SOURCE_BINDING.json').read_text())
    assert sha(args.bark_closure / 'CC0-1.0.txt') == binding['licenseTextSha256']
    for name, digest in binding['derivativeHashes'].items():
        assert sha(args.bark_closure / 'mod/Textures/veyra' / name) == digest
    old_parts, *_ = parent.geometry(k)
    parent.broad_leaf = slim_pair
    parts, branches, clusters, probes, tip, radius = parent.geometry(k)
    assert parts[0].positions == old_parts[0].positions and parts[0].normals == old_parts[0].normals
    assert parts[0].uvs == old_parts[0].uvs and parts[0].indices == old_parts[0].indices
    checks = parent.verify(parts); assert checks['totalTriangles'] == 28716
    texture(k); mesh = MOD / MODEL; mesh.parent.mkdir(parents=True, exist_ok=True); k.collada(mesh, parts)
    doc = ET.parse(mesh); old_doc = ET.parse(args.parent_crown / 'mod/Meshes/veyra/veyra_swamp_crown_01.dae')
    doc.find("c:library_images/c:image[@id='m1-image']/c:init_from", NS).text = 'textures/veyra/crown_leaf_refined_011.dds'
    phong = doc.find("c:library_effects/c:effect[@id='m1-effect']/c:profile_COMMON/c:technique/c:phong", NS)
    for field, value in [('emission', '.075 .10 .035 1'), ('ambient', '.82 .86 .74 1'), ('specular', '.01 .014 .006 1')]:
        phong.find('c:' + field + '/c:color', NS).text = value
    phong.find('c:shininess/c:float', NS).text = '3'
    doc.write(mesh, encoding='utf-8', xml_declaration=True)
    old_wood = ET.tostring(old_doc.find("c:library_geometries/c:geometry[@id='g0']", NS))
    new_wood = ET.tostring(doc.find("c:library_geometries/c:geometry[@id='g0']", NS)); assert old_wood == new_wood
    rid = 'veyra_swamp_crown_01'; parent_esp = args.parent_crown / 'mod/Veyra-Dense-Crown.esp'
    header = k.subrecord(b'HEDR', struct.pack('<fI32s256sI', 1.3, 0, b'LEVIATH Workshop', b'Own leaf-only refinement; single own STAT model override', 1))
    header += k.subrecord(b'MAST', k.string('Veyra-Dense-Crown.esp')) + k.subrecord(b'DATA', struct.pack('<Q', parent_esp.stat().st_size))
    body = k.subrecord(b'NAME', k.string(rid)) + k.subrecord(b'MODL', k.string('veyra/veyra_swamp_crown_refined_011.dae'))
    esp = MOD / 'Veyra-Crown-Refinement-011.esp'; esp.write_bytes(k.record(b'TES3', header) + k.record(b'STAT', body))
    preview(old_parts, parts)
    closure = BASE / 'bark-closure'; closure.mkdir(exist_ok=True)
    for name in ('CC0-1.0.txt', 'SOURCE_BINDING.json', 'THIRD_PARTY_NOTICES.md'):
        (closure / name).write_bytes((args.bark_closure / name).read_bytes())
    receipt = {'schema': 'veyra.crown-refinement-build.v1', 'version': '0.1.1', 'parentVersion': '0.1.0',
               'parentFreezeSha256': sha(args.parent_crown / 'FREEZE_RECEIPT.json'), 'parentBuilderSha256': PARENT_BUILDER,
               'parentModelSha256': PARENT_MESH, 'parentPluginSha256': PARENT_PLUGIN,
               'seed': 2026100351, 'geometryKernelSha256': sha(args.parent_crown / 'geometry-kernel.py'),
               'generatorSha256': sha(Path(__file__)), 'checks': checks, 'oldTriangles': 28716, 'triangleDelta': 0,
               'oldLeaves': probes, 'newLeaves': probes * 2, 'trianglesPerNewLeafIncludingBackfaces': 4,
               'stemGeometryCanonicalXMLSha256': hashlib.sha256(new_wood).hexdigest(), 'stemGeometryExactParentMatch': True,
               'rootOriginLocalZ': 0, 'allExistingRefsAndTransformsChanged': 0, 'ownStatOverrides': 1, 'cellRecords': 0,
               'colliderScope': 'Wood/stem/root serialized geometry exact. Leaf draw mesh differs; full crown collider must be native-tested, no all-collider-byte identity claim.',
               'barkBindingSha256': sha(closure / 'SOURCE_BINDING.json'), 'barkCC0LegalTextSha256': sha(closure / 'CC0-1.0.txt'),
               'barkTextureDependencies': binding['derivativeHashes'], 'barkTexturesCopied': 0,
               'parentFrozenSourcesUnchanged': all(sha(args.parent_crown / name) == value['sha256'] for name, value in freeze['files'].items()),
               'generatedHashes': {p.relative_to(MOD).as_posix(): sha(p) for p in sorted(MOD.rglob('*')) if p.is_file()},
               'previewSha256': sha(BASE / 'CROWN_COMPARISON_PREVIEW.png'), 'leafPreviewSha256': sha(BASE / 'LEAF_TEXTURE_PREVIEW.png'),
               'nativeEngineStarted': False, 'nativeMaterialSilhouetteAndCollision': 'PENDING_ROOT_SAME_SCENE_PROBE'}
    (BASE / 'BUILD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'SOURCE_BUILD_PASS', 'totalTriangles': checks['totalTriangles'], 'individualLeaves': probes * 2, 'woodExact': True, 'generated': receipt['generatedHashes']}, indent=2))

if __name__ == '__main__': main()
