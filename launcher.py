"""Launch TES III Morrowind through OpenMW, with the in-game HALVETH mod."""
from pathlib import Path
import argparse
import configparser
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.local'
URL='http://127.0.0.1:18765'
BRIDGE_STATUS=ROOT/'mod'/'bridge'/'companion-status.json'
LAUNCH_OPTIONS={}


def configure(args):
    """Load only explicit per-checkout installation preferences, never game data."""
    from scripts.prepare_profile import default_install
    config_path=ROOT/'local-config.json'
    saved={}
    if config_path.exists():
        saved=json.loads(config_path.read_text(encoding='utf-8'))
        if not isinstance(saved,dict) or set(saved)-{'install_root','source_profile','model'}:
            raise ValueError('Invalid local-config.json; expected installation, profile and model preferences.')
        if any(not isinstance(value,str) or not value.strip() for value in saved.values()):
            raise ValueError('Local configuration values must be nonempty strings.')
    options={
        'install_root':str(args.install_root or saved.get('install_root') or default_install()),
        'source_profile':args.source_profile or saved.get('source_profile','max'),
        'model':args.model or saved.get('model','hermes3:8b'),
        'copy_saves':bool(args.copy_saves),
    }
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',options['source_profile']):
        raise ValueError('Source profile must contain 1-48 ASCII letters, digits, underscores or hyphens.')
    if args.save_config:
        persisted={key:options[key] for key in ('install_root','source_profile','model')}
        temporary=config_path.with_suffix('.json.new')
        temporary.write_text(json.dumps(persisted,indent=2)+'\n',encoding='utf-8')
        temporary.replace(config_path)
    LAUNCH_OPTIONS.clear()
    LAUNCH_OPTIONS.update(options)
    return options


def get_status():
    try:
        with urllib.request.urlopen(URL+'/api/status',timeout=3) as response:
            return json.load(response)
    except (OSError,ValueError):
        return None


def background(command,log):
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/log).open('a',encoding='utf-8') as output:
        return subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def prepare(profile,copy_saves=None,reset_settings=False):
    from scripts.prepare_profile import prepare,DEFAULT_INSTALL
    args=argparse.Namespace(install_root=Path(LAUNCH_OPTIONS.get('install_root',DEFAULT_INSTALL)),state_dir=STATE,
        source_profile=LAUNCH_OPTIONS.get('source_profile','max'),profile=profile,smoke=False,
        copy_saves=LAUNCH_OPTIONS.get('copy_saves',False) if copy_saves is None else copy_saves,
        reset_settings=reset_settings)
    return prepare(args)


def companion(profile='beauty'):
    receipt=prepare(profile)
    from server import Store
    store=Store(STATE/'universe.sqlite3')
    if store.counts()['lore']==0:
        from scripts.import_lore import index,from_config
        index(from_config(Path(receipt['profile_dir'])/'openmw.cfg'),STATE)
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2):
            pass
    except OSError:
        ollama=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe'
        if ollama.exists():
            background([str(ollama),'serve'],'ollama.log')
    existing=get_status()
    # A single stable log path serves every selected Genesis graphics profile.
    log=STATE/'game.stdout.log'
    if existing is None:
        python=Path(sys.executable)
        process=background([str(python),str(ROOT/'server.py'),'--log',str(log),'--model',LAUNCH_OPTIONS.get('model','hermes3:8b')],'companion.log')
        (STATE/'companion.pid').write_text(str(process.pid),encoding='ascii')
        for _ in range(40):
            if get_status():
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Der Begleiter konnte nicht starten. Details in .local/companion.log.')
    return receipt


