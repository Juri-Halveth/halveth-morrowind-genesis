"""MIT. Build local MODL/ITEX overrides from the user's licensed TES3 records.

No original record bodies are distributed in this source package. A flat,
explicit source OpenMW config supplies the licensed logical load order.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,struct

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fields(body):
 offset=0
 while offset<len(body):
  if len(body)-offset<8:raise ValueError('Truncated subrecord header')
  tag,size=struct.unpack_from('<4sI',body,offset);offset+=8
  value=body[offset:offset+size];offset+=size
  if len(value)!=size:raise ValueError('Truncated subrecord value')
  yield tag,value
def records(p):
 if p.stat().st_size>128*1024*1024:raise ValueError('Source file exceeds parser limit')
 with p.open('rb') as stream:
  while header:=stream.read(16):
   if len(header)!=16:raise ValueError('Truncated record header')
   tag,size,unknown,flags=struct.unpack('<4sIII',header)
   if size>64*1024*1024:raise ValueError('Record exceeds parser limit')
   body=stream.read(size)
   if len(body)!=size:raise ValueError('Truncated record body')
   yield tag,body,unknown,flags
def sub(tag,value):return struct.pack('<4sI',tag,len(value))+value
def record(tag,body,unknown=0,flags=0):return struct.pack('<4sIII',tag,len(body),unknown,flags)+body
def identifier(value):return value.rstrip(b'\0').decode('cp1252').casefold()
def relative(value):
 p=Path(value)
 if p.is_absolute() or ':' in value or '..' in p.parts or '\\' in value:raise ValueError('Invalid relative asset address')
 return p

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();source_root=Path(__file__).resolve().parent.parent
config=args.config.resolve(strict=True);destination=args.output.resolve()
if destination.exists():raise ValueError('Output must be a fresh directory')
if destination==source_root or source_root.is_relative_to(destination) or destination.is_relative_to(source_root):raise ValueError('Output must be separate from the source package')
if config.stat().st_size>1024*1024:raise ValueError('Config exceeds parser limit')
roots=[];names=[];local_root=None;resets=set()
for row in config.read_text(encoding='utf-8-sig').splitlines():
 if row.startswith('config='):raise ValueError('Includes are unsupported; provide an explicit isolated flat config')
 if row.startswith('replace='):
  key=row.split('=',1)[1].strip()
  if key in {'config','data','content'}:
   if roots or local_root or names:raise ValueError('Source resets must precede source entries')
   if key in resets:raise ValueError('Duplicate source reset')
   resets.add(key)
  elif key not in {'fallback','fallback-archive','groundcover'}:raise ValueError('Unsupported replacement directive')
  continue
 if row.startswith(('data=','data-local=')):
  if resets!={'config','data','content'}:raise ValueError('Explicit config/data/content resets are required before source entries')
  root=Path(row.split('=',1)[1].strip().strip('"'))
  if not root.is_absolute():root=config.parent/root
  root=root.resolve(strict=True)
  if not root.is_dir():raise ValueError('Data root must be a directory')
  if row.startswith('data-local='):
   if local_root is not None:raise ValueError('Only one explicit data-local root is supported')
   local_root=root
  else:roots.append(root)
 elif row.startswith('content='):
  if resets!={'config','data','content'}:raise ValueError('Explicit source resets are required')
  name=row.split('=',1)[1].strip();relative(name)
  if '/' in name:raise ValueError('Content requires a simple filename')
  if Path(name).suffix.casefold() in {'.esm','.esp','.omwaddon','.omwgame'}:names.append(name)
if local_root is not None:roots.append(local_root)
if not roots or not names:raise ValueError('A flat config with explicit data and logical content is required')
if len(names)!=len(set(n.casefold() for n in names)):raise ValueError('Duplicate logical content names')
for root in [*roots,config.parent]:
 if destination==root or destination.is_relative_to(root) or root.is_relative_to(destination):raise ValueError('Output must be separate from source config and game data roots')
sources=[]
for name in names:
 p=next((r/name for r in reversed(roots) if (r/name).is_file()),None)
 if p is None:raise ValueError('Unresolved content: '+name)
 sources.append(p)
master=next((p for p in sources if p.name.casefold()=='morrowind.esm'),None)
if master is None:raise ValueError('Licensed Morrowind.esm is required')
world=json.loads((source_root/'world-map.json').read_text(encoding='utf8'))
icons=json.loads((source_root/'item-map.json').read_text(encoding='utf8'))['items']
if len(world)!=39 or len(icons)!=40:raise ValueError('Bound map counts differ')
wm={r['recordId'].casefold():r for r in world};im={r['recordId'].casefold():r for r in icons}
if len(wm)!=39 or len(im)!=40:raise ValueError('Duplicate record IDs')
before={str(p):sha(p) for p in sources};selected={}
for p in sources:
 for tag,body,unknown,flags in records(p):
  if tag not in {b'STAT',b'MISC',b'LIGH',b'WEAP',b'ARMO',b'CLOT',b'INGR',b'BOOK',b'ALCH',b'LOCK',b'PROB',b'REPA',b'APPA'}:continue
  parts=list(fields(body));ids=[identifier(v) for k,v in parts if k==b'NAME']
  if ids and ids[0] in wm.keys()|im.keys():
   if any(k==b'DELE' for k,v in parts):raise ValueError('A bound record is deleted')
   selected[ids[0]]=(tag,parts,unknown,flags)
if set(selected)!=wm.keys()|im.keys():raise ValueError('Some bound records are unresolved')
payload=[]
for line in (source_root/'PAYLOAD.sha256').read_text(encoding='utf8').splitlines():
 path=relative(line[66:]);source=source_root/path
 if not source.is_file() or source.is_symlink() or sha(source)!=line[:64]:raise ValueError('Own asset binding differs')
 payload.append((source,path))
for row in world:
 model=source_root/'mod/Meshes'/relative(row['model'])
 if sha(model)!=row['modelSha256']:raise ValueError('Model differs from map')
for row in icons:
 if not (source_root/'mod/Icons'/relative(row['iconPath'])).is_file():raise ValueError('Own icon is missing')
plugins=[];checks=[]
for filename,mapping,field in [('REZERO-Original-Room.esp',wm,b'MODL'),('REZERO-Original-Items.esp',im,b'ITEX')]:
 output=[]
 for rid,row in sorted(mapping.items()):
  tag,parts,unknown,flags=selected[rid]
  if field==b'MODL' and tag.decode()!=row['kind']:raise ValueError('Record type differs')
  if sum(k==field for k,v in parts)!=1:raise ValueError('Exactly one target field is required')
  value=row['model'] if field==b'MODL' else row['iconPath']
  updated=[(k,value.encode('ascii')+b'\0' if k==field else v) for k,v in parts]
  # Icons see the new world-model field for intersecting original item IDs.
  if field==b'ITEX' and rid in wm:
   updated=[(k,wm[rid]['model'].encode('ascii')+b'\0' if k==b'MODL' else v) for k,v in updated]
  allowed={field}|({b'MODL'} if field==b'ITEX' and rid in wm else set())
  if [(k,v) for k,v in updated if k not in allowed]!=[(k,v) for k,v in parts if k not in allowed]:raise ValueError('Logical fields changed')
  body=b''.join(sub(k,v) for k,v in updated);output.append(record(tag,body,unknown,flags))
  checks.append({'plugin':filename,'id':rid,'changedFields':sorted(k.decode() for k in allowed),'outputRecordSha256':hashlib.sha256(body).hexdigest()})
 h=sub(b'HEDR',struct.pack('<fI32s256sI',1.3,0,b'REZERO Own Art',b'Local licensed-record binding for new presentation.',len(output)))
 h+=sub(b'MAST',master.name.encode('ascii')+b'\0')+sub(b'DATA',struct.pack('<Q',master.stat().st_size))
 plugins.append((filename,record(b'TES3',h)+b''.join(output)))
if before!={str(p):sha(p) for p in sources}:raise ValueError('Source changed during build')
destination.mkdir(parents=True)
for source,path in payload:
 target=destination/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for name,data in plugins:(destination/'mod'/name).write_bytes(data)
(destination/'CONTENT.list').write_text('REZERO-Original-Room.esp\nREZERO-Original-Items.esp\nrezero.omwscripts\n',encoding='ascii')
(destination/'LOCAL_BUILD_PRIVATE.json').write_text(json.dumps({'scope':'39 MODL and 40 ITEX overrides, no new CELL/reference records','sourceFiles':before,'sourceUnchanged':True,'checks':checks},indent=2)+'\n',encoding='utf8')
print('BUILT',destination,'39 original model records; 40 original icon records. Native profile integration is separate.')
