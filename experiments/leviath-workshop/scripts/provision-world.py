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
ORDER = ('frontier', 'frontier-textures', 'plaza', 'bark', 'crown', 'scenery', 'courier', 'fieldwork',
         'portal', 'construction', 'townlife', 'panels', 'hud', 'audio')
MODULES = {
    'bark': ('presentation/bark-materials',None,('Textures/veyra/swamp_bark.dds','Textures/veyra/swamp_bark_n.dds')),
    'crown': ('presentation/crown-candidate','Veyra-Dense-Crown.esp',
              ('Meshes/veyra/veyra_swamp_crown_01.dae','Textures/veyra/crown_leaf_01.dds')),
    'scenery': ('presentation/frontier-scenery-candidate','LEVIATH-Frontier-Scenery.esp',
                ('Meshes/veyra/frontier_scenery/veyra_frontier_grass_01.dae',
                 'Meshes/veyra/frontier_scenery/veyra_frontier_stone_cluster_01.dae')),
    'frontier': ('presentation/frontier-candidate', 'LEVIATH-Frontier.esp',
                 ('Textures/veyra/frontier/frontier_ground.dds',
                  'Textures/veyra/frontier/frontier_stone.dds', 'Textures/veyra/frontier/frontier_coast.dds')),
    'frontier-textures': ('presentation/frontier-texture-candidate', None,
                 ('Textures/veyra/frontier/frontier_ground.dds',
                  'Textures/veyra/frontier/frontier_stone.dds', 'Textures/veyra/frontier/frontier_coast.dds')),
    'plaza': ('presentation/plaza-candidate', 'LEVIATH-Plaza.esp',
                 ('Meshes/veyra/plaza/veyra_plaza_approach.dae',
                  'Meshes/veyra/plaza/veyra_plaza_arena.dae','Meshes/veyra/plaza/veyra_plaza_arrival.dae')),
    'courier': ('gameplay', 'veyra-courier.omwscripts',
                ('scripts/veyra_courier/config.lua', 'scripts/veyra_courier/routes.lua',
                 'scripts/veyra_courier/global.lua', 'scripts/veyra_courier/player.lua')),
    'fieldwork': ('gameplay', 'veyra-fieldwork.omwscripts',
                  ('scripts/veyra_fieldwork/config.lua', 'scripts/veyra_fieldwork/global.lua',
                   'scripts/veyra_fieldwork/player.lua')),
    'portal': ('gameplay/portal', 'veyra-portal.omwscripts',
               ('scripts/veyra_portal/config.lua','scripts/veyra_portal/global.lua','scripts/veyra_portal/player.lua')),
    'construction': ('gameplay/construction', 'veyra-construction.omwscripts',
               ('scripts/veyra_construction/config.lua','scripts/veyra_construction/global.lua',
                'scripts/veyra_construction/player.lua','Meshes/veyra/construction/plantbed.dae')),
    'townlife': ('gameplay/townlife', 'Veyra-Townlife.omwscripts',
               ('scripts/veyra_townlife/config.lua','scripts/veyra_townlife/global.lua',
                'scripts/veyra_townlife/actor.lua','scripts/veyra_townlife/player.lua',
                'Textures/veyra_townlife/white.png')),
    'panels': ('gameplay/panels', 'veyra-panel-coordinator.omwscripts',
               ('scripts/veyra_panels/player.lua','scripts/veyra_courier/config.lua',
                'scripts/veyra_courier/global.lua','scripts/veyra_courier/player.lua',
                'scripts/veyra_fieldwork/player.lua','scripts/veyra_portal/player.lua',
                'scripts/veyra_construction/player.lua','scripts/halveth/fieldcraft.lua',
                'scripts/halveth/knowledge.lua','scripts/halveth/paths.lua',
                'scripts/halveth/player.lua','scripts/halveth/universe.lua','scripts/halveth/worldlife.lua')),
    'hud': ('presentation/hud014', 'Veyra-Presentation.omwscripts', ('scripts/veyra/hud.lua','Textures/veyra/white.png')),
    'audio': ('presentation/spatial-audio', 'Veyra-Spatial-Audio.omwscripts',
              ('scripts/veyra/spatial_audio.lua', 'Sound/veyra/courier_bell_mono.wav')),
}
DEPENDENCIES = {'frontier-textures': ('frontier',), 'plaza': ('frontier','frontier-textures'),
                'crown': ('bark',), 'scenery': ('frontier','frontier-textures','crown'),
                'courier': ('panels',), 'fieldwork': ('panels',),
                'portal': ('frontier','panels'), 'construction': ('frontier','panels'),
                'townlife': ('frontier','frontier-textures','plaza'), 'audio': ('courier',)}
