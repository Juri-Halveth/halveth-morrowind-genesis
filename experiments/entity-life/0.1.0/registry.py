"""MIT. Local source-bound identity catalogue; no original game bytes are exported."""
from pathlib import Path
import argparse, collections, datetime, gzip, hashlib, json, struct

VERSION = 'entity-life.registry/0.1.0'
WORLD = 'HALVETH-MORROWIND-REZERO'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def eid(world, kind, anchor):
    # State, position, appearance and invented display name are absent here.
    return 'e_' + digest(json.dumps([world, kind, anchor], ensure_ascii=True,
                                  separators=(',', ':')).encode('ascii'))


def alias(identity):
    a = ['Avela', 'Nerion', 'Soryn', 'Velora', 'Tavren', 'Ilyra', 'Orun', 'Zeyra']
    b = ['Nebel', 'Funke', 'Kiesel', 'Welle', 'Stern', 'Wind', 'Moos', 'Faden']
    return a[int(identity[2:4], 16) % len(a)] + '-' + b[int(identity[4:6], 16) % len(b)] + '-' + identity[-12:]


def text(raw):
    return raw.rstrip(b'\0').decode('cp1252')


def parts(body):
    cursor = 0
    result = []
    while cursor < len(body):
        if len(body) - cursor < 8:
            raise ValueError('Truncated subrecord header')
        tag, size = struct.unpack_from('<4sI', body, cursor)
        cursor += 8
        value = body[cursor:cursor + size]
        if len(value) != size:
            raise ValueError('Truncated subrecord body')
        cursor += size
        result.append((tag, value))
    return result


def records(path):
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError('Content file exceeds the 128 MiB bound')
    with path.open('rb') as stream:
        while header := stream.read(16):
            offset = stream.tell() - 16
            if len(header) != 16:
                raise ValueError('Truncated record header')
            tag, size, unknown, flags = struct.unpack('<4sIII', header)
            if size > 64 * 1024 * 1024:
                raise ValueError('Record exceeds the 64 MiB bound')
            body = stream.read(size)
            if len(body) != size:
                raise ValueError('Truncated record body')
            yield tag, parts(body), digest(header + body), offset


def source_config(config):
    config = config.resolve(strict=True)
    if config.stat().st_size > 1024 * 1024:
        raise ValueError('Config exceeds the 1 MiB bound')
    roots, names, resets, local = [], [], set(), None
    for row in config.read_text(encoding='utf-8-sig').splitlines():
        if row.startswith('config='):
            raise ValueError('Use an explicit flat isolated config; includes are unsupported')
        if row.startswith('replace='):
            key = row.split('=', 1)[1].strip()
            if key in {'config', 'data', 'content'}:
                if roots or names or local is not None or key in resets:
                    raise ValueError('Source resets must occur once before all source entries')
                resets.add(key)
            elif key not in {'fallback', 'fallback-archive', 'groundcover'}:
                raise ValueError('Unsupported replacement directive')
        elif row.startswith(('data=', 'data-local=')):
            if resets != {'config', 'data', 'content'}:
                raise ValueError('Explicit config/data/content resets are required')
            path = Path(row.split('=', 1)[1].strip().strip('"'))
            if not path.is_absolute():
                path = config.parent / path
            path = path.resolve(strict=True)
            if not path.is_dir():
                raise ValueError('Data root is not a directory')
            if row.startswith('data-local='):
                if local is not None:
                    raise ValueError('Duplicate data-local directive')
                local = path
            else:
                roots.append(path)
        elif row.startswith('content='):
            if resets != {'config', 'data', 'content'}:
                raise ValueError('Explicit source resets are required')
            name = row.split('=', 1)[1].strip()
            if '/' in name or '\\' in name or ':' in name or name in {'', '.', '..'}:
                raise ValueError('Content must be a simple filename')
            if Path(name).suffix.casefold() in {'.esm', '.esp', '.omwaddon', '.omwgame'}:
                names.append(name)
    if local is not None:
        roots.append(local)
    if not roots or not names or len(names) != len(set(n.casefold() for n in names)):
        raise ValueError('Missing roots/content or duplicate logical content')
    sources = []
    for name in names:
        path = next((root / name for root in reversed(roots) if (root / name).is_file()), None)
        if path is None:
            raise ValueError('Unresolved content: ' + name)
        sources.append(path.resolve(strict=True))
    return config, roots, sources


