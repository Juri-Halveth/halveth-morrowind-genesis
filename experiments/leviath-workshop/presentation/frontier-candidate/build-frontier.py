#!/usr/bin/env python3
"""MIT. Own seeded sixteen-cell TES3 terrain, additive and input-bound."""
from pathlib import Path
import argparse
import datetime
import hashlib
import io
import json
import math
import random
import struct
import sys
from PIL import Image, ImageDraw
import PIL

BASE=Path(__file__).resolve().parent
MOD=BASE/'mod'
CELLS=tuple((x,y)for y in range(-64,-60)for x in range(64,68))
SIZE=8192;GRID=65;GLOBAL=257;STEP=128;SEED=20261003
REGION='veyra_frontier_region';ENTRY_NAME='LEVIATH Frontier Entry'
MATERIAL_IDS=('veyra_frontier_ground','veyra_frontier_stone','veyra_frontier_coast')
WEATHER=bytes((60,30,10,0,0,0,0,0,0,0))
VERSION=1.3
VERSION_BYTES=struct.pack('<f',VERSION)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def string(value):return value.encode('ascii')+b'\0'
def sub(kind,data):return struct.pack('<4sI',kind,len(data))+data
def record(kind,data):return struct.pack('<4sIII',kind,len(data),0,0)+data
def records(path):
 with path.open('rb')as f:
  while header:=f.read(16):
   if len(header)!=16:raise ValueError('Truncated record header')
   kind,size,_,flags=struct.unpack('<4sIII',header);data=f.read(size)
   if len(data)!=size:raise ValueError('Truncated record body')
   yield kind,flags,data
def subs(data):
 pos=0
 while pos<len(data):
  if pos+8>len(data):raise ValueError('Truncated subrecord header')
  key,n=struct.unpack_from('<4sI',data,pos);pos+=8
  if pos+n>len(data):raise ValueError('Truncated subrecord body')
  yield key,data[pos:pos+n];pos+=n
def text(value):return value.rstrip(b'\0').decode('cp1252')

def resolve_config(path):
 dirs=[];content=[];configs=[]
 def load(path):
  resolved=path.resolve()
  if resolved in configs:raise ValueError('Recursive/repeated config is outside this bound adapter')
  configs.append(resolved)
  for line in path.read_text(encoding='utf-8-sig').splitlines():
   line=line.strip()
   if not line or line.startswith('#')or'='not in line:continue
   key,value=line.split('=',1);value=value.strip().strip('"')
   if key=='data':dirs.append(Path(value))
   elif key=='content'and value.lower().endswith(('.esp','.esm')):content.append(value)
   elif key=='config':load(Path(value)/'openmw.cfg')
   elif key=='replace':raise ValueError('replace directive is not supported by this bound adapter')
 load(path)
 sources=[]
 for name in dict.fromkeys(content):
  source=next((d/name for d in reversed(dirs)if(d/name).is_file()),None)
  if source is None:raise ValueError('Unresolved declared content: '+name)
  sources.append((name,source))
 return sources,configs

def bind_base(config,binding):
 expected=json.loads(binding.read_text())
 if sha(config)!=expected['rootConfigSha256']:raise ValueError('Bound config differs')
 sources,configs=resolve_config(config)
 if [name for name,_ in sources]!=[row['content']for row in expected['content']]:
  raise ValueError('Effective content order differs from binding')
 wanted_ids={REGION,*MATERIAL_IDS,ENTRY_NAME.casefold()}
 rows=[];snapshots={p:sha(p)for p in configs};master=None
 for(name,path),row in zip(sources,expected['content']):
  if sha(path)!=row['sha256']:raise ValueError('Bound source content changed: '+name)
  snapshots[path]=row['sha256'];coordinates={b'CELL':set(),b'LAND':set()};conflicts=[]
  for kind,flags,data in records(path):
   if kind not in(b'CELL',b'LAND',b'REGN',b'LTEX'):continue
   for key,value in subs(data):
    if kind in(b'REGN',b'LTEX',b'CELL')and key==b'NAME':
     if text(value).casefold()in wanted_ids:conflicts.append('own_id:'+text(value))
     if kind!=b'CELL':break
    if kind==b'CELL'and key==b'DATA'and len(value)==12:
     f,x,y=struct.unpack('<Iii',value)
     if not f&1:coordinates[kind].add((x,y))
     break
    if kind==b'LAND'and key==b'INTV':coordinates[kind].add(struct.unpack('<ii',value));break
  overlap={kind.decode():sorted(points&set(CELLS))for kind,points in coordinates.items()}
  if conflicts or any(overlap.values()):raise ValueError('Additive namespace/coordinate collision in '+name)
  rows.append({'content':name,'sha256':row['sha256'],'bytes':path.stat().st_size,
   'collisionCount':0,'scannedCoordinateCounts':{k.decode():len(v)for k,v in coordinates.items()}})
  if name.casefold()=='morrowind.esm':master=path
 if master is None:raise ValueError('Bound Morrowind master missing')
 return master,snapshots,rows

