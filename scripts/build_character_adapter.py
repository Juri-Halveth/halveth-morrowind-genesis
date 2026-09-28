"""Build a private appearance adapter from acquired body and clothing packs.

Existing BODY records change only MODL. Existing CLOT records change only
INDX/BNAM/CNAM (worn body-part bindings). Item names, scripts, enchantments,
weight/value, world models and icons are copied byte-for-byte from the supplied
masters. New clothing BODY definitions come from the acquired clothing pack.
No upstream plugin is activated and no mesh or texture is copied by this tool.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_head_adapter import recbytes
from scripts.build_selective_head_adapter import index_meshes, model_path
from scripts.graphics_profile import validate_visual_plugin

PART_FIELDS = {b'INDX', b'BNAM', b'CNAM'}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_records(path: Path, allowed=None) -> dict:
    """Parse bounded records; return BODY/CLOT without executing game scripts."""
    result = {}
    with path.open('rb') as stream:
        length = path.stat().st_size
        first = True
        while header := stream.read(16):
            if len(header) != 16:
                raise ValueError('Truncated record header.')
            tag, size, unknown, flags = struct.unpack('<4sIII', header)
            if (first and tag != b'TES3') or (not first and tag == b'TES3'):
                raise ValueError('Invalid master/plugin header order.')
            first = False
            if allowed is not None and tag not in allowed:
                raise ValueError(f'Unexpected donor record: {tag!r}')
            if size > 64 * 1024 * 1024 or stream.tell() + size > length:
                raise ValueError('Record exceeds bounded input.')
            if tag not in (b'BODY', b'CLOT'):
                stream.seek(size, 1)
                continue
            raw, offset, parts = stream.read(size), 0, []
            while offset < size:
                if size - offset < 8:
                    raise ValueError('Truncated subrecord header.')
                key, count = struct.unpack_from('<4sI', raw, offset)
                offset += 8
                if offset + count > size:
                    raise ValueError('Subrecord exceeds record.')
                parts.append((key, raw[offset:offset + count]))
                offset += count
            names = [v for k, v in parts if k == b'NAME']
            if len(names) != 1 or not names[0].endswith(b'\0') or b'\0' in names[0][:-1] or len(names[0]) < 2:
                raise ValueError('Missing/ambiguous record identity.')
            key = (tag, names[0][:-1].lower())
            if key in result or b'DELE' in dict(parts) or flags & 0x20:
                raise ValueError('Duplicated/deleted body or clothing record.')
            result[key] = (unknown, flags, parts)
    if first:
        raise ValueError('Empty plugin.')
    return result


def build_adapter(masters: list[Path], body_pack: Path, clothes_pack: Path,
                  data_directories: list[Path], output_dir: Path) -> dict:
    masters = [Path(p).resolve(strict=True) for p in masters]
    donors = [Path(body_pack).resolve(strict=True), Path(clothes_pack).resolve(strict=True)]
    directories = [Path(p).resolve(strict=True) for p in data_directories]
    output_dir = Path(output_dir).resolve()
    if not masters or len(set(masters + donors)) != len(masters + donors):
        raise ValueError('Supply distinct masters and donor plugins.')
    if output_dir.exists() or any(output_dir.is_relative_to(p) for p in directories):
        raise ValueError('Output must be a new directory outside the acquired packs.')
    sources = {p: digest(p) for p in masters + donors}
    base = {}
    for path in masters:
        base.update(read_records(path))
    bodies = read_records(donors[0], {b'TES3', b'BODY'})
    clothes = read_records(donors[1], {b'TES3', b'BODY', b'CLOT'})
    if set(bodies) & set(clothes):
        raise ValueError('Body and clothing donor identities overlap.')
    donor = {**bodies, **clothes}
    meshes, _ = index_meshes(directories)
    output, changes, used, excluded = {}, [], {}, []
    required_bodies = {(b'BODY', value.rstrip(b'\0').lower())
                       for key, (_, _, parts) in clothes.items() if key[0] == b'CLOT' and key in base
                       for field, value in parts if field in (b'BNAM', b'CNAM')}
    for key, (unknown, flags, parts) in donor.items():
        kind, rid = key
        current = base.get(key)
        if kind == b'BODY':
            if not current and key not in required_bodies:
                excluded.append({'kind': 'BODY', 'id': rid.decode('cp1252'),
                                 'reason': 'Unreferenced by the selected existing clothing items.'})
                continue
            values = dict(parts)
            if set(values) != {b'NAME', b'MODL', b'FNAM', b'BYDT'} or len(parts) != 4 or len(values[b'BYDT']) != 4:
                raise ValueError('Unexpected BODY definition.')
            if values[b'BYDT'][0] in (0, 1) or values[b'BYDT'][0] > 14:
                raise ValueError('This adapter excludes head/hair and unknown body-part types.')
            if current:
                bu, bf, original = current
                if (bu, bf) != (unknown, flags) or [(k, v) for k, v in original if k != b'MODL'] != [(k, v) for k, v in parts if k != b'MODL']:
                    raise ValueError('Donor changes non-model fields of an existing BODY.')
                parts = [(k, values[b'MODL'] if k == b'MODL' else v) for k, v in original]
                changed = ['BODY.MODL']
            else:
                if key in bodies or values[b'BYDT'][3] != 1:
                    raise ValueError('Only clothing BODY additions are allowed.')
                changed = ['new clothing BODY']
            model = model_path(values[b'MODL'])
            if model.casefold() not in meshes:
                raise FileNotFoundError(f'Donor model is unavailable: {model}')
            asset = meshes[model.casefold()]
            used[asset['path']] = {**asset, 'sha256': digest(Path(asset['path']))}
        else:
            if not current:
                excluded.append({'kind': 'CLOT', 'id': rid.decode('cp1252'),
                                 'reason': 'New items are outside the existing-item appearance scope.'})
                continue
            unknown, flags, original = current
            bindings = [(k, v) for k, v in parts if k in PART_FIELDS]
            if not bindings:
                raise ValueError('Clothing donor has no worn body-part bindings.')
            for field, value in bindings:
                if field in (b'BNAM', b'CNAM'):
                    ref = (b'BODY', value.rstrip(b'\0').lower())
                    if ref not in donor and ref not in base:
                        raise ValueError('Clothing refers to an unavailable BODY.')
            # Keep the source order, replacing the old binding block in place.
            parts, inserted = [], False
            for field, value in original:
                if field in PART_FIELDS:
                    if not inserted:
                        parts.extend(bindings)
                        inserted = True
                else:
                    parts.append((field, value))
            if not inserted:
                parts.extend(bindings)
            assert [(k, v) for k, v in parts if k not in PART_FIELDS] == [(k, v) for k, v in original if k not in PART_FIELDS]
            changed = ['CLOT.INDX', 'CLOT.BNAM', 'CLOT.CNAM']
        output[key] = recbytes(kind, parts, unknown, flags)
        changes.append({'kind': kind.decode(), 'id': rid.decode('cp1252'),
                        'existing': current is not None, 'allowedChanges': changed})
    if not output or not any(k[0] == b'CLOT' for k in output):
        raise ValueError('Empty body/clothing selection.')
    header = [(b'HEDR', struct.pack('<fI32s256sI', 1.3, 0, b'HALVETH character adapter',
               b'Private appearance adapter. Original item properties preserved. Third-party credits remain with acquired packs.', len(output)))]
    for path in masters:
        header.extend([(b'MAST', path.name.encode('cp1252') + b'\0'),
                       (b'DATA', struct.pack('<Q', path.stat().st_size))])
    blob = recbytes(b'TES3', header) + b''.join(output.values())
    for path, expected in sources.items():
        if digest(path) != expected:
            raise ValueError('A source plugin changed during the build.')
    for asset in used.values():
        if digest(Path(asset['path'])) != asset['sha256']:
            raise ValueError('A selected mesh changed during the build.')
    name = 'HALVETH-Character-Appearance.esp'
    with tempfile.TemporaryDirectory(prefix='halveth-character-') as temporary:
        staged = Path(temporary) / name
        staged.write_bytes(blob)
        validation = validate_visual_plugin(staged, digest(staged))
    output_dir.mkdir(parents=True, exist_ok=False)
    plugin = output_dir / name
    plugin.write_bytes(blob)
    receipt = {'schema': 'halveth.character-appearance.v1', 'recordedAt': datetime.now(timezone.utc).isoformat(),
               'file': plugin.name, 'sha256': digest(plugin), 'recordCounts': validation['recordCounts'],
               'sourcePlugins': [{'path': str(p), 'sha256': h} for p, h in sources.items()],
               'changes': changes, 'excludedRecords': excluded, 'selectedNifs': list(used.values()), 'installed': False,
               'preservation': 'Existing BODY: all bytes except MODL. Existing CLOT: all bytes except INDX/BNAM/CNAM. New clothing BODY definitions only. No NPC, script, quest, cell or dialogue records.',
               'privateLocalDerivative': True,
               'scope': 'Record bytes, source hashes, referenced BODY IDs and loose mesh presence. Rendering, skin weights and texture dependencies require a native scene.'}
    (output_dir / 'adapter-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    (output_dir / 'CREDITS.txt').write_text('Private local adapter for Better Bodies (PsychoDog Studios) and Better Clothes Complete (original Better Clothes team; Nkfree93 compilation and credited contributors). Keep all original pack readmes and licenses. Derived game records and third-party assets are excluded from the public source release.\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, action='append', required=True)
    parser.add_argument('--body-pack', type=Path, required=True)
    parser.add_argument('--clothes-pack', type=Path, required=True)
    parser.add_argument('--data-directory', type=Path, action='append', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = build_adapter(args.master, args.body_pack, args.clothes_pack, args.data_directory, args.output_dir)
    print(json.dumps({k: result[k] for k in ('file', 'sha256', 'recordCounts', 'installed', 'preservation')}, indent=2))


if __name__ == '__main__':
    main()