OWN_ASSETS = 'docs/OWN_ASSET_BINDINGS.json'
ENGINE_API_BINDINGS = 'docs/ENGINE_API_BINDINGS.json'
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


def file_digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def input_row(path, destination=None, maximum=None):
    if not path.is_file() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Required regular input missing or symlinked: ' + str(path))
    limit=maximum if maximum is not None else (16*1024*1024 if destination else 512*1024*1024)
    if path.stat().st_size > limit:
        raise ValueError('Input exceeds bounded copy contract')
    row = {'path': str(path), 'sha256': file_digest(path)}
    if destination is not None:
        row['destination'] = destination
    return row


def resolve_modules(requested):
    if not requested or len(requested) != len(set(requested)) or set(requested) - set(ORDER):
        raise ValueError('Select unique known production modules')
    resolved = set(requested)
    while True:
        before = set(resolved)
        for name in tuple(resolved):
            resolved.update(DEPENDENCIES.get(name, ()))
        if resolved == before:
            break
    # The exact fourteen-file overlay travels with its coordinator. Its scripts
    # only execute through an existing registration; Genesis globals/registrations
    # remain external bound base dependencies rather than inventing a new install.
    return tuple(name for name in ORDER if name in resolved)


def owned_asset_binding(package, relative, bindings):
    address = package.relative_to(ROOT).as_posix() + '/mod/' + relative
    row = bindings.get('assets', {}).get(address)
    if row is None:
        row = bindings.get('authoredAssets', {}).get(address)
    cc0=(package.relative_to(ROOT).as_posix()=='presentation/bark-materials' and relative in ('Textures/veyra/swamp_bark.dds','Textures/veyra/swamp_bark_n.dds')) or (
         package.relative_to(ROOT).as_posix()=='presentation/spatial-audio' and relative=='Sound/veyra/courier_bell_mono.wav')
    expected_license='CC0-1.0' if cc0 else 'MIT'
    if not row or row.get('license') != expected_license or row.get('originalGameAssetBytes') != 0:
        raise ValueError('Owned asset lacks an explicit source/license binding: ' + address)
    path = package / 'mod' / relative
    if path.stat().st_size != row['bytes'] or digest(path.read_bytes()) != row['sha256']:
        raise ValueError('Owned generated asset differs from its approved binding: ' + address)
    generator = ROOT / row['sourceGenerator'] if row.get('sourceGenerator') else None
    if generator is not None and digest(generator.read_bytes()) != row['sourceGeneratorSha256']:
        raise ValueError('Owned asset generator changed without a new binding')
    if cc0:
        for file_key,hash_key in (('licenseFile','licenseSha256'),('provenanceFile','provenanceSha256')):
            if file_digest(ROOT/row[file_key])!=row[hash_key]:
                raise ValueError('Bound CC0 legal/provenance bytes differ')
    return row


def verify_existing_vfs(data, payload, bindings, overlay, hud):
    # OpenMW picks VFS files by data order. Detect a different existing version
    # before writing, rather than hide it under a later own data directory.
    observed={}
    for row in payload:
        destination = row['destination']
        if '/mod/' not in destination:
            continue
        relative = destination.split('/mod/', 1)[1]
        for directory, _ in data:
            original = directory / relative
            if original.exists() or original.is_symlink():
                bound = input_row(original)
                observed[bound['path']]=bound
                allowed={row['sha256']}
                if relative.startswith('Textures/veyra/frontier/'):
                    allowed.update(asset['sha256'] for address,asset in bindings.get('assets',{}).items()
                                   if address.endswith('/mod/'+relative))
                if relative in overlay.get('allowedExistingHashes',{}):
                    allowed.update(overlay['allowedExistingHashes'][relative])
                if relative=='scripts/veyra/hud.lua' and hud:
                    allowed.add(hud['baseOwnHudSha256'])
                if bound['sha256'] not in allowed:
                    raise ValueError('Existing VFS source differs; choose a compatible base: ' + relative)
    return list(observed.values())


def bind_content_references(data, rows, defaults):
    found={}
    for key,value in defaults+rows:
        if key!='content':continue
        name=unquote(value)
        if '/' in name or '\\' in name or name in ('','.','..'):
            raise ValueError('Content name is outside the regular top-level reference contract')
        path=next((directory/name for directory,_ in reversed(data) if (directory/name).is_file()),None)
        if path is None:
            raise ValueError('Referenced base content is unavailable: '+name)
        row=input_row(path,maximum=256*1024*1024)
        found[row['path']]=row
    return list(found.values())