def field(ps, tag, default=None):
    return next((value for key, value in ps if key == tag), default)


def record_anchor(kind, ps, source, offset, topic):
    if kind == 'CELL':
        data = field(ps, b'DATA')
        if data is None or len(data) != 12:
            raise ValueError('CELL requires the original 12-byte DATA field')
        flags, x, y = struct.unpack('<Iii', data)
        if flags & 1:
            return 'interior:' + text(field(ps, b'NAME', b'')).casefold(), 'SEMANTIC_ADDRESS'
        return f'exterior:{x},{y}', 'SEMANTIC_ADDRESS'
    if kind == 'SCPT' and field(ps, b'SCHD') is not None:
        return text(field(ps, b'SCHD')[:32]).casefold(), 'SEMANTIC_ADDRESS'
    if kind == 'SKIL' and field(ps, b'INDX') is not None:
        return 'skill:' + str(struct.unpack('<I', field(ps, b'INDX'))[0]), 'SEMANTIC_ADDRESS'
    if kind == 'LAND' and field(ps, b'INTV') is not None:
        x, y = struct.unpack('<ii', field(ps, b'INTV'))
        return f'land:{x},{y}', 'SEMANTIC_ADDRESS'
    if kind == 'INFO' and field(ps, b'INAM') is not None:
        return topic + '/' + text(field(ps, b'INAM')).casefold(), 'SEMANTIC_ADDRESS'
    if field(ps, b'NAME') is not None:
        return text(field(ps, b'NAME')).casefold(), 'SEMANTIC_ADDRESS'
    # These records receive an explicitly snapshot-scoped address, not a false
    # promise of stable identity across a rewritten source file.
    return source.casefold() + ':offset:' + str(offset), 'SNAPSHOT_ADDRESS'


def make_entry(world, kind, anchor, state_hash, source, basis, extra=None):
    identity = eid(world, kind, anchor)
    value = {'id': identity, 'inventedName': alias(identity), 'world': world,
             'kind': kind, 'anchor': anchor, 'identityBasis': basis,
             'stateSha256': state_hash, 'sourceFile': source}
    if extra:
        value.update(extra)
    return value


