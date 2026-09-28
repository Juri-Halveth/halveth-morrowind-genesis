"""Build a private BODY.MODL-only adapter for a separately acquired head pack.

Existing Better Heads/Khajiit mappings are retained unless the new pack contains
the exact original NIF path. This tool writes a new directory, never installs,
copies third-party assets, or changes master files or the original adapter.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_head_adapter import records, recbytes
from scripts.graphics_profile import validate_visual_plugin


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_path(value: bytes) -> str:
    if not value.endswith(b'\0') or b'\0' in value[:-1]:
        raise ValueError('BODY.MODL must be one terminated model path.')
    text = value[:-1].decode('cp1252').replace('\\', '/')
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ':' in text or '..' in path.parts:
        raise ValueError('BODY.MODL must be a relative mesh path.')
    return str(path)


def declared_masters(header: bytes) -> list[tuple[str, int]]:
    """Bind the preserved TES3 master links to the supplied source order."""
    cursor, pending, result = 16, None, []
    while cursor < len(header):
        key, size = struct.unpack_from('<4sI', header, cursor)
        value = header[cursor + 8:cursor + 8 + size]
        cursor += 8 + size
        if key == b'MAST':
            if pending is not None or not value.endswith(b'\0') or b'\0' in value[:-1]:
                raise ValueError('Invalid TES3 master declaration.')
            pending = value[:-1].decode('cp1252')
        elif key == b'DATA':
            if pending is None or size != 8:
                raise ValueError('Invalid TES3 master size binding.')
            result.append((pending.casefold(), struct.unpack('<Q', value)[0]))
            pending = None
    if pending is not None:
        raise ValueError('Unbound TES3 master declaration.')
    return result


def index_meshes(directories: list[Path]) -> tuple[dict, list]:
    """Use OpenMW case-insensitive VFS names; later registered packs take priority."""
    selected, assets = {}, []
    for directory in directories:
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f'Replacement data directory is unavailable or linked: {directory}')
        mesh_dirs = [path for path in directory.iterdir()
                     if path.is_dir() and path.name.casefold() == 'meshes']
        if len(mesh_dirs) > 1:
            raise ValueError('Ambiguous case-folded Meshes directories.')
        local = {}
        for mesh_dir in mesh_dirs:
            for path in sorted(mesh_dir.rglob('*'), key=lambda item: str(item).casefold()):
                if not path.is_file() or path.suffix.casefold() != '.nif':
                    continue
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError('Replacement mesh escapes its data directory.')
                name = path.relative_to(mesh_dir).as_posix()
                key = name.casefold()
                if key in local:
                    raise ValueError(f'Ambiguous case-folded NIF path: {name}')
                record = {'dataDirectory': str(directory), 'relativePath': 'Meshes/' + name,
                          'modelPath': name, 'path': str(path), 'bytes': path.stat().st_size}
                local[key] = record
                assets.append(record)
        selected.update(local)
    if not selected:
        raise ValueError('Replacement data directories contain no loose NIF files under Meshes.')
    return selected, assets


def build_adapter(masters: list[Path], existing_adapter: Path,
                  replacement_data: list[Path], output_dir: Path) -> dict:
    masters = [Path(path).resolve(strict=True) for path in masters]
    existing_adapter = Path(existing_adapter).resolve(strict=True)
    replacement_data = [Path(path).resolve(strict=True) for path in replacement_data]
    output_dir = Path(output_dir).resolve()
    if not masters or len(set(masters)) != len(masters):
        raise ValueError('Supply distinct master files in game load order.')
    if len(set(replacement_data)) != len(replacement_data):
        raise ValueError('Supply distinct replacement data directories.')
    if output_dir.exists():
        raise FileExistsError('Choose a new output directory; existing output is preserved.')
    if any(output_dir.is_relative_to(directory) for directory in replacement_data):
        raise ValueError('Output must be separate from replacement assets.')
    sources = [*masters, existing_adapter]
    before = {path: digest(path) for path in sources}
    inspected = validate_visual_plugin(existing_adapter, before[existing_adapter])
    if set(inspected['recordCounts']) - {'TES3', 'BODY'}:
        raise ValueError('Existing adapter must contain TES3 and BODY records only.')
    existing_raw = existing_adapter.read_bytes()
    if hashlib.sha256(existing_raw).hexdigest() != before[existing_adapter]:
        raise ValueError('Adapter changed during source acquisition.')
    _, header_size, _, _ = struct.unpack_from('<4sIII', existing_raw)
    header = existing_raw[:16 + header_size]
    expected_masters = [(path.name.casefold(), path.stat().st_size) for path in masters]
    if declared_masters(header) != expected_masters:
        raise ValueError('Supplied master names, sizes or order differ from the existing adapter header.')
    base = {}
    for master in masters:
        seen = set()
        for rid, unknown, flags, parts in records(master):
            if not rid or rid in seen:
                raise ValueError('Missing or duplicate BODY ID in a master.')
            seen.add(rid)
            base[rid] = (unknown, flags, parts)
    meshes, assets = index_meshes(replacement_data)
    output_records, changes, preserved, used, seen = [], [], [], {}, set()
    for rid, unknown, flags, parts in records(existing_adapter):
        if not rid or rid in seen or rid not in base:
            raise ValueError('Adapter BODY ID is duplicated or absent from the supplied masters.')
        seen.add(rid)
        base_unknown, base_flags, original = base[rid]
        original_values = dict(original)
        current_values = dict(parts)
        if sum(key == b'MODL' for key, _ in original) != 1 or sum(key == b'MODL' for key, _ in parts) != 1:
            raise ValueError('Each head/hair BODY must have exactly one MODL.')
        if b'DELE' in original_values or not original_values.get(b'BYDT') or original_values[b'BYDT'][0] not in (0, 1):
            raise ValueError('Adapter contains a deleted or non-head/hair BODY.')
        if (unknown, flags) != (base_unknown, base_flags) or \
                [(key, value) for key, value in parts if key != b'MODL'] != \
                [(key, value) for key, value in original if key != b'MODL']:
            raise ValueError('Existing adapter changes fields beyond BODY.MODL.')
        original_model = model_path(original_values[b'MODL'])
        current_model = model_path(current_values[b'MODL'])
        replacement = meshes.get(original_model.casefold())
        if replacement:
            mesh_path = Path(replacement['path'])
            used[str(mesh_path)] = {**replacement, 'sha256': digest(mesh_path)}
            next_parts = [(key, original_values[b'MODL'] if key == b'MODL' else value)
                          for key, value in parts]
        else:
            next_parts = parts
        changed = next_parts != parts
        entry = {'id': rid.decode('cp1252'), 'previousModel': current_model,
                 'originalModel': original_model,
                 'resultModel': original_model if replacement else current_model}
        if changed:
            changes.append({**entry, 'replacementNif': replacement['relativePath'],
                            'changedFields': ['BODY.MODL']})
        else:
            preserved.append({**entry, 'reason': 'already uses original model' if replacement
                              else 'original NIF absent from replacement pack'})
        output_records.append(recbytes(b'BODY', next_parts, unknown, flags))
    # Heads not overridden by the old adapter already use their base path.
    direct_base_paths = []
    for rid, (_, _, parts) in base.items():
        values = dict(parts)
        if rid in seen or b'DELE' in values or not values.get(b'BYDT') or values[b'BYDT'][0] not in (0, 1):
            continue
        if b'MODL' in values:
            name = model_path(values[b'MODL'])
            if name.casefold() in meshes:
                direct_base_paths.append({'id': rid.decode('cp1252'), 'originalModel': name})
    blob = header + b''.join(output_records)
    for path, expected in before.items():
        if digest(path) != expected:
            raise ValueError('A source plugin changed during the build.')
    for asset in used.values():
        if digest(Path(asset['path'])) != asset['sha256']:
            raise ValueError('A selected replacement mesh changed during the build.')
    output_dir.mkdir(parents=True, exist_ok=False)
    plugin = output_dir / existing_adapter.name
    with plugin.open('xb') as target:
        target.write(blob)
    result = validate_visual_plugin(plugin, hashlib.sha256(blob).hexdigest())
    unused = [asset for asset in assets if asset['path'] not in used]
    receipt = {
        'schema': 'halveth.selective-head-adapter.v1',
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'file': plugin.name, 'sha256': result['sha256'], 'bytes': len(blob),
        'bodyRecords': len(output_records), 'changedRecords': len(changes),
        'preservedRecords': len(preserved), 'changedFields': ['BODY.MODL'],
        'npcRecords': 0, 'deletedRecords': 0, 'installed': False,
        'sourcePlugins': [{'path': str(path), 'sha256': before[path]} for path in sources],
        'replacementDataDirectories': [str(path) for path in replacement_data],
        'availableNifCount': len(assets), 'selectedNifCount': len(used),
        'unselectedNifCount': len(unused), 'selectedNifs': list(used.values()),
        'unselectedNifs': unused, 'changes': changes, 'preserved': preserved,
        'basePathsPresentWithoutAdapterOverride': direct_base_paths,
        'activation': 'Replace the old adapter data directory in a separately reviewed graphics manifest; load replacement assets after earlier packs. No activation performed.',
        'scope': 'Loose NIF path availability and unchanged non-MODL BODY bytes checked. Texture dependencies, NIF rendering and appearance require a native scene.',
        'privateLocalDerivative': True,
    }
    (output_dir / 'adapter-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    (output_dir / 'CREDITS.txt').write_text(
        'Selective HALVETH BODY.MODL adapter. Source masters and the earlier adapter remain unchanged.\n'
        'Westly and the original mesh/texture contributors remain credited by the separately acquired head pack readmes.\n'
        'Retained Better Heads and Khajiit mappings keep their existing source-pack credits.\n'
        'No meshes or textures were copied or modified. Keep every original pack readme/license.\n'
        'This local derived plugin contains source game records and is not part of the public source package.\n',
        encoding='utf-8')
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, action='append', required=True,
                        help='Base master, repeated in game load order.')
    parser.add_argument('--existing-adapter', type=Path, required=True)
    parser.add_argument('--replacement-data', type=Path, action='append', required=True,
                        help='Acquired pack data root containing Meshes, repeated in VFS order.')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New private output directory; must not already exist.')
    args = parser.parse_args()
    result = build_adapter(args.master, args.existing_adapter, args.replacement_data, args.output_dir)
    print(json.dumps({key: result[key] for key in (
        'file', 'sha256', 'bodyRecords', 'changedRecords', 'preservedRecords',
        'availableNifCount', 'selectedNifCount', 'unselectedNifCount', 'installed')}, indent=2))


if __name__ == '__main__':
    main()