def terrain():
 rng=random.Random(SEED)
 terms=[(rng.uniform(.6,2.5),rng.uniform(.6,2.5),rng.uniform(0,math.tau),rng.uniform(5,27))for _ in range(9)]
 heights=[]
 for y in range(GLOBAL):
  row=[]
  for x in range(GLOBAL):
   u=(x-128)/128;v=(y-128)/128
   radial=math.sqrt((u*1.04)**2+(v*.98)**2)
   # One continuous function; outer square border is the missing-LAND sea floor.
   edge=min(x,y,256-x,256-y)/256
   if edge==0:value=-2048
   else:
    coast=max(0,min(1,(1-radial)/.27))
    coast=coast*coast*(3-2*coast)
    undulation=sum(math.sin(u*a*math.pi+phase)*math.cos(v*b*math.pi-phase)*weight for a,b,phase,weight in terms)
    inland=376+undulation+120*math.sin(u*4.3)**2
    value=-2048*(1-coast)+inland*coast
    radius=math.sqrt((x-128)**2+(y-128)**2)*STEP
    if radius<=6200:value=320
    elif radius<7900:
     blend=(radius-6200)/1700;blend=blend*blend*(3-2*blend)
     value=320*(1-blend)+value*blend
   row.append(int(round(value/8))*8)
  heights.append(row)
 return heights

def at(grid,x,y):return grid[max(0,min(256,y))][max(0,min(256,x))]
def normal(grid,x,y):
 dx=(at(grid,x+1,y)-at(grid,x-1,y))/(2*STEP)
 dy=(at(grid,x,y+1)-at(grid,x,y-1))/(2*STEP)
 if x in(0,256):dx=0
 if y in(0,256):dy=0
 length=math.sqrt(dx*dx+dy*dy+1)
 return tuple(max(-127,min(127,int(round(n/length*127))))for n in(-dx,-dy,1))

def encode_heights(grid):
 first=grid[0][0]//8
 differences=[];previous_y=first
 for y in range(65):
  row_first=grid[y][0]//8
  differences.append(row_first-previous_y);previous_y=row_first
  previous_x=row_first
  for x in range(1,65):
   value=grid[y][x]//8;differences.append(value-previous_x);previous_x=value
 if any(not -128<=d<=127 for d in differences):raise ValueError('VHGT signed-byte overflow')
 return struct.pack('<f',float(first))+struct.pack('<4225b',*differences)+b'\0\0\0',min(differences),max(differences)

def lod(grid):
 values=[]
 for y in range(9):
  for x in range(9):
   height=grid[int(y*64/9)][int(x*64/9)]
   value=int(height/(128 if height>0 else 16))
   values.append(max(-128,min(127,value)))
 return struct.pack('<81b',*values)

def texture_palette(global_grid,x0,y0):
 palette=[]
 for y in range(16):
  row=[]
  for x in range(16):
   gx,gy=x0+x*4+2,y0+y*4+2
   height=at(global_grid,gx,gy)
   slope=max(abs(at(global_grid,gx+1,gy)-at(global_grid,gx-1,gy)),
       abs(at(global_grid,gx,gy+1)-at(global_grid,gx,gy-1)))/(2*STEP)
   index=3 if height<72 else 2 if slope>.40 else 1
   row.append(index)
  palette.append(row)
 # Serialized4x4 blocks, decoded as row-major by the engine.
 values=[palette[yb*4+y][xb*4+x]for yb in range(4)for xb in range(4)for y in range(4)for x in range(4)]
 return struct.pack('<256H',*values),palette