def catalogue(config, destination, asset_root=None):
    config, roots, sources = source_config(config)
    destination = destination.resolve()
    if destination.exists():
        raise ValueError('Output must be a fresh directory')
    protected = [config.parent, *roots, Path(__file__).resolve().parent]
    if asset_root:
        asset_root = asset_root.resolve(strict=True)
        if not asset_root.is_dir():
            raise ValueError('Asset root must be a directory')
        protected.append(asset_root)
    for root in protected:
        if destination == root or destination.is_relative_to(root) or root.is_relative_to(destination):
            raise ValueError('Output must be outside source package, source config and game data roots')
    config_hash = file_digest(config)
    before = {str(path): file_digest(path) for path in sources}
    templates, refs, gaps, parsed, topic = {}, {}, [], collections.Counter(), ''
    for source in sources:
        masters = []
        for tag, ps, state_hash, offset in records(source):
            kind = tag.decode('ascii')
            parsed[kind] += 1
            if kind == 'TES3':
                masters = [text(v) for k, v in ps if k == b'MAST']
                continue
            anchor, basis = record_anchor(kind, ps, source.name, offset, topic)
            if kind == 'DIAL':
                topic = anchor
            entry = make_entry(WORLD, 'RECORD/' + kind, anchor, state_hash,
                               source.name, basis, {'recordType': kind,
                               'deleted': field(ps, b'DELE') is not None})
            templates[(kind, anchor)] = entry
            if kind != 'CELL':
                continue
            if any(k == b'MVRF' for k, v in ps):
                gaps.append({'kind': 'MOVED_REFERENCE_RESOLUTION', 'sourceFile': source.name,
                             'cell': anchor, 'status': 'UNKNOWN'})
            starts = [i for i, (key, value) in enumerate(ps) if key == b'FRMR']
            for start, stop in zip(starts, starts[1:] + [len(ps)]):
                group = ps[start:stop]
                if len(group[0][1]) != 4:
                    raise ValueError('Only original 4-byte FRMR records are supported')
                raw = struct.unpack('<I', group[0][1])[0]
                high = raw >> 24
                if high > len(masters):
                    gaps.append({'kind': 'UNRESOLVED_REFERENCE_OWNER', 'sourceFile': source.name,
                                 'cell': anchor, 'rawRefnum': raw, 'status': 'UNKNOWN'})
                    origin, index, ref_basis = source.name, raw, 'SNAPSHOT_ADDRESS'
                else:
                    origin = masters[high - 1] if high else source.name
                    index = raw & 0xffffff if high else raw
                    ref_basis = 'SOURCE_REFERENCE_OWNER_AND_INDEX'
                ref_anchor = origin.casefold() + ':' + str(index)
                base = field(group, b'NAME')
                payload = b''.join(struct.pack('<4sI', k, len(v)) + v for k, v in group)
                refs[ref_anchor] = make_entry(WORLD, 'INSTANCE', ref_anchor, digest(payload),
                    source.name, ref_basis, {'recordId': text(base).casefold() if base else None,
                    'cell': anchor, 'deleted': field(group, b'DELE') is not None})
    by_name = collections.defaultdict(list)
    for (kind, anchor), entry in templates.items():
        if kind != 'CELL':
            by_name[anchor].append(entry['id'])
    for entry in refs.values():
        entry['templateIds'] = by_name.get(entry['recordId'], [])
        if len(entry['templateIds']) != 1:
            entry['templateResolution'] = 'UNKNOWN'
    own_assets = []
    if asset_root:
        for path in sorted(asset_root.rglob('*')):
            if path.is_symlink():
                raise ValueError('Asset symlinks are unsupported')
            if path.is_file():
                relative = path.relative_to(asset_root).as_posix()
                own_assets.append(make_entry('HALVETH-OWN-ASSETS', 'FILE', relative,
                    file_digest(path), 'OWN_ASSET_ROOT', 'RELATIVE_FILE_ADDRESS'))
    entries = sorted([*templates.values(), *refs.values(), *own_assets], key=lambda v: v['id'])
    if len(entries) != len({entry['id'] for entry in entries}):
        raise ValueError('Duplicate identity addresses')
    if before != {str(path): file_digest(path) for path in sources} or config_hash != file_digest(config):
        raise ValueError('Source changed during the read-only catalogue')
    destination.mkdir(parents=True)
    registry = destination / 'registry.jsonl.gz'
    with registry.open('wb') as target, gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as packed:
        for entry in entries:
            packed.write((json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode('ascii'))
    # The demo binds real source identities; all relationship rules remain the
    # separate prototype's declared design, never inferred from these records.
    npc = next((v for v in refs.values() if v['recordId'] == 'fargoth' and not v['deleted']), None)
    npc = npc or next((v for (k, a), v in templates.items() if k == 'NPC_' and a == 'fargoth'), None)
    dagoth = next((v for v in refs.values() if v['recordId'] and
                   ('dagoth_ur' in v['recordId'] or 'dagoth ur' in v['recordId']) and not v['deleted']), None)
    cup = next((v for v in refs.values() if v['recordId'] and 'goblet' in v['recordId'] and not v['deleted']), None)
    demo = [('actor', npc), ('dagoth', dagoth), ('cup', cup)]
    if all(v is not None for role, v in demo):
        (destination / 'DEMO_ENTITIES.tsv').write_text(''.join(role + '\t' + v['id'] + '\t' + v['inventedName'] + '\n' for role, v in demo), encoding='ascii')
    counts = dict(collections.Counter(v['kind'] for v in entries))
    receipt = {'schema': VERSION, 'recordedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'coverage': 'FINITE_SOURCE_RECORD_AND_FRMR_SNAPSHOT', 'sources': before,
        'sourceConfigSha256': config_hash, 'sourceBytesUnchanged': True,
        'entities': len(entries), 'recordTemplates': len(templates), 'placedReferenceAddresses': len(refs),
        'ownProjectFiles': len(own_assets), 'kinds': counts, 'recordsRead': dict(parsed),
        'snapshotAddressCount': sum(v['identityBasis'] == 'SNAPSHOT_ADDRESS' for v in entries),
        'unknownReferenceTemplates': sum(v.get('templateResolution') == 'UNKNOWN' for v in refs.values()),
        'observationGaps': gaps, 'registrySha256': file_digest(registry),
        'excluded': ['SAVE_RUNTIME_CREATED_OBJECTS', 'BSA_INTERNAL_FILES', 'UNCONNECTED_EXTERNAL_WORLDS',
                     'REAL_HUMAN_IDENTITY', 'BIOLOGICAL_ENERGY_SENSOR', 'NATIVE_APPEARANCE_MUTATION'],
        'reopenTrigger': 'Bind a save-aware/native runtime adapter or an explicit new owned world namespace'}
    (destination / 'CATALOGUE_PRIVATE.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: receipt[k] for k in ['coverage', 'entities', 'recordTemplates', 'placedReferenceAddresses', 'ownProjectFiles', 'snapshotAddressCount', 'unknownReferenceTemplates']}, indent=2))
    return receipt


def bind_demo(directory):
    receipt = json.loads((directory / 'CATALOGUE_PRIVATE.json').read_text(encoding='utf8'))
    registry = directory / 'registry.jsonl.gz'
    if file_digest(registry) != receipt['registrySha256']:
        raise ValueError('The source registry changed')
    chosen = {}
    with gzip.open(registry, 'rt', encoding='ascii') as stream:
        for row in stream:
            e = json.loads(row)
            if e['kind'] != 'INSTANCE' or e['deleted']:
                continue
            rid = e.get('recordId') or ''
            if rid == 'fargoth':
                chosen.setdefault('actor', e)
            if 'dagoth_ur' in rid or 'dagoth ur' in rid:
                chosen.setdefault('dagoth', e)
            if 'goblet' in rid:
                chosen.setdefault('cup', e)
    if set(chosen) != {'actor', 'dagoth', 'cup'}:
        raise ValueError('The three exact demo roles are unresolved; no synthetic fallback is relabelled as source-bound')
    target = directory / 'DEMO_ENTITIES.tsv'
    if target.exists():
        raise ValueError('The existing role binding must not be overwritten')
    target.write_text(''.join(role + '\t' + chosen[role]['id'] + '\t' + chosen[role]['inventedName'] + '\n'
                             for role in ['actor', 'dagoth', 'cup']), encoding='ascii')
    (directory / 'DEMO_BINDING_PRIVATE.json').write_text(json.dumps({
        'registrySha256': receipt['registrySha256'], 'bindingSha256': file_digest(target),
        'selectionRule': 'Lowest ASCII entity ID per declared original-reference role',
        'roles': chosen, 'storyRules': 'DECLARED_SEPARATE_PROTOTYPE_DESIGN'}, indent=2) + '\n', encoding='utf8')
    print('BOUND: three actual placed-reference IDs. The Dagoth endpoint can be a CREA record.')


def find(registry, query, limit):
    count = 0
    with gzip.open(registry, 'rt', encoding='ascii') as stream:
        for row in stream:
            entry = json.loads(row)
            if query.casefold() in (entry['id'] + ' ' + entry['inventedName'] + ' ' + entry['anchor'] + ' ' + str(entry.get('recordId', ''))).casefold():
                print(json.dumps(entry, ensure_ascii=False))
                count += 1
                if count >= limit:
                    break
    print('SHOWN', count, '; display bound', limit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    build = commands.add_parser('catalogue')
    build.add_argument('--config', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--assets', type=Path)
    query = commands.add_parser('find')
    query.add_argument('--registry', type=Path, required=True)
    query.add_argument('--query', required=True)
    query.add_argument('--limit', type=int, default=8)
    bind = commands.add_parser('bind-demo')
    bind.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'catalogue':
        catalogue(args.config, args.output, args.assets)
    elif args.mode == 'bind-demo':
        bind_demo(args.directory)
    else:
        if not 1 <= args.limit <= 100:
            raise ValueError('Limit must be between 1 and 100')
        find(args.registry, args.query, args.limit)


if __name__ == '__main__':
    main()
