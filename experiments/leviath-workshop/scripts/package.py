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
    'scripts/workshop.sh', 'scripts/fetch-assets.sh', 'scripts/asset-sources.tsv',
    'scripts/package.py', 'scripts/check-lua.sh', 'tools/essences.sh', 'tests/test_bash_tools.py',
    'tests/test_source_package.py',
    'tests/check-essences.sh', 'rules/policy.py', 'rules/check_policy.py',
    'presentation/LICENSE', 'presentation/README.md', 'presentation/build-assets.py',
    'presentation/check-hud.lua', 'presentation/CHECK_HUD.sh',
    'presentation/mod/Veyra-Presentation.omwscripts',
    'presentation/mod/scripts/veyra/hud.lua',
    'presentation/vegetation/build-vegetation.py',
    'presentation/vegetation/check-vegetation.py',
    'presentation/vegetation/README.md',
    'presentation/vegetation/THIRD_PARTY_NOTICES.md',
    'presentation/vegetation/cfg-additive.txt',
    'presentation/vegetation/cfg-tree02-override.txt',
    'gameplay/LICENSE', 'gameplay/README.md', 'gameplay/check-courier.lua',
    'gameplay/CHECK_COURIER.sh', 'gameplay/mod/veyra-courier.omwscripts',
    'gameplay/mod/scripts/veyra_courier/config.lua',
    'gameplay/mod/scripts/veyra_courier/routes.lua',
    'gameplay/mod/scripts/veyra_courier/global.lua',
    'gameplay/mod/scripts/veyra_courier/player.lua',
}
REQUIRED = {'LICENSE', 'README.md', 'scripts/workshop.sh', 'scripts/fetch-assets.sh',
            'rules/policy.py', 'rules/check_policy.py', 'tools/essences.sh'}
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