def dds(image,path):
 blobs=[]
 while True:
  out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT1');blobs.append(out.getvalue())
  if image.size==(1,1):break
  image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
 header=bytearray(blobs[0][:128]);struct.pack_into('<I',header,8,struct.unpack_from('<I',header,8)[0]|0x20000)
 struct.pack_into('<I',header,28,len(blobs));struct.pack_into('<I',header,108,0x401008)
 path.write_bytes(header+b''.join(blob[128:]for blob in blobs))

def textures():
 folder=MOD/'Textures/veyra/frontier';folder.mkdir(parents=True,exist_ok=True)
 result=[]
 for number,(name,color)in enumerate(zip(('ground','stone','coast'),((93,104,68),(101,99,88),(149,139,111)))):
  image=Image.new('RGB',(512,512));pixels=image.load();rng=random.Random(SEED+number*97)
  for y in range(512):
   for x in range(512):
    grain=rng.randint(-13,13)
    broad=8*math.sin(x*math.tau/128)*math.cos(y*math.tau/128)
    seam=4*math.sin((x+y)*math.tau/32)
    pixels[x,y]=tuple(max(0,min(255,int(channel+grain+broad+seam)))for channel in color)
  path=folder/('frontier_'+name+'.dds');dds(image,path)
  result.append(path)
 return result

