"""Package owned source and explicitly approved artwork without private game state."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0'
DEST=ROOT/'dist'/f'HALVETH-Morrowind-Genesis-{VERSION}-public-source.zip'
# Exact asset paths keep newly downloaded graphics and personal screenshots out,
# including files placed outside the ordinary .local directory.
ROOT_FILES={'.gitignore','.gitattributes','README.md','LICENSE','ASSET-LICENSE.md','THIRD-PARTY-NOTICES.md','CONTRIBUTING.md',
            'PUBLIC-STATUS.json','ASSET-PROVENANCE.json',
            'launcher.py','server.py','graphics_status.py','project_knowledge.py','character_profile.py','START.cmd'}
SOURCE_DIRECTORIES={'assets','data','docs','mod','native','scripts','tests','web','installer','.github','LICENSES'}
EXACT_TEXT_FILES={'.github/workflows/test.yml','LICENSES/CC0-1.0.txt',
                  'installer/GenesisSetup.csproj','installer/Program.cs','installer/build_installer.py',
                  'installer/README.md','installer/openmw-0.51.0-runtime-files.txt',
                  'docs/NATIVE-VERIFICATION-0.4.0.json','docs/NATIVE-VERIFICATION-0.5.0.json',
                  'docs/NATIVE-VERIFICATION-0.6.0.json','docs/NATIVE-VERIFICATION-0.7.0.json',
                  'docs/NATIVE-VERIFICATION-0.8.0.json',
                  'docs/NATIVE-VERIFICATION-0.8.1.json',
                  'docs/NATIVE-VERIFICATION-0.9.0.json',
                  'docs/NATIVE-VERIFICATION-1.0.0.json'}
DATA_FILES={'data/projects.json','data/project-knowledge.json','data/generation-providers.json','data/native-content.json'}
OWNED_ASSETS={'mod/Textures/halveth/scarlet-love-banner.png',
              'mod/Textures/halveth/love-astrolabe-0.7.png',
              'installer/love-astrolabe-icon-0.8.png',
              'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.tga',
              'assets/ScarletLoveBanner/Textures/Tx_de_tapestry_02.dds'}
# The original shader is source text. Keep its path exact: a blanket .omwfx
# allowance could accidentally package third-party shader downloads.
OWNED_SHADER='mod/shaders/halveth_atmosphere.omwfx'
EXCLUDED_PARTS={'.local','.git','__pycache__','.pytest_cache','.venv','venv','obj','bin',
                'node_modules','runtime','profiles','saves','screenshots','captures',
                'downloads','backups','work','logs','dist'}
EXCLUDED_FILES={'data/entities.json','data/entity-sources.json','data/graphics-install.json',
                'mod/bridge/inbox.json','mod/bridge/companion-status.json','source-manifest.json','local-config.json'}
SOURCE_SUFFIXES={
    'docs':{'.md'},
    'mod':{'.lua','.omwscripts','.omwfont'},
    'native':{'.cs'},
    'scripts':{'.py','.ps1','.cmd','.sh','.mjs'},
    'installer':set(),  # Exact source files above; never package generated obj/bin code.
    'tests':{'.py'},
    'web':{'.html','.css','.js'},
}
STARTER=[
    {'id':'halveth','name':'HALVETH','kind':'Projektfigur','description':'Entwirft neue Möglichkeiten für deine Spielwelt.','source':'Genesis starter'},
    {'id':'lucinet','name':'LUCINET','kind':'Projektfigur','description':'Verbindet Spielwissen, Orte und die Erinnerung deiner Reise.','source':'Genesis starter'},
    {'id':'rachel','name':'RACHEL','kind':'Projektfigur','description':'Begleitet deine Werkstatt mit Neu, In Arbeit und Erledigt.','source':'Genesis starter'}]


def is_link(path):
    return path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction())


def source_files():
    """Yield source and exact approved assets, pruning runtime trees first."""
    for current,directories,names in os.walk(ROOT,topdown=True,followlinks=False):
        current=Path(current)
        directories[:]=[name for name in directories
                       if name.casefold() not in EXCLUDED_PARTS and not is_link(current/name)
                       and (current!=ROOT or name in SOURCE_DIRECTORIES)]
        for name in names:
            path=current/name
            relative=path.relative_to(ROOT)
            rel=relative.as_posix()
            if is_link(path) or rel.casefold() in EXCLUDED_FILES:
                continue
            if any(part.casefold() in EXCLUDED_PARTS for part in relative.parts):
                continue
            if rel in OWNED_ASSETS or rel==OWNED_SHADER or rel in EXACT_TEXT_FILES:
                allowed=True
            elif len(relative.parts)==1:
                allowed=rel in ROOT_FILES
            elif relative.parts[0]=='data':
                allowed=rel in DATA_FILES
            else:
                allowed=path.suffix.casefold() in SOURCE_SUFFIXES.get(relative.parts[0],set())
            if allowed:
                yield rel,path


def collect_files():
    files={}
    for name,path in source_files():
        files[name]=path.read_bytes()
    files['data/entities.json']=json.dumps(STARTER,ensure_ascii=False,indent=2).encode('utf-8')
    files['mod/bridge/inbox.json']=b'{"sequence":0,"sessionId":""}\n'
    files['RELEASE-NOTE.txt']=(
        f'Genesis {VERSION}: public-source package; own code/docs MIT, exact owned artwork files CC0-1.0 to the extent of owned rights.\n'
        'This archive contains 3 original starter cards, built-in JARVIS, 8 original paraphrased cards with public source references, and an original generated Scarlet Love banner with its approved texture derivatives.\n'
        'Version 0.4 adds six original native books with fifteen authored passages, three native spells, an F7 knowledge journal, a bounded alchemy study bonus, and a direct Morrowind start with a hidden optional companion.\n'
        'Version 0.5 adds the native character/inventory/magic/encounter workbench, mouse access from normal menus, current-state character dialogue direction, antialiased bundled-font configuration and read-only plugin record survey tooling.\n'
        'Version 0.6 adds original native exploration paths, an alchemy recipe planner, and an original adjustable atmosphere shader inside OpenMW.\n'
        'Version 0.7 adds the native Sammelatlas, a stronger Morgenrot light profile and the original LOVE astrolabe artwork in the in-game companion view.\n'
        'Version 0.8 adds a native observed-NPC worldlife journal, an optional owned wanderer, actor scheduling for the owned character, and live outdoor light response. The installer sources build a one-file Windows setup with an own LOVE icon; no installer EXE is part of this source ZIP.\n'
        'Version 0.8.1 opens a nearby observed NPC directly from the native Worldlife chronicle and lays out its controls responsively.\n'
        'Version 0.9 adds a native first-person, third-person and free-look camera panel, bounded viewport observations for the player dialogue context, and direct rotation and zoom controls.\n'
        'Version 1.0 binds observed NPC history to the actual conversation target and makes the owned wanderer removable after changing cells, with native save/reload verification. It is a scoped OpenMW extension for an existing licensed Morrowind installation.\n'
        'The generation-provider manifest and production briefs are included; no copied source registry, Bethesda assets, extracted game text, saves, logs or model weights are included.\n'
        'Only the 5 exact owned art asset paths and the one original shader source path are allowed. No New World code, textures, models or game data is included. Other downloaded textures, shaders, meshes, binary game plugins, local graphics manifests, profiles, runtime state and document screenshots are excluded. See ASSET-PROVENANCE.json when present and docs/GENERATION-PIPELINE.md.\n'
        'Read README.md, LICENSE, ASSET-LICENSE.md and THIRD-PARTY-NOTICES.md. Python 3.11+, separately configured OpenMW 0.51 and optional local Ollama model required.\n'
        'A source archive is not a standalone installer, hosted CI pass or confirmation that publication succeeded.\n'
    ).encode('utf-8')
    return files


def validate_files(files):
    """Validate this public snapshot without reading a private install manifest."""
    required={'LICENSE','ASSET-LICENSE.md','LICENSES/CC0-1.0.txt','ASSET-PROVENANCE.json',
              'README.md','PUBLIC-STATUS.json','THIRD-PARTY-NOTICES.md','data/entities.json',
              'mod/bridge/inbox.json','data/native-content.json','native/GenesisEntry.cs',
              'scripts/build_native_entry.py','scripts/build_native_content.py',
              'mod/scripts/halveth/content_catalog.lua','mod/scripts/halveth/content.lua',
              'mod/scripts/halveth/knowledge.lua','mod/scripts/halveth/universe.lua',
              'mod/scripts/halveth/inspect.lua','mod/scripts/halveth/paths.lua',
              'mod/scripts/halveth/visuals.lua','mod/scripts/halveth/perspective.lua',
              OWNED_SHADER,'character_profile.py',
              'mod/scripts/halveth/fieldcraft.lua',
        'mod/scripts/halveth/worldlife.lua','mod/scripts/halveth/actor_life.lua',
        'mod/scripts/halveth/actor_life_global.lua','tests/integration_actor_life.py',
        'tests/integration_perspective.py',
        'tests/integration_installer.py',
              'installer/GenesisSetup.csproj','installer/Program.cs','installer/build_installer.py','installer/README.md',
              'installer/openmw-0.51.0-runtime-files.txt',
              'mod/Fonts/MysticCards.omwfont',*OWNED_ASSETS}
    required.add('docs/NATIVE-VERIFICATION-0.4.0.json')
    required.add('docs/NATIVE-VERIFICATION-0.5.0.json')
    required.add('docs/NATIVE-VERIFICATION-0.6.0.json')
    required.add('docs/NATIVE-VERIFICATION-0.7.0.json')
    required.add('docs/NATIVE-VERIFICATION-0.8.0.json')
    required.add('docs/NATIVE-VERIFICATION-0.8.1.json')
    required.add('docs/NATIVE-VERIFICATION-0.9.0.json')
    required.add('docs/NATIVE-VERIFICATION-1.0.0.json')
    missing=required-files.keys()
    if missing:
        raise ValueError('Missing public release files: '+', '.join(sorted(missing)))
    if b'MIT License' not in files['LICENSE'] or b'CC0 1.0 Universal' not in files['LICENSES/CC0-1.0.txt']:
        raise ValueError('Expected MIT and complete CC0 license texts.')
    if json.loads(files['data/entities.json'])!=STARTER:
        raise ValueError('Public register must contain only the original starter cards.')
    if json.loads(files['mod/bridge/inbox.json'])!={'sequence':0,'sessionId':''}:
        raise ValueError('Public mailbox must be reset.')
    if 'mod/bridge/companion-status.json' in files:
        raise ValueError('Runtime companion status must not be published.')
    provenance=json.loads(files['ASSET-PROVENANCE.json'])
    records={record['path']:record for record in provenance['files']}
    if set(records)!=OWNED_ASSETS:
        raise ValueError('Asset provenance must bind exactly the five owned art paths.')
    for name in OWNED_ASSETS:
        raw=files[name]
        if len(raw)!=records[name]['bytes'] or hashlib.sha256(raw).hexdigest()!=records[name]['sha256']:
            raise ValueError('Asset provenance mismatch: '+name)
    # Text inspection is intentionally narrow and cannot replace human review.
    local_path=re.compile(r'[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+[\\/]',re.I)
    private_key=re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    for name,raw in files.items():
        if name in OWNED_ASSETS:
            continue
        text=raw.decode('utf-8-sig')
        if local_path.search(text) or private_key.search(text):
            raise ValueError('Machine-specific path or private-key material in public text: '+name)
    return {'files':len(files),'bytes':sum(map(len,files.values())),'assetCount':len(OWNED_ASSETS),
            'validation':'Required files, clean starters/mailbox, exact asset provenance and bounded text inspection passed.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate the public distributable snapshot without writing an archive.')
    args=parser.parse_args()
    files=collect_files()
    validation=validate_files(files)
    if args.check:
        print(json.dumps(validation,indent=2))
        return
    manifest={'version':VERSION,'publication':'PUBLIC_SOURCE_PACKAGE',
        'licenses':{'codeAndDocumentation':'MIT','originalBanner':'CC0-1.0'},
        'files':[{'path':name,'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in sorted(files.items())]}
    files['SOURCE-MANIFEST.json']=json.dumps(manifest,indent=2).encode('utf-8')
    DEST.parent.mkdir(parents=True,exist_ok=True)
    temporary=DEST.with_name(DEST.name+'.new')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,value in sorted(files.items()):
            archive.writestr('HALVETH-Morrowind-Genesis/'+name,value)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise OSError('Source archive CRC verification failed.')
        for record in manifest['files']:
            if hashlib.sha256(archive.read('HALVETH-Morrowind-Genesis/'+record['path'])).hexdigest()!=record['sha256']:
                raise OSError('Source archive hash verification failed: '+record['path'])
    # Output is confined to ignored dist/. Earlier local candidate archives remain untouched.
    temporary.replace(DEST)
    receipt={'file':DEST.name,'bytes':DEST.stat().st_size,'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),'files':len(files)}
    DEST.with_suffix('.sha256').write_text(receipt['sha256']+'  '+DEST.name+'\n',encoding='ascii')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