def start_game(profile):
    try:
        receipt=companion(profile)
        availability={'status':'available','profile':profile}
    except Exception:
        # The local AI/service is optional. A valid TES III profile can play
        # offline even if the service or its local model is unavailable.
        details=traceback.format_exc()
        receipt=prepare(profile)
        availability={'status':'offline','profile':profile,
            'message':'Morrowind startet offline. Der lokale Begleiter ist momentan nicht erreichbar.'}
        STATE.mkdir(parents=True,exist_ok=True)
        with (STATE/'companion-start-errors.log').open('a',encoding='utf-8') as output:
            output.write(details+'\n')
    (STATE/'companion-availability.json').write_text(json.dumps(availability,ensure_ascii=False)+'\n',encoding='utf-8')
    # This small VFS-visible record supplies the nonblocking in-game status.
    # Diagnostics and local file paths remain in .local, outside game content.
    BRIDGE_STATUS.parent.mkdir(parents=True,exist_ok=True)
    pending=BRIDGE_STATUS.with_name(BRIDGE_STATUS.name+'.new')
    pending.write_text(json.dumps({'status':availability['status']})+'\n',encoding='utf-8')
    pending.replace(BRIDGE_STATUS)
    pid_path=STATE/'game.pid'
    if os.name=='nt' and pid_path.exists():
        pid=pid_path.read_text(encoding='ascii').strip()
        if pid.isdigit():
            # tasklist uses the Windows OEM code page, which can differ from
            # Python's text decoder. The image name and PID are ASCII; keep bytes.
            result=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode!=0:
                raise RuntimeError('Die Windows-Prozessabfrage ist fehlgeschlagen. Das Spiel wurde nicht erneut gestartet.')
            if not isinstance(result.stdout,bytes) or not result.stdout.strip():
                raise RuntimeError('Die Windows-Prozessabfrage hat keine verwertbare Ausgabe geliefert. Das Spiel wurde nicht erneut gestartet.')
            expected=[b'"openmw.exe"',f'"{pid}"'.encode('ascii')]
            if any(line.strip().lower().split(b',',2)[:2]==expected for line in result.stdout.splitlines()):
                raise RuntimeError('Dein Genesis-Spiel läuft bereits. Wechsle in das vorhandene Fenster.')
    with (STATE/'game.stdout.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(receipt['command'],cwd=receipt['cwd'],stdout=log,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    pid_path.write_text(str(process.pid),encoding='ascii')
    (STATE/'active-profile.json').write_text(json.dumps({'profile':profile,'pid':process.pid}),encoding='utf-8')
    return process.pid


PROFILE_COPY = {
    'original': ('Original', 'Die vertraute Welt', 'Das bisherige Erscheinungsbild als eigener Rückkehrpunkt.'),
    'beauty': ('Scarlet Beauty', 'Licht. Wasser. Atmosphäre.', 'Das ausgewogene Grafikprofil für deine Reise durch Vvardenfell.'),
    'cinematic': ('Cinematic', 'Die große Aussicht', 'Das aufwendigere Profil für Panoramen und deinen eigenen Bildvergleich.'),
}


def describe_profile(profile):
    """Read only deliberately public graphics fields; exclude paths and save data."""
    if profile not in PROFILE_COPY:
        raise ValueError('Unbekanntes Genesis-Profil.')
    profile_dir = STATE/'profiles'/profile
    parser = configparser.ConfigParser(interpolation=None)
    settings_file = profile_dir/'settings.cfg'
    settings_error = None
    try:
        parser.read(settings_file,encoding='utf-8-sig')
    except (OSError,configparser.Error):
        settings_error = 'Die vorhandenen Einstellungen konnten nicht gelesen werden.'
    def value(section,key):
        return parser.get(section,key,fallback='—')
    values = {
        'Auflösung': f"{value('Video','resolution x')} × {value('Video','resolution y')}",
        'Schattenauflösung': value('Shadows','shadow map resolution'),
        'Wasserauflösung': value('Water','rtt size'),
        'Texturfilter': value('General','anisotropy')+'× anisotrop' if parser.has_option('General','anisotropy') else '—',
        'Sichtweite (Spielwerte)': value('Camera','viewing distance'),
        'Nachbearbeitung': {'true':'Aktiviert','false':'Deaktiviert'}.get(value('Post Processing','enabled'),value('Post Processing','enabled')),
    }
    packages = []
    character_style = ''
    manifest_present = False
    try:
        manifest = json.loads((STATE/'graphics'/'install.json').read_text(encoding='utf-8-sig'))
        if not isinstance(manifest,dict):
            raise ValueError('Invalid manifest')
        manifest_present = True
        character_style = str(manifest.get('characterStyle',''))
        for item in manifest.get('packages',[]):
            if not isinstance(item,dict):
                continue
            directory = item.get('dataDirectory')
            exists = None
            if isinstance(directory,str) and directory:
                target = Path(directory)
                if not target.is_absolute():
                    target = ROOT/target
                exists = target.is_dir()
            packages.append({'name':str(item.get('name','Inhaltspaket')),
                'version':str(item.get('version','')),'status':str(item.get('status','nicht angegeben')),
                'filesPresent':exists,'bytes':item.get('bytes')})
    except (OSError,ValueError,TypeError):
        pass
    last_profile = None
    try:
        last_profile = json.loads((STATE/'active-profile.json').read_text(encoding='utf-8')).get('profile')
    except (OSError,ValueError,AttributeError):
        pass
    return {'profile':profile,'prepared':settings_file.is_file(),'settings':values,
        'settingsError':settings_error,'packages':packages,'manifestPresent':manifest_present,
        'characterStyle':character_style,'lastStartedProfile':last_profile}


def apply_graphics(profile):
    """Apply the explicit preset using the profile builder's backup and preservation path."""
    receipt = prepare(profile,reset_settings=True)
    graphics = receipt.get('graphics',{})
    if graphics.get('settings_backup'):
        return 'Grafikvorlage angewendet. Die vorherigen Einstellungen wurden gesichert.'
    return 'Grafikprofil vorbereitet. Die aktuellen Werte stehen in der Profilübersicht.'


def main(argv=None):
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--play',action='store_true',
        help='Start Morrowind and its hidden local companion directly, without a launcher window or browser.')
    mode.add_argument('--companion-only',action='store_true')
    parser.add_argument('--profile',choices=['original','beauty','cinematic'],default='beauty')
    parser.add_argument('--install-root',type=Path)
    parser.add_argument('--source-profile')
    parser.add_argument('--model')
    parser.add_argument('--copy-saves',action='store_true')
    parser.add_argument('--save-config',action='store_true')
    args=parser.parse_args(argv)
    configure(args)
    if args.companion_only:
        companion(args.profile)
        return 0
    start_game(args.profile)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
