"""Package an exact own-source and owned procedural asset allowlist, never game data."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('legacy_source_boundary',ROOT/'scripts/package.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
UNITS={
 'prototypes/wildlife-source-only':('LICENSE','README.md','PUBLIC_SCOPE.md','SOURCE_BINDING.json',
 'build-creature.py','check-creature.py',
 'mod/Veyra-Wildlife.omwscripts','mod/scripts/veyra_wildlife/actor.lua','mod/scripts/veyra_wildlife/config.lua','mod/scripts/veyra_wildlife/global.lua'),
 'presentation/crown-candidate':('LICENSE','README.md','THIRD_PARTY_NOTICES.md','build-crown.py','check-crown.py','geometry-kernel.py','cfg-additive.txt','PLACEMENT.json'),
 'presentation/frontier-scenery-candidate':('LICENSE','README.md','THIRD_PARTY_NOTICES.md','build-scenery.py','check-scenery.py','geometry-kernel.py','cfg-additive.txt','SCENERY_MANIFEST.json'),
 'presentation/bark-materials':('CC0-1.0.txt','SOURCE_BINDING.json','THIRD_PARTY_NOTICES.md'),
 'presentation/frontier-candidate':('LICENSE','README.md','build-frontier.py','check-frontier.py','verify-frontier.py','verify-frontier.sh','cfg-additive.txt','ENTRY.json','PARSER_BINDING.json'),
 'presentation/frontier-texture-candidate':('LICENSE','README.md','build-textures.py','check-textures.py','cfg-texture-only.txt'),
 'presentation/plaza-candidate':('LICENSE','README.md','build-plaza.py','check-plaza.py','cfg-additive.txt','PLACEMENTS.json'),
 'gameplay/portal':('LICENSE','README.md','mod/veyra-portal.omwscripts','mod/scripts/veyra_portal/config.lua','mod/scripts/veyra_portal/global.lua','mod/scripts/veyra_portal/player.lua'),
 'gameplay/construction':('LICENSE','README.md','mod/veyra-construction.omwscripts','mod/scripts/veyra_construction/config.lua','mod/scripts/veyra_construction/global.lua','mod/scripts/veyra_construction/player.lua','mod/Meshes/veyra/construction/plantbed.dae'),
 'gameplay/townlife':('LICENSE','README.md','SOURCE_BINDING.json','ANCHOR_PATCH_BINDING.json','UI_ONLY.diff','build-assets.py','check-townlife.lua','bind-frontier.py','mod/Veyra-Townlife.omwscripts','mod/scripts/veyra_townlife/config.lua','mod/scripts/veyra_townlife/global.lua','mod/scripts/veyra_townlife/actor.lua','mod/scripts/veyra_townlife/player.lua'),
 'gameplay/panels':('LICENSE','README.md','SOURCE_BINDINGS.json','mod/veyra-panel-coordinator.omwscripts','mod/scripts/veyra_panels/player.lua','mod/scripts/veyra_courier/config.lua','mod/scripts/veyra_courier/global.lua','mod/scripts/veyra_courier/player.lua','mod/scripts/veyra_fieldwork/player.lua','mod/scripts/veyra_portal/player.lua','mod/scripts/veyra_construction/player.lua','mod/scripts/halveth/fieldcraft.lua','mod/scripts/halveth/knowledge.lua','mod/scripts/halveth/paths.lua','mod/scripts/halveth/player.lua','mod/scripts/halveth/universe.lua','mod/scripts/halveth/worldlife.lua'),
 'presentation/hud014':('LICENSE','README.md','build-assets.py','check-assets.py','check-hud-label.lua','SOURCE_BINDING.json','mod/Veyra-Presentation.omwscripts','mod/scripts/veyra/hud.lua'),
}
NATIVE_FILES={'docs/WORLD_NATIVE.json','docs/HUD014_NATIVE.json','docs/PORTAL_NATIVE.json',
              'docs/CONSTRUCTION_NATIVE.json','docs/TOWNLIFE_NATIVE.json','docs/INTEGRATION_NATIVE.json',
              'docs/COURIER024_NATIVE.json','docs/PROVISION_WORLD_NATIVE.json','docs/CORE_NATIVE.json'}
EXTRA_FIXED={'scripts/provision-world.py','scripts/provision-world.sh','scripts/package-world.py','scripts/check-world-lua.sh',
             'tests/test_world_provision.py','tests/test_world_package.py','docs/WORLD_PROVISIONING.md',
             'docs/OWN_ASSET_BINDINGS.json','docs/KEY_CAPABILITY.json','docs/RELEASE_0.2.0.md','docs/ENGINE_API_BINDINGS.json',
             'presentation/spatial-audio/KENNEY-LICENSE.txt','presentation/spatial-audio/ASSET_RECEIPT.json'}
NEW_TEXT=EXTRA_FIXED|{prefix+'/'+name for prefix,names in UNITS.items() for name in names}
ASSETS={
 'presentation/spatial-audio/mod/Sound/veyra/courier_bell_mono.wav',
 'presentation/crown-candidate/mod/Veyra-Dense-Crown.esp',
 'presentation/crown-candidate/mod/Meshes/veyra/veyra_swamp_crown_01.dae',
 'presentation/crown-candidate/mod/Textures/veyra/crown_leaf_01.dds',
 'presentation/frontier-scenery-candidate/mod/LEVIATH-Frontier-Scenery.esp',
 'presentation/frontier-scenery-candidate/mod/Meshes/veyra/frontier_scenery/veyra_frontier_grass_01.dae',
 'presentation/frontier-scenery-candidate/mod/Meshes/veyra/frontier_scenery/veyra_frontier_stone_cluster_01.dae',
 'presentation/bark-materials/mod/Textures/veyra/swamp_bark.dds',
 'presentation/bark-materials/mod/Textures/veyra/swamp_bark_n.dds',
 'presentation/frontier-candidate/mod/LEVIATH-Frontier.esp',
 'presentation/plaza-candidate/mod/LEVIATH-Plaza.esp',
 'presentation/plaza-candidate/mod/Meshes/veyra/plaza/veyra_plaza_approach.dae',
 'presentation/plaza-candidate/mod/Meshes/veyra/plaza/veyra_plaza_arena.dae',
 'presentation/plaza-candidate/mod/Meshes/veyra/plaza/veyra_plaza_arrival.dae',
 'gameplay/townlife/mod/Textures/veyra_townlife/white.png',
 'presentation/hud014/mod/Textures/veyra/white.png',
}|{prefix+'/mod/Textures/veyra/frontier/frontier_'+name+'.dds'
   for prefix in ('presentation/frontier-candidate','presentation/frontier-texture-candidate')
   for name in ('ground','stone','coast')}
CC0_ASSETS={'presentation/bark-materials/mod/Textures/veyra/'+n for n in ('swamp_bark.dds','swamp_bark_n.dds')}|{
 'presentation/spatial-audio/mod/Sound/veyra/courier_bell_mono.wav'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def regular(relative,limit):
    path=ROOT/relative
    if not path.is_file() or path.is_symlink() or any((ROOT/Path(*Path(relative).parts[:i])).is_symlink()
            for i in range(1,len(Path(relative).parts))):
        raise ValueError('Required regular publication file missing or symlinked: '+relative)
    if path.stat().st_size>limit:raise ValueError('Publication file exceeds bound: '+relative)
    return path.read_bytes()


def text_file(relative):
    raw=regular(relative,512*1024)
    text=raw.decode('utf-8-sig')
    if '\0' in text or legacy.LOCAL_PATH.search(text) or legacy.PRIVATE_KEY.search(text) or legacy.ACCESS_TOKEN.search(text):
        raise ValueError('Publication text requires private/binary review: '+relative)
    return raw


def collect(require_native=True):
    legacy.ROOT=ROOT
    files=legacy.collect()  # Historical receipts still bind their unchanged source bytes.
    for relative in sorted(NEW_TEXT):files[relative]=text_file(relative)
    bound=json.loads(files['docs/OWN_ASSET_BINDINGS.json'])
    if bound.get('schema')!='veyra.workshop.own-assets.v1' or bound.get('bethesdaAssetBytes')!=0:
        raise ValueError('Owned asset manifest has a different reviewed scope')
    if set(bound.get('assets',{}))!=ASSETS:
        raise ValueError('Asset binding set differs from the exact authored allowlist')
    for relative in sorted(ASSETS):
        row=bound['assets'][relative];raw=regular(relative,16*1024*1024)
        license_name='CC0-1.0' if relative in CC0_ASSETS else 'MIT'
        if row.get('license')!=license_name or row.get('originalGameAssetBytes')!=0 or row.get('sha256')!=sha(raw) or row.get('bytes')!=len(raw):
            raise ValueError('Owned asset bytes/license differ from source binding: '+relative)
        if relative in CC0_ASSETS:
            for file_key,hash_key in (('licenseFile','licenseSha256'),('provenanceFile','provenanceSha256')):
                path=row[file_key]
                if path not in files or sha(files[path])!=row[hash_key]:raise ValueError('CC0 license/provenance closure differs')
            if row.get('sourceGenerator'):
                generator=row['sourceGenerator']
                if generator not in files or sha(files[generator])!=row['sourceGeneratorSha256']:
                    raise ValueError('CC0 transformation source binding differs')
        else:
            generator=row['sourceGenerator']
            if generator not in files or sha(files[generator])!=row['sourceGeneratorSha256']:
                raise ValueError('Owned asset generator is outside the exact source closure: '+relative)
        if relative.endswith('.dds') and raw[:4]!=b'DDS ':raise ValueError('Owned DDS header differs')
        if relative.endswith('.esp') and raw[:4]!=b'TES3':raise ValueError('Owned ESP header differs')
        if relative.endswith('.png') and raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Owned PNG header differs')
        if relative.endswith('.wav') and (raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE'):raise ValueError('Bound CC0 WAV header differs')
        if relative.endswith('.dae'):
            text=raw.decode('utf8');
            if '<COLLADA' not in text or legacy.LOCAL_PATH.search(text):raise ValueError('Owned COLLADA contract differs')
        files[relative]=raw
    for relative in sorted(NATIVE_FILES):
        if not require_native and not (ROOT/relative).is_file():continue
        raw=text_file(relative);receipt=json.loads(raw)
        hashes=receipt.get('moduleHashes')
        if not hashes:raise ValueError('Native inclusion has no exact selected source binding: '+relative)
        for source,expected in hashes.items():
            if source not in files or sha(files[source])!=expected:
                raise ValueError('Active native receipt/source binding differs: '+relative+' -> '+source)
        gate=receipt.get('nativeInclusionGate')
        if require_native and (gate in ('PENDING','NOT_RUN') or
                               (relative=='docs/PROVISION_WORLD_NATIVE.json' and gate is None)):
            raise ValueError('Active native inclusion gate remains pending: '+relative)
        if relative=='docs/PROVISION_WORLD_NATIVE.json':
            if gate!='EXACT_NEW_PROFILE_UNMODIFIED_NORMAL_SAVE_START_BOUND' or receipt.get('status')!='BOUNDED_NATIVE_NORMAL_SAVE_START_PASS':
                raise ValueError('New profile native scope differs from reviewed normal-save-start contract')
            if receipt.get('exitCode')!=0 or receipt.get('timedOut') is not False or receipt.get('debugFixtureRegistered') is not False:
                raise ValueError('New profile normal native run is incomplete or debug-derived')
            for predicate in ('allInstallationInputsUnchanged','allNativeModulesBeforeAfterEqual','allBoundOriginalsUnchanged',
                              'profileConfigurationRestored','playLockRemoved','explicitUnchangedSaveCopyLoaded'):
                if receipt.get(predicate) is not True:raise ValueError('New profile native preservation predicate incomplete')
        if relative=='docs/CORE_NATIVE.json':
            if gate!='EXACT_INSTALLED_PAYLOAD_PRIVATE_DERIVED_CORE_PROBE_BOUND' or receipt.get('status')!='BOUNDED_NATIVE_CORE_PASS':
                raise ValueError('Core native scope differs from the private-derived controller contract')
            if receipt.get('privateControllerDerivation',{}).get('modifiedHunks')!=1:
                raise ValueError('Core private controller derivation differs')
            names=[]
            for run in receipt.get('results',[]):
                if run.get('exitCode')!=0 or run.get('complete')is not True or run.get('timedOut')is not False:
                    raise ValueError('Core native run incomplete')
                names+=run['assertionNames']
            if len(names)!=149 or len(set(names))!=144 or receipt.get('loggedPassCount')!=149 or receipt.get('distinctAssertionCount')!=144:
                raise ValueError('Core native logged/distinct counts differ')
        files[relative]=raw
    overlay=json.loads(files['gameplay/panels/SOURCE_BINDINGS.json'])
    for name,h in overlay['productionHashes'].items():
        path='gameplay/panels/mod/'+name
        if path not in files or sha(files[path])!=h:raise ValueError('Frozen UI overlay closure differs')
    prototype=json.loads(files['prototypes/wildlife-source-only/SOURCE_BINDING.json'])
    if prototype.get('classification')!='PROTOTYPE_SOURCE_ONLY' or prototype.get('installationModule') is not False or prototype.get('defaultEnabled') is not False:
        raise ValueError('Prototype source-only/default-off scope differs')
    for source,expected in prototype['sourceHashes'].items():
        path='prototypes/wildlife-source-only/'+source
        if path not in files or sha(files[path])!=expected:raise ValueError('Frozen prototype source binding differs')
    return files


def manifest(files,accepted):
    rows=[{'path':name,'bytes':len(raw),'sha256':sha(raw)} for name,raw in sorted(files.items())]
    return{'schema':'veyra.workshop.own-source-assets-manifest.v2','dataClass':'PUBLIC','version':'0.2.0',
           'scope':'EXACT_OWN_SOURCE_MIT_ASSETS_AND_SEPARATE_CC0_ALLOWLIST','files':rows,
           'filesDigest':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),
           'bytes':sum(len(raw) for raw in files.values()),'ownedGeneratedAssetFiles':len(ASSETS-CC0_ASSETS),
           'separatelyLicensedCC0DerivativeFiles':len(CC0_ASSETS),
           'nativeInclusion':'EXACT_RECEIPT_BINDINGS_REQUIRED_PASS' if accepted else 'CANDIDATE_INSPECTION_NATIVE_GATES_NOT_ENFORCED',
           'proprietaryGameAssets':0,'saveGames':0,'downloadedAssetDerivatives':len(CC0_ASSETS),'privateRuntimeFiles':0,
           'inspection':'BOUND_TEXT_AND_EXACT_OWN_BINARY_DIGEST_CONTRACT; root review remains separate'}


def archive(target,files,result):
    target=target.resolve()
    if target.exists():raise ValueError('Existing archive retained; choose a new output')
    target.parent.mkdir(parents=True,exist_ok=True)
    entries={**files,'SOURCE_MANIFEST.json':(json.dumps(result,indent=2)+'\n').encode('utf8')}
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as stream:
        for name,raw in sorted(entries.items()):
            info=zipfile.ZipInfo('leviath-workshop/'+name,(2026,10,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;stream.writestr(info,raw)
    with zipfile.ZipFile(target) as stream:
        if stream.testzip() is not None:raise ValueError('Own-source archive CRC failed')
        if any(stream.read('leviath-workshop/'+n)!=raw for n,raw in entries.items()):
            raise ValueError('Own-source archive decoded-byte roundtrip failed')
    result['archive']={'filename':target.name,'bytes':target.stat().st_size,'sha256':sha(target.read_bytes()),'roundtrip':'EXACT_DECODED_BYTES_PASS'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--inspect-candidate',action='store_true',help='Read-only inspection without native eligibility or ZIP')
    args=parser.parse_args()
    if args.inspect_candidate and args.archive:raise ValueError('A pending candidate inspection cannot create an accepted archive')
    files=collect(not args.inspect_candidate);result=manifest(files,not args.inspect_candidate)
    if args.archive:archive(args.archive,files,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
