"""Build one-file Windows setups for the existing TES III: Morrowind world.

The public candidate includes only own Genesis content and Python's official
embeddable runtime. --local-engine additionally packages the user's installed
OpenMW 0.51 engine binaries for a private, non-published candidate. Neither
variant includes Bethesda game data, saves, mod downloads or model weights.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
VERSION = '1.0.1'
PYTHON_VERSION = '3.14.7'
PYTHON_URL = f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip'
PYTHON_SHA256 = 'd297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15'
OPENMW_SOURCE = 'https://gitlab.com/OpenMW/openmw/-/tags/openmw-0.51.0'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def official_python() -> bytes:
    cache = ROOT / '.local' / 'installer-cache' / f'python-{PYTHON_VERSION}-embed-amd64.zip'
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        request = urllib.request.Request(PYTHON_URL, headers={'User-Agent': 'HALVETH-Genesis-Installer-Build/0.8'})
        with urllib.request.urlopen(request, timeout=120) as response, cache.open('wb') as output:
            shutil.copyfileobj(response, output)
    raw = cache.read_bytes()
    if digest(raw) != PYTHON_SHA256:
        raise ValueError('Official Python embeddable ZIP SHA-256 differs from python.org release page.')
    return raw


def owned_sources() -> dict[str, bytes]:
    sys.path.insert(0, str(ROOT))
    from scripts.build_release import collect_files, validate_files
    source = collect_files()
    validate_files(source)
    return {f'app/{path}': data for path, data in source.items() if path != 'RELEASE-NOTE.txt'}


def python_runtime(raw: bytes) -> dict[str, bytes]:
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip():
            raise ValueError('Official Python ZIP CRC verification failed.')
        for name in archive.namelist():
            if '/' in name or '\\' in name or name.startswith('.'):
                raise ValueError('Unexpected Python runtime path: ' + name)
            files[f'runtime/{name}'] = archive.read(name)
    if 'runtime/python.exe' not in files or 'runtime/LICENSE.txt' not in files:
        raise ValueError('Official Python runtime is incomplete.')
    # The private interpreter sees installed app modules but no global packages.
    files['runtime/python314._pth'] = b'python314.zip\n.\n../app\n'
    return files


def local_openmw(root: Path) -> dict[str, bytes]:
    root = root.resolve()
    if not (root / 'openmw.exe').is_file() or not (root / 'LICENSE.txt').is_file():
        raise FileNotFoundError('Expected OpenMW engine/openmw.exe and GPLv3 LICENSE.txt.')
    readme = (root / 'README.txt').read_text(encoding='utf-8', errors='replace')
    if '* Version: 0.51.0' not in readme or '* License: GPLv3' not in readme:
        raise ValueError('Only the locally inspected OpenMW 0.51.0/GPLv3 engine is supported.')
    allowlist = HERE / 'openmw-0.51.0-runtime-files.txt'
    allowed = {line.strip() for line in allowlist.read_text(encoding='utf-8-sig').splitlines()
               if line.strip() and not line.startswith('#')}
    if len(allowed) < 100 or 'openmw.exe' not in allowed or 'openmw.cfg' not in allowed:
        raise ValueError('The exact OpenMW runtime inventory is incomplete.')
    files = {}
    present = set()
    for path in root.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('Links in engine runtime require review: ' + str(path))
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in allowed:
            # Never package new files from a mutable local engine directory.
            # A changed official runtime inventory needs human review first.
            continue
        present.add(relative)
        if relative == 'openmw.cfg':
            cfg = path.read_text(encoding='utf-8', errors='replace')
            if 'C:/Users/' in cfg or 'C:\\Users\\' in cfg:
                raise ValueError('Engine-local config contains a machine-specific path.')
        files[f'engine/{relative}'] = path.read_bytes()
    missing = allowed - present
    if missing:
        raise FileNotFoundError('Expected OpenMW runtime files missing: ' + ', '.join(sorted(missing)[:8]))
    if 'engine/openmw.exe' not in files or 'engine/resources/default.omwgame' not in files:
        # Resource manifests differ by release; the resources directory itself is mandatory.
        if not any(name.startswith('engine/resources/') for name in files):
            raise ValueError('OpenMW engine resources are absent.')
    return files


def make_payload(mode: str, engine: Path | None) -> dict:
    files = owned_sources()
    files.update(python_runtime(official_python()))
    if mode == 'local-engine':
        if engine is None:
            raise ValueError('--local-engine requires --engine-directory.')
        files.update(local_openmw(engine))
    records = [{'path': name, 'sha256': digest(data), 'bytes': len(data)}
               for name, data in sorted(files.items())]
    manifest = {'version': VERSION, 'mode': mode, 'pythonSha256': PYTHON_SHA256,
                'engineSource': OPENMW_SOURCE if mode == 'local-engine' else None,
                'files': records}
    payload = HERE / 'payload.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        archive.writestr('payload-manifest.json', json.dumps(manifest, indent=2).encode('utf-8'))
    with zipfile.ZipFile(payload) as archive:
        if archive.testzip():
            raise IOError('Installer payload CRC failed.')
    return {'mode': mode, 'files': len(files), 'payloadBytes': payload.stat().st_size,
            'payloadSha256': digest(payload.read_bytes()),
            'pythonSource': PYTHON_URL, 'pythonSha256': PYTHON_SHA256,
            'engineSource': OPENMW_SOURCE if mode == 'local-engine' else None,
            'engineExeSha256': digest(files['engine/openmw.exe']) if mode == 'local-engine' else None}


def build(args: argparse.Namespace) -> dict:
    mode = 'local-engine' if args.local_engine else 'owned-mod'
    payload = make_payload(mode, args.engine_directory)
    icon_source = HERE / 'love-astrolabe-icon-0.8.png'
    from PIL import Image
    with Image.open(icon_source) as image:
        image.save(HERE / 'love-astrolabe.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    target = ROOT / 'dist' / 'installer-candidates' / mode
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(['dotnet', 'publish', str(HERE / 'GenesisSetup.csproj'), '-c', 'Release',
                    '-r', 'win-x64', '--self-contained', 'true', '-o', str(target),
                    '/p:PublishSingleFile=true', '/p:IncludeNativeLibrariesForSelfExtract=true'], check=True)
    built = target / 'HALVETH Morrowind.exe'
    if not built.is_file():
        raise FileNotFoundError('dotnet publish did not produce one-file EXE.')
    name = (f'HALVETH-Morrowind-Genesis-{VERSION}-Local-Engine-Setup.exe' if args.local_engine
            else f'HALVETH-Morrowind-Genesis-{VERSION}-Setup.exe')
    output = ROOT / 'dist' / 'installer-candidates' / name
    shutil.copy2(built, output)
    receipt = {**payload, 'exe': str(output), 'bytes': output.stat().st_size,
               'sha256': digest(output.read_bytes()),
               'publication': 'LOCAL_ONLY_LICENSE_REVIEW_REQUIRED' if args.local_engine else 'PUBLIC_CANDIDATE_NOT_PUBLISHED',
               'containsBethesdaAssets': False, 'containsModelWeights': False,
               'runtime': 'Single visible launcher invoking installed OpenMW engine and the embedded Python companion.'}
    (output.with_suffix('.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-engine', action='store_true', help='Build private full-engine setup; never publish without GPL/dependency review.')
    parser.add_argument('--engine-directory', type=Path, help='Exact local OpenMW 0.51.0 engine folder for private build.')
    build(parser.parse_args())
