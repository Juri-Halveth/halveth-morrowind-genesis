"""Read local graphics receipts and actual profile settings for the companion UI."""
import configparser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def graphics_status():
    try:
        installed = json.loads((ROOT/'.local/graphics/install.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        installed = {}
    profiles=[]
    descriptions={
        'original':('Original','Dein bisheriges max-Profil, mit separaten Spielständen.'),
        'beauty':('Scarlet Beauty','Atmosphäre, klare Oberflächen und weicheres Licht für die Reise.'),
        'cinematic':('Cinematic','Mehr Landschaftsweite und höhere Wasserauflösung für ruhige Ansichten.')}
    for key,(name,description) in descriptions.items():
        path=ROOT/'.local/profiles'/key
        config=configparser.ConfigParser(interpolation=None)
        try:
            config.read(path/'settings.cfg',encoding='utf-8-sig')
        except configparser.Error:
            config=configparser.ConfigParser()
        def value(section,setting):
            return config.get(section,setting,fallback='—')
        settings={
            'Auflösung':value('Video','resolution x')+' × '+value('Video','resolution y'),
            'Schattenauflösung':value('Shadows','shadow map resolution'),
            'Wasserauflösung':value('Water','rtt size'),
            'Anisotropie':value('General','anisotropy')+'×',
            'Sichtweite (Engine-Einheiten)':value('Camera','viewing distance'),
            'Effekte':value('Post Processing','chain')}
        profiles.append({'id':key,'name':name,'description':description,'settings':settings,
                         'prepared':(path/'openmw.cfg').exists(),'status':'Vorbereitet' if (path/'openmw.cfg').exists() else 'Noch nicht vorbereitet',
                         'features':[f"{value('Shadows','shadow map resolution')}er Schatten",f"{value('Water','rtt size')}er Wasser"]})
    packages=[{key:p.get(key) for key in ('name','version','status','bytes','license','source','fileCount')} for p in installed.get('packages',[])]
    try:
        checks=json.loads((ROOT/'.local/graphics/verification.json').read_text(encoding='utf-8'))
    except (OSError,ValueError): checks={}
    for profile in profiles:
        if checks.get(profile['id'],{}).get('passed'):
            profile['status']='Im Spiel geprüft'
    return {'graphicsProfiles':profiles,'graphics':{
        'activeProfile':None,'installedPackages':packages,
        'installedBytes':sum(p.get('bytes') or 0 for p in packages),
        'characterStyle':installed.get('characterStyle','Originale Charaktergrafik'),
        'verification':checks}}