def make_plan(base_profile, engine, destination, modules):
    base, exe = Path(base_profile).resolve(), Path(engine).resolve()
    target = Path(destination).resolve()
    if Path(destination).exists() or Path(destination).is_symlink():
        raise ValueError('Destination already exists; initial provision needs a new directory')
    selected = resolve_modules(modules)
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
    api_path=ROOT/ENGINE_API_BINDINGS
    api=json.loads(api_path.read_bytes())
    if api.get('schema')!='veyra.workshop.engine-api-inputs.v1':
        raise ValueError('Engine API input contract differs')
    inputs.append(input_row(api_path))
    for name,h in api['resourcesFiles'].items():
        p=resources/name;row=input_row(p)
        if row['sha256']!=h:raise ValueError('Engine API/interface bytes differ from the bound native version: '+name)
        inputs.append(row)
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
    asset_names = [name for name in selected if name in ('frontier','frontier-textures','plaza','construction','townlife','hud','bark','crown','scenery','audio')]
    bindings = {}
    overlay = {}
    hud = {}
    if asset_names:
        bindings_file = ROOT / OWN_ASSETS
        inputs.append(input_row(bindings_file))
        bindings = json.loads(bindings_file.read_bytes())
        if bindings.get('schema') != 'veyra.workshop.own-assets.v1' or bindings.get('bethesdaAssetBytes') != 0:
            raise ValueError('Owned asset manifest has a different reviewed scope')
    if 'panels' in selected:
        overlay_path = ROOT/'gameplay/panels/SOURCE_BINDINGS.json'
        inputs.append(input_row(overlay_path))
        overlay=json.loads(overlay_path.read_bytes())
        if overlay.get('schema')!='veyra.workshop.overlay-bindings.v1':
            raise ValueError('Panel overlay has a different source contract')
    if 'hud' in selected:
        hud_path=ROOT/'presentation/hud014/SOURCE_BINDING.json'
        inputs.append(input_row(hud_path));hud=json.loads(hud_path.read_bytes())
        if hud.get('schema')!='veyra.hud-label-source.v1':
            raise ValueError('HUD has a different source contract')
        if digest((ROOT/'presentation/hud014/mod/scripts/veyra/hud.lua').read_bytes())!=hud['candidateHudSha256']:
            raise ValueError('HUD candidate differs from its source binding')
        if 'courier' in selected:
            bound=overlay['productionHashes']['scripts/veyra_courier/player.lua']
            if bound!=hud['courierKeyBinding']['sourceSha256']:
                raise ValueError('Courier key and HUD footer source bindings differ')
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
        for relative in ((registration,) if registration else ()) + scripts:
            if name=='panels' and digest((package/'mod'/relative).read_bytes())!=overlay['productionHashes'].get(relative):
                raise ValueError('Panel overlay source differs from its exact freeze')
            if relative.endswith(('.esp','.dds','.dae','.png','.wav')):
                owned_asset_binding(package, relative, bindings)
            payload.append(input_row(package / 'mod' / relative, 'modules/' + name + '/mod/' + relative))
        license_name='CC0-1.0.txt' if name=='bark' else 'LICENSE'
        payload.append(input_row(package / license_name, 'modules/' + name + '/' + license_name))
        if name=='bark':
            for relative in ('SOURCE_BINDING.json','THIRD_PARTY_NOTICES.md'):
                payload.append(input_row(package/relative,'modules/bark/'+relative))
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
    inputs+=verify_existing_vfs(data, payload, bindings, overlay, hud)
    inputs+=bind_content_references(data,rows,defaults)
    disjoint(target, protected)
    plan = {
        'schema': 'veyra.workshop.provision-plan.v2', 'dataClass': 'RESTRICTED_RAW',
        'destination': str(target), 'baseProfile': str(base), 'baseConfig': str(base_cfg),
        'engine': str(exe), 'engineCwd': str(exe.parent), 'resources': str(resources),
        'requestedModules': list(modules), 'modules': list(selected), 'inputs': inputs, 'payload': payload,
        'ownAssetBindingSha256': digest((ROOT / OWN_ASSETS).read_bytes()) if asset_names else None,
        'engineApiBindingSha256': digest(api_path.read_bytes()),
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
        if path.is_symlink() or not path.is_file() or file_digest(path) != row['sha256']:
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
        if registration and registration.casefold() not in seen:
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