def preview(grid):
 image=Image.new('RGB',(770,820),(22,29,35));draw=ImageDraw.Draw(image)
 draw.text((24,16),'LEVIATH FRONTIER / OWN HEIGHTFIELD PLAN / NOT ENGINE',fill=(231,233,230))
 draw.text((24,38),'16 cells; central flat pad; every outer height=-2048',fill=(188,197,199))
 for y in range(257):
  for x in range(257):
   h=grid[y][x]
   color=(30,65+int((h+2048)/2048*20),98)if h<0 else(99+int(h/20),122+int(h/45),74)
   draw.rectangle((x*2+128,256*2-y*2+88,x*2+129,256*2-y*2+89),fill=color)
 for i in range(5):
  draw.line((128+i*128,88,128+i*128,602),fill=(173,181,155),width=1)
  draw.line((128,88+i*128,642,88+i*128),fill=(173,181,155),width=1)
 # Entry at global vertex96,96; centre at128,128.
 ex,ey=128+96*2,88+(256-96)*2
 draw.ellipse((ex-5,ey-5,ex+5,ey+5),fill=(242,198,81))
 draw.text((32,652),'ENTRY: CELL(65,-63), X536576 Y-512000, flat height320',fill=(231,233,230))
 draw.text((32,680),'Water/soil appearance and native traversal remain to be tested.',fill=(188,197,199))
 image.save(BASE/'HEIGHTFIELD_PREVIEW.png')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--base-config',type=Path,required=True)
 parser.add_argument('--binding',type=Path,default=BASE/'BASE_CONTENT_COLLISION_RECEIPT.json')
 args=parser.parse_args()
 if len(CELLS)!=16 or len(set(CELLS))!=16:raise ValueError('Sixteen-cell contract broken')
 master,snapshot,sources=bind_base(args.base_config,args.binding)
 MOD.mkdir(parents=True,exist_ok=True)
 terrain_grid=terrain();texture_files=textures();bodies=[];cell_info=[]
 assert VERSION_BYTES.hex()=='6666a63f'and len(WEATHER)==10 and sum(WEATHER)==100
 bodies.append(record(b'REGN',sub(b'NAME',string(REGION))+sub(b'FNAM',string('LEVIATH Frontier'))+
  sub(b'WEAT',WEATHER)+sub(b'CNAM',struct.pack('<I',0x005a7752))))
 for i,name in enumerate(MATERIAL_IDS):
  path='veyra/frontier/frontier_'+('ground','stone','coast')[i]+'.dds'
  bodies.append(record(b'LTEX',sub(b'NAME',string(name))+sub(b'INTV',struct.pack('<I',i))+sub(b'DATA',string(path))))
 for x,y in CELLS:
  name=ENTRY_NAME if(x,y)==(65,-63)else''
  bodies.append(record(b'CELL',sub(b'NAME',string(name))+sub(b'DATA',struct.pack('<Iii',2,x,y))+
   sub(b'RGNN',string(REGION))))
 for x,y in CELLS:
  x0,y0=(x-64)*64,(y+64)*64
  tile=[row[x0:x0+65]for row in terrain_grid[y0:y0+65]]
  vhgt,dmin,dmax=encode_heights(tile)
  normals=[n for yy in range(65)for xx in range(65)for n in normal(terrain_grid,x0+xx,y0+yy)]
  vtex,palette=texture_palette(terrain_grid,x0,y0)
  data=(sub(b'INTV',struct.pack('<ii',x,y))+sub(b'DATA',struct.pack('<I',7))+
    sub(b'VNML',struct.pack('<12675b',*normals))+sub(b'VHGT',vhgt)+sub(b'WNAM',lod(tile))+
    sub(b'VCLR',bytes((255,))*12675)+sub(b'VTEX',vtex))
  bodies.append(record(b'LAND',data))
  cell_info.append({'coordinates':[x,y],'heightRange':[min(map(min,tile)),max(map(max,tile))],
   'heightDeltaRange':[dmin,dmax],'heightGridSha256':hashlib.sha256(struct.pack('<4225i',*(h for row in tile for h in row))).hexdigest(),
   'textureIndices':sorted({index for row in palette for index in row})})
 assert len(bodies)==36
 header=sub(b'HEDR',struct.pack('<fI32s256sI',VERSION,0,b'LEVIATH Workshop',
   b'Own additive sixteen-cell Frontier terrain; no original cell overrides',len(bodies)))
 header+=sub(b'MAST',string('Morrowind.esm'))+sub(b'DATA',struct.pack('<Q',master.stat().st_size))
 plugin=MOD/'LEVIATH-Frontier.esp';plugin.write_bytes(record(b'TES3',header)+b''.join(bodies))
 entry={'schema':'veyra.frontier-entry.v1','version':'0.1.0','cellName':ENTRY_NAME,'cellCoordinates':[65,-63],
  'position':{'x':536576,'y':-512000,'z':576},'terrainHeight':320,'verticalMargin':256,
  'centralPad':{'centre':{'x':540672,'y':-507904,'z':320},'flatRadius':6200},
  'networkEffects':0,'automaticTeleport':False,'plugin':'LEVIATH-Frontier.esp','pluginSha256':sha(plugin),
  'nativeEntryObservation':'PENDING_ROOT_PROBE'}
 (BASE/'ENTRY.json').write_text(json.dumps(entry,indent=2)+'\n',encoding='utf-8')
 preview(terrain_grid)
 for path,digest in snapshot.items():
  if sha(path)!=digest:raise ValueError('Source changed during build')
 generated={p.relative_to(MOD).as_posix():sha(p)for p in MOD.rglob('*')if p.is_file()}
 result={'schema':'veyra.frontier-build.v1','version':'0.1.0','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'seed':SEED,'generatorSha256':sha(Path(__file__)),'buildRuntime':{'python':sys.version.split()[0],'pillow':PIL.__version__},
  'status':'OWN_ADDITIVE_BYTES_BUILT_NATIVE_PENDING','formatVersion':{'name':'TES3_1.3','hedrBytesHex':VERSION_BYTES.hex(),
    'storedFloat32':struct.unpack('<f',VERSION_BYTES)[0],'regionWeatBytes':10,'weatherProbabilitySum':100},
  'recordCounts':{'TES3':1,'REGN':1,'LTEX':3,'CELL':16,'LAND':16},'contentBinding':sources,
  'baseConfigSha256':sha(args.base_config),'bindingManifestSha256':sha(args.binding),
  'collisionCount':0,'originalCoordinateOverrides':0,'sourceFilesUnchanged':len(snapshot),
  'cellCoordinates':[list(c)for c in CELLS],'heightScale':8,'globalGridSize':257,'cellGridSize':65,
  'cells':cell_info,'heightRange':[min(map(min,terrain_grid)),max(map(max,terrain_grid))],
  'outerHeight':-2048,'sharedEdges':'GENERATED_FROM_SAME_GLOBAL_GRID_PENDING_SERIALIZED_CHECK',
  'texturePaths':[p.relative_to(MOD).as_posix()for p in texture_files],
  'generatedHashes':generated,'entryManifestSha256':sha(BASE/'ENTRY.json'),
  'originalGameAssetsCopied':0,'engineStarted':False,'sourceProfilesMutated':0,'networkEffects':0,
  'claimCeiling':'OWN_ADDATIVE_TERRAIN_BYTES_WITH_BOUND_BASE_COLLISION_CHECK_ONLY'}
 (BASE/'BUILD_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('FRONTIER_BUILD_PASS CELL16 LAND16 LTEX3 REGN1 version1.3 WEAT10 originalOverrides0')

if __name__=='__main__':main()
