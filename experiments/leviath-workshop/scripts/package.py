"""Package only the explicit own-source allowlist, with bounded text inspection."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FIXED = {
    '.gitattributes', '.gitignore', 'LICENSE', 'README.md',
    'docs/SOURCE_BINDINGS.md', 'docs/NATIVE_SCOPE.md', 'docs/COURIER_NATIVE.json',
    'docs/COURIER_RELOAD_NATIVE.json', 'docs/COURIER_DEPOT_RELOAD_NATIVE.json',
    'docs/FIELDWORK_NATIVE.json', 'docs/FIELDWORK_DONE_RELOAD_NATIVE.json',
    'docs/FIELDWORK_WORKING_RELOAD_NATIVE.json',
    'docs/PRESENTATION_NATIVE.json',
    'docs/AUDIO_NATIVE.json', 'docs/CI_WORKSHOP.md',
    'scripts/workshop.sh', 'scripts/fetch-assets.sh', 'scripts/asset-sources.tsv',
    'scripts/package.py', 'scripts/check-lua.sh', 'tools/essences.sh', 'tests/test_bash_tools.py',
    'scripts/provision.sh', 'scripts/provision.py', 'tests/test_provision.py', 'docs/PROVISIONING.md',
    'docs/PROVISION_NATIVE.json',
    'tests/test_source_package.py',
    'tests/check-essences.sh', 'rules/policy.py', 'rules/check_policy.py',
    'presentation/LICENSE', 'presentation/README.md', 'presentation/build-assets.py',
    'presentation/check-assets.py',
    'presentation/check-hud.lua', 'presentation/CHECK_HUD.sh',
    'presentation/mod/Veyra-Presentation.omwscripts',
    'presentation/mod/scripts/veyra/hud.lua',
    'presentation/spatial-audio/build-audio.py',
    'presentation/spatial-audio/cfg-candidate.txt',
    'presentation/spatial-audio/CHECK_AUDIO.sh',
    'presentation/spatial-audio/check-audio.lua',
    'presentation/spatial-audio/LICENSE',
    'presentation/spatial-audio/README.md',
    'presentation/spatial-audio/THIRD_PARTY_NOTICES.md',
    'presentation/spatial-audio/mod/Veyra-Spatial-Audio.omwscripts',
    'presentation/spatial-audio/mod/scripts/veyra/spatial_audio.lua',
    'presentation/vegetation/build-vegetation.py',
    'presentation/vegetation/check-vegetation.py',
    'presentation/vegetation/README.md',
    'presentation/vegetation/THIRD_PARTY_NOTICES.md',
    'presentation/vegetation/cfg-additive.txt',
    'presentation/vegetation/cfg-tree02-override.txt',
    'gameplay/LICENSE', 'gameplay/README.md', 'gameplay/mod/veyra-courier.omwscripts',
    'gameplay/FIELDWORK.md', 'gameplay/mod/veyra-fieldwork.omwscripts',
    'docs/COURIER_STACK_NATIVE.json', 'docs/COURIER_TRANSFER_RELOAD_NATIVE.json',
    'docs/COURIER_CLAIMED_MIGRATION_NATIVE.json', 'docs/COURIER_DEPOT_MIGRATION_NATIVE.json',
    'gameplay/mod/scripts/veyra_fieldwork/config.lua',
    'gameplay/mod/scripts/veyra_fieldwork/global.lua',
    'gameplay/mod/scripts/veyra_fieldwork/player.lua',
    'gameplay/mod/scripts/veyra_courier/config.lua',
    'gameplay/mod/scripts/veyra_courier/routes.lua',
    'gameplay/mod/scripts/veyra_courier/global.lua',
    'gameplay/mod/scripts/veyra_courier/player.lua',
}
# A source release must be dependency-closed. Its production modules, registration
# files, checkers and notices cannot silently disappear from a successful bundle.
OPTIONAL_OBSERVATIONS = set()
REQUIRED = FIXED - OPTIONAL_OBSERVATIONS
LOCAL_PATH = re.compile(r'(?:[a-z]:[\\/]|/c/|/mnt/c/)Users[\\/][^\\/]+[\\/]', re.I)
PRIVATE_KEY = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
ACCESS_TOKEN = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})')


def collect():
    files = {}
    for relative in sorted(FIXED):
        candidate = ROOT / relative
        if not candidate.exists():
            continue
        if candidate.is_symlink() or any((ROOT / Path(*Path(relative).parts[:i])).is_symlink()
                                         for i in range(1, len(Path(relative).parts))):
            raise ValueError('Source symlink: ' + relative)
        if not candidate.is_file() or candidate.stat().st_size > 512 * 1024:
            raise ValueError('Source size/type outside contract: ' + relative)
        raw = candidate.read_bytes()
        text = raw.decode('utf-8-sig')
        if '\0' in text or LOCAL_PATH.search(text) or PRIVATE_KEY.search(text) or ACCESS_TOKEN.search(text):
            raise ValueError('Private/binary content requires review: ' + relative)
        files[relative] = raw
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError('Required source missing: ' + ', '.join(sorted(missing)))
    if b'MIT License' not in files['LICENSE']:
        raise ValueError('Own source license missing')
    for relative, raw in files.items():
        if relative.startswith('docs/') and relative.endswith('_NATIVE.json'):
            receipt = json.loads(raw)
            for source, expected in receipt['moduleHashes'].items():
                if source not in files or hashlib.sha256(files[source]).hexdigest() != expected:
                    raise ValueError('Native receipt/source binding differs: ' + relative + ' -> ' + source)
    return files


def manifest(files):
    rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())]
    serialized = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode('utf8')
    return {'schema': 'veyra.workshop.source-manifest.v1', 'dataClass': 'PUBLIC',
            'scope': 'EXPLICIT_OWN_SOURCE_ALLOWLIST_ONLY', 'files': rows,
            'filesDigest': hashlib.sha256(serialized).hexdigest(),
            'bytes': sum(len(raw) for raw in files.values()),
            'inspection': 'BOUND_TEXT_PATTERNS_HUMAN_REVIEW_REMAINS_REQUIRED',
            'gameData': 0, 'saveGames': 0, 'downloadedAssets': 0, 'modelWeights': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Optional exact source ZIP output path')
    args = parser.parse_args()
    files = collect()
    result = manifest(files)
    if args.archive:
        target = args.archive.resolve()
        if target.exists():
            raise ValueError('Existing archive retained; choose a new output')
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = dict(files)
        entries['SOURCE_MANIFEST.json'] = (json.dumps(result, indent=2) + '\n').encode('utf8')
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, raw in sorted(entries.items()):
                info = zipfile.ZipInfo('leviath-workshop/' + name, (2026, 10, 3, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip() is not None:
                raise ValueError('Source archive CRC check failed')
            for name, raw in entries.items():
                if archive.read('leviath-workshop/' + name) != raw:
                    raise ValueError('Archive roundtrip mismatch: ' + name)
        result['archive'] = {'filename': target.name, 'bytes': target.stat().st_size,
                             'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                             'roundtrip': 'EXACT_SOURCE_BYTES_PASS'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
