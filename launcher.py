"""Small native launcher for the separate Genesis world and its local companion."""
from pathlib import Path
import argparse
import configparser
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.local'
URL='http://127.0.0.1:18765'
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
        process=background([str(python),str(ROOT/'server.py'),'--log',str(log),
            '--model',LAUNCH_OPTIONS.get('model','hermes3:8b')],'companion.log')
        (STATE/'companion.pid').write_text(str(process.pid),encoding='ascii')
        for _ in range(40):
            if get_status():
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Der Begleiter konnte nicht starten. Details in .local/companion.log.')
    return receipt


def start_game(profile):
    receipt=companion(profile)
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
        process=subprocess.Popen(receipt['command'],cwd=receipt['cwd'],stdout=log,stderr=subprocess.STDOUT)
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


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--companion-only',action='store_true')
    parser.add_argument('--profile',choices=['original','beauty','cinematic'],default='beauty')
    parser.add_argument('--install-root',type=Path,help='Installation root with engine/ and profiles/.')
    parser.add_argument('--source-profile',help='Existing source profile directory name, usually max.')
    parser.add_argument('--model',help='Already installed local Ollama model.')
    parser.add_argument('--copy-saves',action='store_true',help='Copy source saves once, without overwriting; opt-in for this run.')
    parser.add_argument('--save-config',action='store_true',help='Remember installation/profile/model in ignored local-config.json.')
    args=parser.parse_args()
    try:
        configure(args)
    except (OSError,ValueError) as exc:
        parser.error(str(exc))
    if args.companion_only:
        companion(args.profile)
        webbrowser.open(URL)
        return
    import tkinter as tk
    from tkinter import messagebox
    window=tk.Tk()
    window.title('HALVETH · Morrowind Genesis')
    window.geometry('920x860')
    window.minsize(840,820)
    bg='#111716'; panel='#1a211c'; edge='#384332'; ink='#e8e1ce'; muted='#a4ae98'; scarlet='#a55c5b'; gold='#c6b08a'
    window.configure(bg=bg)
    frame=tk.Frame(window,bg=bg,padx=32,pady=22)
    frame.pack(fill='both',expand=True)
    def label(parent,text,size=10,color=ink,serif=False,background=None,**options):
        item=tk.Label(parent,text=text,bg=background or bg,fg=color,
            font=('Georgia' if serif else 'Segoe UI',size),justify='left',anchor='w',**options)
        return item
    top=tk.Frame(frame,bg=bg); top.pack(fill='x')
    label(top,'✧  HALVETH  /  MORROWIND GENESIS',10,gold).pack(side='left')
    label(top,'SCARLET EDITION · LOKAL',8,muted).pack(side='right')
    tk.Frame(frame,bg=edge,height=1).pack(fill='x',pady=(14,18))
    label(frame,'Zurück in eine schönere Welt.',28,ink,serif=True).pack(fill='x')
    label(frame,'Wähle das Licht für deine nächste Geschichte.',11,'#cf9188').pack(fill='x',pady=(5,17))
    selected=tk.StringVar(value=args.profile)
    selector=tk.Frame(frame,bg=bg); selector.pack(fill='x')
    profile_cards={}
    for index,(key,(name,subtitle,description)) in enumerate(PROFILE_COPY.items()):
        selector.columnconfigure(index,weight=1,uniform='profile')
        card=tk.Frame(selector,bg=panel,highlightbackground=edge,highlightthickness=1,padx=15,pady=13)
        card.grid(row=0,column=index,sticky='nsew',padx=(0,10) if index<2 else 0)
        radio=tk.Radiobutton(card,text=name,variable=selected,value=key,bg=panel,fg=ink,
            activebackground=panel,activeforeground=gold,selectcolor='#3b382a',font=('Georgia',19),
            cursor='hand2',anchor='w',highlightthickness=0)
        radio.pack(fill='x')
        label(card,subtitle,9,gold,background=panel).pack(fill='x',pady=(4,7))
        label(card,description,9,muted,background=panel,wraplength=225,height=3).pack(fill='x')
        profile_cards[key]=card
    label(frame,'AKTUELLE PROFILDATEI',8,gold).pack(fill='x',pady=(20,7))
    overview=tk.Frame(frame,bg=panel,highlightbackground=edge,highlightthickness=1,padx=16,pady=11)
    overview.pack(fill='x')
    overview_status=tk.StringVar()
    label(overview,'',9,muted,background=panel,textvariable=overview_status).pack(fill='x',pady=(0,7))
    metrics=tk.Frame(overview,bg=panel); metrics.pack(fill='x')
    metric_vars={}
    for index,title in enumerate(('Auflösung','Schattenauflösung','Wasserauflösung','Texturfilter','Sichtweite (Spielwerte)','Nachbearbeitung')):
        col=index%3; row=index//3; metrics.columnconfigure(col,weight=1,uniform='metric')
        slot=tk.Frame(metrics,bg=panel);slot.grid(row=row,column=col,sticky='ew',pady=5)
        label(slot,title,8,muted,background=panel).pack(fill='x')
        metric_vars[title]=tk.StringVar(value='—')
        label(slot,'',12,ink,background=panel,textvariable=metric_vars[title]).pack(fill='x')
    installed=tk.StringVar()
    label(frame,'INHALTE & CHARAKTERE',8,gold).pack(fill='x',pady=(16,5))
    label(frame,'',9,muted,textvariable=installed,wraplength=830,height=3).pack(fill='x')
    message=tk.StringVar(value='F8 öffnet JARVIS im Spiel. Wähle oben ein Profil und starte deine Reise.')
    buttons=[]
    def refresh_overview(*_):
        profile=selected.get(); info=describe_profile(profile)
        for key,card in profile_cards.items():
            card.configure(highlightbackground=scarlet if key==profile else edge,highlightthickness=2 if key==profile else 1)
        state='Vorbereitet · Werte aus deiner Profildatei' if info['prepared'] else 'Wird beim ersten Start als eigenes Profil angelegt'
        if info['settingsError']:
            state=info['settingsError']
        overview_status.set(state)
        for title,value in info['settings'].items():
            metric_vars[title].set(value)
        packages=info['packages']
        if packages:
            parts=[]
            for item in packages[:2]:
                status='Dateien vorhanden' if item['filesPresent'] is True else 'Dateien fehlen' if item['filesPresent'] is False else item['status']
                parts.append(f"{item['name']}: {status}")
            if len(packages)>2:
                parts.append(f"+ {len(packages)-2} weitere im Konstellarium")
            line='  ·  '.join(parts)
        else:
            line='Zusätzliche Grafikpakete: noch kein Installationsbeleg vorhanden.'
        if info['characterStyle']:
            line+='\n'+info['characterStyle']
        installed.set(line)
    selected.trace_add('write',refresh_overview)
    def run(operation,success):
        profile=selected.get()
        for button in buttons:
            button.configure(state='disabled')
        for child in selector.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget,tk.Radiobutton):widget.configure(state='disabled')
        message.set('Deine Welt wird vorbereitet …')
        def worker():
            try:
                result=operation(profile)
                response=result if isinstance(result,str) else success
                window.after(0,lambda:message.set(response))
            except Exception as exc:
                error=str(exc)
                window.after(0,lambda:messagebox.showerror('HALVETH',error,parent=window))
                window.after(0,lambda:message.set('Der Vorgang konnte nicht abgeschlossen werden.'))
            finally:
                def finish():
                    for button in buttons:button.configure(state='normal')
                    for child in selector.winfo_children():
                        for widget in child.winfo_children():
                            if isinstance(widget,tk.Radiobutton):widget.configure(state='normal')
                    refresh_overview()
                try:window.after(0,finish)
                except RuntimeError:pass
        threading.Thread(target=worker,daemon=True).start()
    def open_companion(profile):
        companion(profile)
        webbrowser.open(URL)
    controls=tk.Frame(frame,bg=bg);controls.pack(fill='x',pady=(10,9))
    for title,operation,success in [('Grafikvorlage anwenden',apply_graphics,''),('Profilübersicht aktualisieren',None,'')]:
        button=tk.Button(controls,text=title,command=(lambda op=operation,done=success:run(op,done)) if operation else refresh_overview,
            bg='#252f24',fg='#c8cbb5',activebackground='#394032',activeforeground=ink,
            relief='flat',font=('Segoe UI',9),padx=14,pady=8,cursor='hand2')
        button.pack(side='left',padx=(0,8));buttons.append(button)
    label(frame,'Grafikvorlage anwenden aktualisiert die Grafikwerte dieses Genesis-Profils mit Sicherung.\nPersönliche Spiel-, Ton- und Eingabeeinstellungen bleiben erhalten.',8,muted).pack(fill='x',pady=(0,12))
    primary=tk.Frame(frame,bg=bg);primary.pack(fill='x')
    for title,operation,success,colour in [
        ('✦  GENESIS SPIELEN',start_game,'OpenMW wurde gestartet. Lade deinen Spielstand und betrete Vvardenfell.',scarlet),
        ('KONSTELLARIUM ÖFFNEN',open_companion,'Das Konstellarium wurde im Browser geöffnet.','#303b2c')]:
        button=tk.Button(primary,text=title,command=lambda op=operation,done=success:run(op,done),bg=colour,fg='#fff0dd',
            activebackground='#bb756d',activeforeground='white',relief='flat',font=('Segoe UI',11,'bold'),pady=13,padx=18,cursor='hand2')
        button.pack(side='left',fill='x',expand=True,padx=(0,10) if operation is start_game else 0)
        buttons.append(button)
    label(frame,'',9,muted,textvariable=message,wraplength=830).pack(fill='x',pady=(12,0))
    refresh_overview()
    window.mainloop()


if __name__=='__main__':
    main()
