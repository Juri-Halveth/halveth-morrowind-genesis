"""MIT. Exact selected add-on files, fixed parent bytes and source/native bindings."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,zipfile

ROOT=Path(__file__).resolve().parents[1]
PARENT_DIGEST='d980cf4a36c6a696bb26577eb7381a4cc133a18a005fab9ae84128c7b75b3698'
PARENT_COMMIT='166a81e8d46db310af7d2a80043502c86aea967b'
COMMON={'.gitattributes','LICENSE','README.md','PARENT_BINDINGS.json','OWN_ASSET_BINDINGS.json',
        'scripts/package-refinements.py','tests/test_publication.py'}
UNITS={
 'crown':{'crown-0.1.1/'+n for n in ('LICENSE','README.md','THIRD_PARTY_NOTICES.md','cfg-additive.txt',
  'SOURCE_BINDING.json','build-refinement.py','check-refinement.py','bark-closure/CC0-1.0.txt',
  'bark-closure/SOURCE_BINDING.json','bark-closure/THIRD_PARTY_NOTICES.md',
  'mod/Veyra-Crown-Refinement-011.esp','mod/Meshes/veyra/veyra_swamp_crown_refined_011.dae',
  'mod/Textures/veyra/crown_leaf_refined_011.dds')}|{'evidence/CROWN_NATIVE.json'},
 'wildlife':{'wildlife-0.1.1/'+n for n in ('LICENSE','README.md','cfg-additive.txt','SOURCE_BINDING.json',
  'check-control.lua','mod/Veyra-Wildlife.omwscripts','mod/scripts/veyra_wildlife/config.lua',
  'mod/scripts/veyra_wildlife/global.lua','mod/scripts/veyra_wildlife/actor.lua','mod/scripts/veyra_wildlife/player.lua',
  'mod/Meshes/veyra/creature/frontier_stag.dae','mod/Meshes/veyra/creature/frontier_stag.txt')}|{'evidence/WILDLIFE_NATIVE.json'},
}
LOCAL_PATH=re.compile(r'(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|/(?:Users|home|mnt|private|tmp)/',re.I)
PRIVATE_KEY=re.compile(r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----')
TOKEN=re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})\b')
# Literal fixed source pins are appended by the preparation step before review.
PRODUCTION={'crown': {'crown-0.1.1/mod/Veyra-Crown-Refinement-011.esp': '4e7426fd965dd4054b133acc18d3c00dc774937ea89feab9f46e02c193e4ff0f', 'crown-0.1.1/mod/Meshes/veyra/veyra_swamp_crown_refined_011.dae': '3ce4e188aa790e2fce1b976b3e594ba3be5ef761ec882e03f7371e39341c7325', 'crown-0.1.1/mod/Textures/veyra/crown_leaf_refined_011.dds': '49683c4a6751b893707f81d3412ed3897dbcb5512fb2e37621b1730a0f8f0934'}, 'wildlife': {'wildlife-0.1.1/mod/Meshes/veyra/creature/frontier_stag.dae': '04be0c945b715fd39b5492f23fe72c7088689e6271812cd7b2099f2f86eb4bec', 'wildlife-0.1.1/mod/Meshes/veyra/creature/frontier_stag.txt': '2b9c43f3a43f05152bd530159ca74882dd64fe133d20f2967bfbde253c135742', 'wildlife-0.1.1/mod/scripts/veyra_wildlife/actor.lua': 'eace1b82dbbc06d0e74f9b0282741d53796f387caf252ff28a98c6c62a128206', 'wildlife-0.1.1/mod/scripts/veyra_wildlife/config.lua': '103dc4c3c20b0bb0098eb564ca1ef596cb078e3debe5a3d5f5ef369aec1167e4', 'wildlife-0.1.1/mod/scripts/veyra_wildlife/global.lua': 'f151c64e6cf53609608f64f344b0e8901946f191ba19db5a32f7b34abcd3a0ed', 'wildlife-0.1.1/mod/scripts/veyra_wildlife/player.lua': '94eca85f746deb31d9d14762a73b7451f36586fd02a357cabcb4fb8c54ba37f6', 'wildlife-0.1.1/mod/Veyra-Wildlife.omwscripts': 'dbbda99e319ea9dcceab3774d31e4286e42382412d5f004fd374db1acd16593a'}}
REVIEW_SOURCES={'crown': {'crown-0.1.1/build-refinement.py': 'c0b8eec002972627e1b062693556ab184a5d65a6b26f1e252d753f22fc67f991', 'crown-0.1.1/check-refinement.py': 'f1c4e821099ac151a40c84072c63a093e0eb7e0517587e1e31b4394e7fb5a6b9'}, 'wildlife': {'wildlife-0.1.1/check-control.lua': 'c41a1b030aaadaf0a3d389880deef86ae5727bd82484f11a963659ffca03aa4e'}}
LICENSE_PINS={'LICENSE': '3a781e2eb64284791a6c887d8183327c2492d8dd2de112bb6de7fc47b0e6303b', 'crown-0.1.1/LICENSE': '2f49b9dd3a853c844ca1f4639c3eaa3292b10a83c1fbe47ca7b46601656c87f2', 'wildlife-0.1.1/LICENSE': '7ada00677695a9472a22537717637e22a598aadff356a12476b194cd6e55b4ba', 'crown-0.1.1/THIRD_PARTY_NOTICES.md': '17a7ec25959f5d13303529ff045400718cde2b4dfa9098c8c5744657894f3ed8', 'crown-0.1.1/bark-closure/CC0-1.0.txt': '8bdc7b952ae0a12e08ccf9463a4750f7288f4d05bf7f2124cc5805ecaabdb01c', 'crown-0.1.1/bark-closure/SOURCE_BINDING.json': '3976f8feb0e302c3ea7e65c044185acfa5453888134c27e8eb77cad30463dd17', 'crown-0.1.1/bark-closure/THIRD_PARTY_NOTICES.md': 'd5e51bb54d0c59b0c7073cf44d3babcb0cc693e41824ed5eb0725fa49deed160'}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def linked(path):return path.is_symlink() or getattr(path,'is_junction',lambda:False)()

def relative(name):
    p=PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or '..' in p.parts or str(p)!=name:
        raise ValueError('Different relative filename contract')
    return p

def regular(root,name,limit):
    p=relative(name);root=Path(root)
    if linked(root) or any(linked(a) for a in root.parents):raise ValueError('Linked root rejected')
    target=root/str(p)
    if linked(target) or any(linked(root/Path(*p.parts[:i])) for i in range(1,len(p.parts))):
        raise ValueError('Linked publication/input file rejected')
    if not target.is_file() or target.stat().st_size>limit:raise ValueError('Required bounded regular file differs: '+name)
    return target.read_bytes()

def text(root,name):
    raw=regular(root,name,512*1024);value=raw.decode('utf8')
    if '\0' in value or LOCAL_PATH.search(value) or PRIVATE_KEY.search(value) or TOKEN.search(value):
        raise ValueError('Private path/key/token or binary text rejected: '+name)
    return raw

def units(value):
    selected=tuple(value)
    if not selected or len(set(selected))!=len(selected) or any(n not in UNITS for n in selected):
        raise ValueError('Explicit distinct known unit selection required')
    return tuple(n for n in UNITS if n in selected)

def check_parent(root,record):
    rows=record.get('parentFiles',[])
    canonical=json.dumps(rows,sort_keys=True,separators=(',',':')).encode('utf8')
    if len(rows)!=215 or sha(canonical)!=PARENT_DIGEST or record.get('parentFilesDigest')!=PARENT_DIGEST:
        raise ValueError('Fixed 215-file parent manifest differs')
    if record.get('parentCommit')!=PARENT_COMMIT or record.get('parentVersion')!='0.2.1':
        raise ValueError('Different reviewed parent commit/version')
    names=set()
    for row in rows:
        if row['path'] in names:raise ValueError('Repeated parent input')
        names.add(row['path']);raw=regular(root,row['path'],16*1024*1024)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('Bound parent bytes changed: '+row['path'])

def collect(selected=None,parent_root=None,inspect=False):
    parent_record=json.loads(text(ROOT,'PARENT_BINDINGS.json'))
    selected=units(parent_record['selectedUnits'] if selected is None else selected)
    check_parent(ROOT.parent/'leviath-workshop' if parent_root is None else parent_root,parent_record)
    universe=COMMON|set().union(*UNITS.values())
    for p in ROOT.rglob('*'):
        if linked(p):raise ValueError('Linked tree entry rejected')
        if p.is_file() and p.relative_to(ROOT).as_posix() not in universe:
            raise ValueError('Unknown publication file rejected: '+p.relative_to(ROOT).as_posix())
    allowed=COMMON|set().union(*(UNITS[n] for n in selected))
    assets=json.loads(text(ROOT,'OWN_ASSET_BINDINGS.json'))
    fixed_assets={p for table in PRODUCTION.values() for p in table if p.endswith(('.dae','.dds','.esp','.txt'))}
    if assets.get('originalGameAssetBytes')!=0 or assets.get('newCC0DerivativeBytes')!=0 or set(assets['assets'])!=fixed_assets:
        raise ValueError('Exact own asset/license scope differs')
    if parent_record.get('productionHashes')!={n+'-0.1.1':p for n,p in PRODUCTION.items()}:
        raise ValueError('Fixed production source map differs')
    files={}
    for name in sorted(allowed):
        files[name]=regular(ROOT,name,16*1024*1024) if name in fixed_assets else text(ROOT,name)
    for name,expected in LICENSE_PINS.items():
        if name in files and sha(files[name])!=expected:raise ValueError('Bound license/provenance bytes differ: '+name)
    for unit in selected:
        hashes=PRODUCTION[unit]
        for name,expected in {**hashes,**REVIEW_SOURCES[unit]}.items():
            if sha(files[name])!=expected:raise ValueError('Fixed reviewed source bytes changed: '+name)
        for name in set(hashes)&fixed_assets:
            row=assets['assets'][name];raw=files[name]
            if row.get('license')!='MIT' or row.get('originalGameAssetBytes')!=0 or row.get('sha256')!=sha(raw) or row.get('bytes')!=len(raw):
                raise ValueError('Own asset bytes/license binding differs')
            if name.endswith('.dds') and raw[:4]!=b'DDS ':raise ValueError('DDS header differs')
            if name.endswith('.esp') and raw[:4]!=b'TES3':raise ValueError('ESP header differs')
            if name.endswith(('.dae','.txt')):
                decoded=raw.decode('utf8')
                if LOCAL_PATH.search(decoded) or PRIVATE_KEY.search(decoded) or TOKEN.search(decoded):raise ValueError('Private asset text rejected')
                if name.endswith('.dae') and '<COLLADA' not in decoded:raise ValueError('COLLADA contract differs')
        binding=json.loads(files[unit+'-0.1.1/SOURCE_BINDING.json'])
        if binding.get('productionHashes')!=hashes or binding.get('reviewSourceHashes')!=REVIEW_SOURCES[unit]:
            raise ValueError('Selected production/review source closure differs')
        if unit=='crown' and (binding.get('sourceBuild')!='LOCAL_PARENT_ONLY' or binding.get('checkerRoute')!='PRIVATE_REBUILD_DEPENDENT'):
            raise ValueError('Public rebuild claim exceeds the source route')
        if unit=='wildlife' and (binding.get('defaultEnabled') is not False or binding.get('physicalKeyGate')!='NOT_OBSERVED'):
            raise ValueError('Wildlife input/default scope differs')
        receipt=json.loads(files['evidence/'+unit.upper()+'_NATIVE.json'])
        if receipt.get('moduleHashes')!=hashes:raise ValueError('Native observation binds different selected production')
        if inspect:continue
        if receipt.get('status')!='BOUNDED_NATIVE_PASS' or receipt.get('nativeInclusionGate')!='EXACT_SELECTED_UNIT_PRODUCTION_BOUND':
            raise ValueError('Selected unit native gate pending: '+unit)
        names=receipt.get('checks',[])
        observed=receipt.get('observationCounts',[])
        if not names or receipt.get('distinctAssertionNames')!=len(set(names)) or len(names)!=len(set(names)):
            raise ValueError('Native logged/distinct assertion names differ')
        if not observed or any(type(n) is not int or n<1 for n in observed) or sum(observed)!=receipt.get('loggedPasses') or sum(observed)<len(names):
            raise ValueError('Native logged/distinct observation counts differ')
        if receipt.get('exitCode')!=0:raise ValueError('Native exit differs')
        for flag in ('allBoundSourcesUnchanged','configurationSettingsAndInputSaveRestored','ownLockRemoved'):
            if receipt.get(flag) is not True:raise ValueError('Native preservation predicate missing: '+flag)
    return files,selected

def manifest(files,selected,inspect=False):
    rows=[{'path':n,'bytes':len(raw),'sha256':sha(raw)} for n,raw in sorted(files.items())]
    return {'schema':'veyra.refinements.manifest.v1','dataClass':'PUBLIC','bundleVersion':'0.1.0',
      'selectedUnits':list(selected),'unitVersions':{n:'0.1.1' for n in selected},'files':rows,
      'filesDigest':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode('utf8')),
      'bytes':sum(len(b) for b in files.values()),'parentCommit':PARENT_COMMIT,'parentFilesDigest':PARENT_DIGEST,
      'nativeInclusion':'CANDIDATE_INSPECTION_ONLY' if inspect else 'EXACT_SELECTED_NATIVE_BINDINGS_PASS',
      'claimScope':'BOUNDED_SOURCE_ASSET_AND_SELECTED_NATIVE_RECORDS_SAME_CORRELATED_CLUSTER',
      'originalGameAssetBytes':0,'privateRuntimeFiles':0,'saveGames':0,'newCC0DerivativeBytes':0}

def archive(target,files,result):
    if result.get('nativeInclusion')!='EXACT_SELECTED_NATIVE_BINDINGS_PASS':raise ValueError('Pending inspection cannot create an accepted archive')
    target=Path(target)
    if target.exists() or linked(target):raise ValueError('Existing archive retained')
    if any(linked(a) for a in target.absolute().parents):raise ValueError('Linked archive ancestor rejected')
    target.parent.mkdir(parents=True,exist_ok=True)
    entries={**files,'SOURCE_MANIFEST.json':(json.dumps(result,indent=2)+'\n').encode('utf8')}
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as stream:
        for name,raw in sorted(entries.items()):
            info=zipfile.ZipInfo('leviath-refinements/'+name,(2026,10,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;stream.writestr(info,raw)
    with zipfile.ZipFile(target) as stream:
        if stream.testzip() is not None or set(stream.namelist())!={'leviath-refinements/'+n for n in entries}:
            raise ValueError('Archive entry/CRC contract differs')
        if any(stream.read('leviath-refinements/'+n)!=raw for n,raw in entries.items()):raise ValueError('Decoded archive bytes differ')
    result['archive']={'filename':target.name,'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'decodedRoundtrip':'EXACT_PASS'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--units',help='Explicit crown,wildlife selection')
    parser.add_argument('--parent-root',type=Path);parser.add_argument('--inspect-candidate',action='store_true');parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    if args.inspect_candidate and args.archive:raise ValueError('Pending inspection cannot create an accepted archive')
    files,selected=collect(None if args.units is None else args.units.split(','),args.parent_root,args.inspect_candidate)
    result=manifest(files,selected,args.inspect_candidate)
    if args.archive:archive(args.archive,files,result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
