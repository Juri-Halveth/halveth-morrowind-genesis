"""Create a local appearance-only plugin from installed, credited head packs.

Only existing base BODY records for head/hair are copied. MODL is the sole
changed subrecord; NPCs, deletion records, flags, race and body flags remain
untouched. Requires the user's three GOTY masters and separately acquired packs.
The derived plugin stays in .local; no game assets enter the source archive.
"""
from pathlib import Path
import hashlib, json, struct
from datetime import datetime, timezone
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_profile import default_install, parse_entries, source_path, atomic_text

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def records(path):
    with path.open('rb') as stream:
        size=path.stat().st_size
        while header:=stream.read(16):
            if len(header)!=16:raise ValueError('Truncated record')
            tag,n,unknown,flags=struct.unpack('<4sIII',header)
            if n>64*1024*1024 or stream.tell()+n>size:raise ValueError('Invalid record size')
            raw=stream.read(n)
            if tag!=b'BODY':continue
            sub=[];cursor=0
            while cursor<len(raw):
                if cursor+8>len(raw):raise ValueError('Truncated subrecord')
                key,length=struct.unpack_from('<4sI',raw,cursor);cursor+=8
                if cursor+length>len(raw):raise ValueError('Invalid subrecord size')
                sub.append((key,raw[cursor:cursor+length]));cursor+=length
            values=dict(sub)
            yield values.get(b'NAME',b'').rstrip(b'\0').lower(),unknown,flags,sub

def subbytes(parts):return b''.join(struct.pack('<4sI',tag,len(value))+value for tag,value in parts)
def recbytes(tag,parts,unknown=0,flags=0):
    payload=subbytes(parts)
    return struct.pack('<4sIII',tag,len(payload),unknown,flags)+payload

def main():
    install=default_install();source=install/'profiles/max'
    dirs=[source_path(v,source) for k,v in parse_entries(source/'openmw.cfg') if k=='data']
    masters=[];base={}
    for name in ('Morrowind.esm','Tribunal.esm','Bloodmoon.esm'):
        found=next((d/name for d in reversed(dirs) if (d/name).is_file()),None)
        if found is None:raise FileNotFoundError(name)
        masters.append(found)
        for rid,u,f,sub in records(found):base[rid]=(u,f,sub)
    graphics=ROOT/'.local/graphics';mods=graphics/'mods'
    sources=[mods/'Better-Heads/Better Heads.esm',mods/'Better-Heads/Better Heads Tribunal addon.esm',
             mods/'khajiit-head-pack-1.4-base/Khajiit-BaseReplace.ESP']
    overrides={};changes=[];skipped=[]
    for pack in sources:
        for rid,_,_,sub in records(pack):
            proposed=dict(sub)
            if rid not in base or b'DELE' in proposed:
                skipped.append({'id':rid.decode('cp1252'),'source':pack.name,'reason':'not an existing live base BODY'});continue
            unknown,flags,original=base[rid];old=dict(original)
            if b'BYDT' not in old or old[b'BYDT'][0] not in (0,1) or b'MODL' not in proposed:
                skipped.append({'id':rid.decode('cp1252'),'source':pack.name,'reason':'not head or hair'});continue
            replacement=proposed[b'MODL']
            model=replacement.rstrip(b'\0').decode('cp1252').replace('\\','/')
            if not any((d/'Meshes'/model).is_file() for d in (mods/'Better-Heads',mods/'khajiit-head-pack-1.4-base')):
                raise FileNotFoundError('Missing model: '+model)
            parts=[(key,replacement if key==b'MODL' else value) for key,value in original]
            # Every non-model byte and the base header fields are preserved.
            assert [(k,v) for k,v in parts if k!=b'MODL']==[(k,v) for k,v in original if k!=b'MODL']
            overrides[rid]=recbytes(b'BODY',parts,unknown,flags)
            changes.append({'id':rid.decode('cp1252'),'source':pack.name,'model':model,'changedFields':['MODL']})
    hedr=struct.pack('<fI32s256sI',1.3,0,b'HALVETH visual adapter',b'Head and hair model paths only. Original NPC, race and body flags preserved. Credits in original Better Heads and Khajiit pack readmes.',len(overrides))
    header=[(b'HEDR',hedr)]
    for master in masters:header.extend([(b'MAST',master.name.encode()+b'\0'),(b'DATA',struct.pack('<Q',master.stat().st_size))])
    blob=recbytes(b'TES3',header)+b''.join(overrides.values())
    dest=mods/'genesis-head-adapter';dest.mkdir(parents=True,exist_ok=True)
    plugin=dest/'HALVETH-Beautiful-Heads.esp'
    if plugin.exists() and plugin.read_bytes()!=blob:raise ValueError('Existing adapter differs; preserve it before building a new version')
    plugin.write_bytes(blob)
    receipt={'recordedAt':datetime.now(timezone.utc).isoformat(),'file':plugin.name,'sha256':digest(plugin),'bytes':len(blob),
        'bodyRecords':len(overrides),'changedFields':['BODY.MODL'],'npcRecords':0,'deletedRecords':0,
        'sources':[{'name':p.name,'sha256':digest(p)} for p in sources],
        'masters':[{'name':p.name,'sha256':digest(p)} for p in masters],'changes':changes,'skipped':skipped}
    atomic_text(dest/'adapter-receipt.json',json.dumps(receipt,indent=2))
    atomic_text(dest/'CREDITS.txt','Better Heads: Gorg, Arathrax/DarkSharp, Motoki and all original model/texture artists named in ../Better-Heads/BH readme.txt.\nKhajiit Head Pack: all authors and credits in ../khajiit-head-pack-1.4-base original readmes.\nModels remain unmodified and keep their original names. HALVETH only replaces existing head/hair BODY.MODL paths. This local derivative is not bundled in the source archive.\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('changes','skipped')},indent=2))

if __name__=='__main__':main()
