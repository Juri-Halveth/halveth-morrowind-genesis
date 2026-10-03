"""MIT. Create only new own profile/modules; OpenMW/runtime inputs stay read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
ORDER = ('courier', 'fieldwork', 'hud', 'audio')
MODULES = {
    'courier': ('gameplay', 'veyra-courier.omwscripts',
                ('scripts/veyra_courier/config.lua', 'scripts/veyra_courier/routes.lua',
                 'scripts/veyra_courier/global.lua', 'scripts/veyra_courier/player.lua')),
    'fieldwork': ('gameplay', 'veyra-fieldwork.omwscripts',
                  ('scripts/veyra_fieldwork/config.lua', 'scripts/veyra_fieldwork/global.lua',
                   'scripts/veyra_fieldwork/player.lua')),
    'hud': ('presentation', 'Veyra-Presentation.omwscripts', ('scripts/veyra/hud.lua',)),
    'audio': ('presentation/spatial-audio', 'Veyra-Spatial-Audio.omwscripts',
              ('scripts/veyra/spatial_audio.lua', 'Sound/veyra/courier_bell_mono.wav')),
}
PROBE = re.compile(r'probe|fixture|world-test', re.I)
WHITE_SHA = '245a82e115217ea58a29329710f13d48617347f30d71db98f8c7657ad7b696d5'
AUDIO_SOURCE = {
    'archiveSha256': '029d734af1582474edf3a694d1b0cebc97c1c152f2f39fa34d4c2bafc5de77f8',
    'member': 'Audio/impactBell_heavy_000.ogg',
    'memberSha256': '94b8bb5f2d43ab65e4bcc32b28562416e9bc2c51d9fd4be1e333660ee52f977f',
    'licenseMemberSha256': 'b49aa9c56b04528b95913de13e506a0f7c5e807b9925db9bfef86af1f91120db',
    'license': 'CC0-1.0',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def entries(path):
    rows = []
    raw = path.read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Configuration exceeds bounded input size')
    for line in raw.decode('utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Malformed configuration line')
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', key):
            raise ValueError('Malformed configuration key')
        rows.append((key.lower(), value))
    return rows


def unquote(value):
    if value.startswith('"'):
        if not value.endswith('"') or len(value) < 2:
            raise ValueError('Unbalanced OpenMW path quotes')
        value = value[1:-1]
        value = re.sub(r'&([&"])', r'\1', value)
    elif value.endswith('"'):
        raise ValueError('Unbalanced OpenMW path quotes')
    return value


def resolved(value, anchor):
    value = unquote(value)
    if not value or '?' in value:
        raise ValueError('Unresolved OpenMW path token or empty path')
    if os.name != 'nt' and re.match(r'^[a-zA-Z]:[\\/]', value):
        raise ValueError('Windows configuration requires a native Windows Python')
    path = Path(value)
    return (path if path.is_absolute() else anchor / path).resolve()


def quoted(path):
    return '"' + path.as_posix().replace('&', '&&').replace('"', '&"') + '"'


def disjoint(destination, protected):
    for source in protected:
        if destination == source or destination in source.parents or source in destination.parents:
            raise ValueError('Destination overlaps a protected input')


def input_row(path, destination=None):
    if not path.is_file() or path.is_symlink():
        raise ValueError('Required regular input missing or symlinked: ' + str(path))
    row = {'path': str(path), 'sha256': digest(path.read_bytes())}
    if destination is not None:
        row['destination'] = destination
    return row


def make_plan(base_profile, engine, destination, modules):
    base, exe = Path(base_profile).resolve(), Path(engine).resolve()
    target = Path(destination).resolve()
    if Path(destination).exists() or Path(destination).is_symlink():
        raise ValueError('Destination already exists; initial provision needs a new directory')
    selected = tuple(name for name in ORDER if name in modules)
    if not selected or len(modules) != len(set(modules)) or set(modules) - set(ORDER):
        raise ValueError('Select unique known production modules')
    base_cfg = base / ('play.cfg' if (base / 'play.cfg').is_file() else 'openmw.cfg')
    settings, bootstrap = base / 'settings.cfg', exe.parent / 'openmw.cfg'
    inputs = [input_row(path) for path in (base_cfg, settings, exe, bootstrap)]
    rows, defaults = entries(base_cfg), entries(bootstrap)
    if any(key == 'config' for key, _ in rows):
        raise ValueError('Nested base configuration requires explicit resolution before provision')
    for key, value in rows + defaults:
        if key == 'script-run' or (key == 'skip-menu' and value.lower() in ('true', '1')):
            raise ValueError('Base configuration contains an automatic startup command')
        if key == 'content' and PROBE.search(unquote(value)):
            raise ValueError('Base configuration contains a native test registration')
    resources_values = [(value, base) for key, value in rows if key == 'resources']
    resources_values += [] if resources_values else [(value, exe.parent) for key, value in defaults if key == 'resources']
    if not resources_values:
        raise ValueError('No explicitly bound engine resources directory')
    resources = resolved(*resources_values[-1])
    if not resources.is_dir():
        raise ValueError('Engine resources directory is unavailable')
    data = [(resolved(value, exe.parent), 'ENGINE_BOOTSTRAP') for key, value in defaults if key == 'data']
    data += [(resolved(value, base), 'BASE_PROFILE') for key, value in rows if key == 'data']
    # Retain base local assets as a read-only data reference, then give generated
    # files a new data-local location. Never reuse the original write destination.
    data += [(resolved(value, base), 'BASE_LOCAL_ASSETS') for key, value in rows if key == 'data-local']
    if not data or any(not path.is_dir() for path, _ in data):
        raise ValueError('A required read-only data directory is unavailable')
    protected = [base, exe.parent, resources, ROOT.resolve(), *[path for path, _ in data]]
    protected.extend(resolved(value, base) for key, value in rows if key in ('user-data', 'data-local'))
    payload = [input_row(ROOT / 'LICENSE', 'LICENSE')]
    optional_copies = []
    for name in ('shaders.yaml', 'input_v3.xml'):
        path = base / name
        if path.exists() or path.is_symlink():
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 256 * 1024:
                raise ValueError('Optional profile input is outside its regular bounded-file contract')
            payload.append(input_row(path, 'profile/' + name))
            optional_copies.append(name)
    for name in selected:
        folder, registration, scripts = MODULES[name]
        package = ROOT / folder
        protected.append((package / 'mod').resolve())
        for relative in (registration, *scripts):
            payload.append(input_row(package / 'mod' / relative, 'modules/' + name + '/mod/' + relative))
        payload.append(input_row(package / 'LICENSE', 'modules/' + name + '/LICENSE'))
        if name == 'hud':
            for relative in ('build-assets.py', 'check-assets.py'):
                payload.append(input_row(package / relative, 'modules/hud/' + relative))
        if name == 'audio':
            receipt_file = package / 'ASSET_RECEIPT.json'
            receipt = json.loads(receipt_file.read_bytes())
            wav = package / 'mod/Sound/veyra/courier_bell_mono.wav'
            if any(receipt['source'].get(key) != value for key, value in AUDIO_SOURCE.items()) or receipt['output']['sha256'] != digest(wav.read_bytes()):
                raise ValueError('Built audio lacks its matching CC0 input/output receipt')
            with wave.open(str(wav), 'rb') as decoded:
                if (decoded.getnchannels(), decoded.getsampwidth(), decoded.getframerate()) != (1, 2, 44100) or decoded.getnframes() < 1:
                    raise ValueError('Built audio does not meet the reviewed mono PCM contract')
            inputs.append(input_row(receipt_file))
            for relative in ('KENNEY-LICENSE.txt', 'THIRD_PARTY_NOTICES.md'):
                payload.append(input_row(package / relative, 'modules/audio/' + relative))
            if digest((package / 'KENNEY-LICENSE.txt').read_bytes()) != receipt['source']['licenseMemberSha256']:
                raise ValueError('Built audio license differs from the bound license member')
    disjoint(target, protected)
    plan = {
        'schema': 'veyra.workshop.provision-plan.v1', 'dataClass': 'RESTRICTED_RAW',
        'destination': str(target), 'baseProfile': str(base), 'baseConfig': str(base_cfg),
        'engine': str(exe), 'engineCwd': str(exe.parent), 'resources': str(resources),
        'modules': list(selected), 'inputs': inputs, 'payload': payload,
        'optionalProfileCopies': optional_copies,
        'dataReferences': [{'path': str(path), 'sourceRole': role} for path, role in data],
        'protectedPaths': [str(path) for path in protected],
        'profile': str(target / 'profile'),
        'engineArguments': ['--replace', 'config', '--config', str(target / 'profile'), '--no-grab'],
        'sourceWrites': 0, 'runtimeWrites': 0, 'networkEffects': 0, 'engineExecution': 'NOT_REQUESTED',
    }
    plan['planDigest'] = digest(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode('utf8'))
    return plan


def fresh_inputs(plan):
    for row in plan['inputs'] + plan['payload']:
        path = Path(row['path'])
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != row['sha256']:
            raise ValueError('A bound input changed; make a fresh plan')


def copy_owned_file(row, stage):
    data = Path(row['path']).read_bytes()
    if digest(data) != row['sha256']:
        raise ValueError('A bound source changed during copying')
    output = stage / row['destination']
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(data)
    if digest(output.read_bytes()) != row['sha256'] or os.path.samefile(output, row['path']):
        raise ValueError('Own copy identity/content check failed')


def render_config(plan):
    destination = Path(plan['destination'])
    profile = destination / 'profile'
    rows = entries(Path(plan['baseConfig']))
    defaults = entries(Path(plan['engine']).parent / 'openmw.cfg')
    result = ['# Own isolated workshop profile; referenced inputs remain external.',
              'replace=config', 'replace=data', 'replace=content', 'replace=fallback-archive',
              'replace=fallback',
              'resources=' + quoted(Path(plan['resources'])),
              'user-data=' + quoted(profile / 'user'), 'data-local=' + quoted(profile / 'data')]
    # Snapshot required bound bootstrap values into the owned profile. The local
    # bootstrap is inevitably loaded, so explicit replace directives avoid relying
    # on a later changed fallback/content/data list from that external directory.
    seen = set()
    for key, value in defaults:
        if key in ('fallback', 'fallback-archive', 'content', 'encoding'):
            result.append(key + '=' + value)
            if key == 'content':
                seen.add(unquote(value).casefold())
    for reference in plan['dataReferences']:
        if reference['sourceRole'] == 'ENGINE_BOOTSTRAP':
            result.append('data=' + quoted(Path(reference['path'])))
    for key, value in rows:
        if key == 'data':
            result.append('data=' + quoted(resolved(value, Path(plan['baseProfile']))))
        elif key not in ('config', 'replace', 'resources', 'user-data', 'data-local'):
            result.append(key + '=' + value)
            if key == 'content':
                seen.add(unquote(value).casefold())
    for reference in plan['dataReferences']:
        if reference['sourceRole'] == 'BASE_LOCAL_ASSETS':
            result.append('data=' + quoted(Path(reference['path'])))
    for name in plan['modules']:
        registration = MODULES[name][1]
        result.append('data=' + quoted(destination / 'modules' / name / 'mod'))
        if registration.casefold() not in seen:
            result.append('content=' + registration)
            seen.add(registration.casefold())
    return '\n'.join(result) + '\n'


def apply_plan(plan):
    target = Path(plan['destination'])
    if target.exists() or target.is_symlink():
        raise ValueError('Destination appeared after planning')
    disjoint(target.resolve(), [Path(path).resolve() for path in plan['protectedPaths']])
    fresh_inputs(plan)
    nonce = uuid.uuid4().hex
    stage = target.parent / (target.name + '.stage-' + nonce)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    expected_stage = stage.resolve()
    disjoint(expected_stage, [Path(path).resolve() for path in plan['protectedPaths']])
    marker = stage / '.owned-provision-stage'
    marker.write_text(nonce, encoding='ascii')
    try:
        for row in plan['payload']:
            copy_owned_file(row, stage)
        profile = stage / 'profile'
        (profile / 'user').mkdir(parents=True)
        (profile / 'data').mkdir()
        config = render_config(plan)
        for name in ('openmw.cfg', 'play.cfg'):
            (profile / name).write_text(config, encoding='utf8', newline='\n')
        settings = next(row for row in plan['inputs'] if Path(row['path']).name == 'settings.cfg')
        copy_owned_file({**settings, 'destination': 'profile/settings.cfg'}, stage)
        if 'hud' in plan['modules']:
            for script in ('build-assets.py', 'check-assets.py'):
                subprocess.run([sys.executable, str(stage / 'modules/hud' / script)],
                               check=True, capture_output=True, text=True)
            generated = stage / 'modules/hud/mod/Textures/veyra/white.png'
            if digest(generated.read_bytes()) != WHITE_SHA:
                raise ValueError('Own HUD texture differs from the reviewed pixel contract')
        fresh_inputs(plan)
        outputs = {path.relative_to(stage).as_posix(): digest(path.read_bytes())
                   for path in sorted(stage.rglob('*')) if path.is_file() and path != marker}
        receipt = {**plan, 'schema': 'veyra.workshop.provision-receipt.v1', 'status': 'OWN_COPIES_CREATED',
                   'sourceHashesUnchanged': True, 'outputs': outputs, 'nativeAcceptance': 'NOT_RUN'}
        (stage / 'INSTALL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
        if target.exists() or target.is_symlink():
            raise ValueError('Destination appeared during provisioning')
        stage.rename(target)
        (target / marker.name).unlink()
        return receipt
    except BaseException:
        # This fresh stage was created here; never remove the requested final target.
        if stage.exists() and not stage.is_symlink() and stage.resolve() == expected_stage:
            if marker.is_file() and marker.read_text(encoding='ascii') == nonce:
                shutil.rmtree(stage)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'apply'))
    parser.add_argument('--base-profile', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--modules', default='courier,hud,fieldwork')
    parser.add_argument('--expect-plan', help='Optional exact digest of the reviewed read-only plan')
    args = parser.parse_args()
    names = args.modules.split(',')
    plan = make_plan(args.base_profile, args.engine, args.destination, names)
    if args.expect_plan is not None and args.expect_plan != plan['planDigest']:
        raise ValueError('Current input/destination plan differs from the reviewed digest')
    result = plan if args.action == 'plan' else apply_plan(plan)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
