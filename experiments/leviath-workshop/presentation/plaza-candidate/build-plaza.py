#!/usr/bin/env python3
"""MIT. Own bounded arrival, approach and arena; references in owned Frontier only."""
from pathlib import Path
from dataclasses import dataclass,field
import argparse,datetime,hashlib,importlib.util,json,math,struct,sys
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw

BASE=Path(__file__).resolve().parent
MOD=BASE/'mod'
FRONTIER=BASE.parent/'frontier-candidate'
FRONTIER_SHA='7484682d663d62a22dfe59c01d3dbce862a2e1897f66e1b563b5b455cb2a75ad'
ENTRY_SHA='e79d41749cb8084edf2fb70a91a07aec13a3869bfac52a0beef683d21d02c1f2'
BINDER_SHA='300202c2d19493c715effe737fc6f08443512140993697706eab0747f9eef298'
STONE_SHA='d54f2025d173e9ade36d1e011c20b0f2e4667e2afe353013a5f05cff1b0bad31'
NS='http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('',NS)
IDS=('veyra_plaza_arrival','veyra_plaza_approach','veyra_plaza_arena')
CENTRE=(540672.,-507904.,320.)
ENTRY=(536576.,-512000.,320.)
GATE_ANGLE=math.pi*1.25
SEGMENTS=128

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def subtract(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def direction(a):
 length=math.sqrt(sum(v*v for v in a))
 if length<1e-8:raise ValueError('Degenerate owned triangle')
 return tuple(v/length for v in a)

@dataclass
class Mesh:
 positions:list=field(default_factory=list)
 normals:list=field(default_factory=list)
 uvs:list=field(default_factory=list)
 indices:list=field(default_factory=list)
 def triangle(self,a,b,c):
  normal=direction(cross(subtract(b,a),subtract(c,a)))
  # Planar projection chooses the two major face axes. Scale256worldunits
  # per texture tile keeps floors and walls on a coherent own material scale.
  omitted=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3)if i!=omitted]
  for p in(a,b,c):
   self.indices.append(len(self.positions));self.positions.append(p);self.normals.append(normal)
   self.uvs.append((p[axes[0]]/256,p[axes[1]]/256))
 def quad(self,a,b,c,d):self.triangle(a,b,c);self.triangle(a,c,d)
 def solid(self,polygon,low,top):
  high=[(x,y,z)for(x,y),z in zip(polygon,top if isinstance(top,list)else[top]*len(polygon))]
  bottom=[(x,y,low)for x,y in polygon]
  for i in range(1,len(polygon)-1):
   self.triangle(high[0],high[i],high[i+1]);self.triangle(bottom[0],bottom[i+1],bottom[i])
  for i in range(len(polygon)):
   j=(i+1)%len(polygon);self.quad(bottom[i],bottom[j],high[j],high[i])

def rectangle(width,length,angle=0,centre=(0,0)):
 points=[(-width/2,-length/2),(width/2,-length/2),(width/2,length/2),(-width/2,length/2)]
 return [(centre[0]+x*math.cos(angle)-y*math.sin(angle),centre[1]+x*math.sin(angle)+y*math.cos(angle))for x,y in points]
def angular_distance(a,b):return abs((a-b+math.pi)%math.tau-math.pi)
def wedge(inner,outer,start,end):
 return[(inner*math.cos(start),inner*math.sin(start)),(outer*math.cos(start),outer*math.sin(start)),
        (outer*math.cos(end),outer*math.sin(end)),(inner*math.cos(end),inner*math.sin(end))]

def build_geometry():
 arrival=Mesh();arrival.solid(rectangle(512,512),-64,8)
 gate=(CENTRE[0]+3000*math.cos(GATE_ANGLE),CENTRE[1]+3000*math.sin(GATE_ANGLE))
 middle=((ENTRY[0]+gate[0])/2,(ENTRY[1]+gate[1])/2)
 delta=(gate[0]-ENTRY[0],gate[1]-ENTRY[1]);length=math.hypot(*delta)
 approach=Mesh();approach.solid(rectangle(length,720,math.atan2(delta[1],delta[0])),-64,8)
 arena=Mesh()
 # Filled disk with solid depth; no double-sided plane is used as a floor.
 disk=[(1900*math.cos(i*math.tau/SEGMENTS),1900*math.sin(i*math.tau/SEGMENTS))for i in range(SEGMENTS)]
 arena.solid(disk,-64,8)
 gate_half=math.asin(360/3000)
 sector_half=math.pi/SEGMENTS
 seating_gate_half=math.asin(360/1900)
 ramp_half=math.radians(7)
 seating_sectors=wall_sectors=0
 for i in range(SEGMENTS):
  a=i*math.tau/SEGMENTS;b=(i+1)*math.tau/SEGMENTS;angle=(a+b)/2
  is_gate=angular_distance(angle,GATE_ANGLE)<gate_half+sector_half
  is_seating_gate=angular_distance(angle,GATE_ANGLE)<seating_gate_half+sector_half
  is_ramp=angular_distance(angle,math.pi/2)<ramp_half
  if not is_seating_gate and not is_ramp:
   for terrace in range(8):
    arena.solid(wedge(1900+terrace*112.5,1900+(terrace+1)*112.5,a,b),-64,8+32*(terrace+1))
   seating_sectors+=1
  if not is_gate:
   top=1280 if math.sin(angle)>.55 else 736
   arena.solid(wedge(2800,3000,a,b),-64,top)
   wall_sectors+=1
 # Own four-sided sloped route,16degree incline, cut into the north seating.
 arena.solid([(-200,1900),(200,1900),(200,2800),(-200,2800)],-64,[8,8,264,264])
 cut_half=math.ceil(gate_half/(math.tau/SEGMENTS))*(math.tau/SEGMENTS)
 for direction_sign in(-1,1):
  angle=GATE_ANGLE+direction_sign*(cut_half+math.asin(150/2900))
  centre=(2900*math.cos(angle),2900*math.sin(angle))
  arena.solid(rectangle(240,300,angle,centre),-64,1120)
 placements=[{'id':IDS[0],'reference':0x101,'position':ENTRY,'rotationZ':0.,'coordinates':[65,-63]},
             {'id':IDS[1],'reference':0x102,'position':(*middle,320.),'rotationZ':0.,'coordinates':[65,-63]},
             {'id':IDS[2],'reference':0x103,'position':CENTRE,'rotationZ':0.,'coordinates':[66,-62]}]
 # Bind the representation actually stored in TES3, especially at large
 # world coordinates where float32 has a finite position resolution.
 for placement in placements:
  placement['position']=tuple(struct.unpack('<f',struct.pack('<f',v))[0]for v in placement['position'])
 return dict(zip(IDS,(arrival,approach,arena))),placements,{'wallSectors':wall_sectors,'seatingSectors':seating_sectors,
  'segments':SEGMENTS,'gateHalfAngle':gate_half,'snappedOuterOpeningWidth':6000*math.sin(cut_half),
  'rampSlopeDegrees':math.degrees(math.atan2(256,900)),
  'arrivalFootprint':[512,512],'arrivalNarrowingReason':'All four axis-aligned landing corners fit within the decoded flat-pad radius6200'}

def child(parent,tag,text=None,**attrs):
 item=ET.SubElement(parent,'{'+NS+'}'+tag,attrs)
 if text is not None:item.text=str(text)
 return item

def collada(path,mesh):
 doc=ET.Element('{'+NS+'}COLLADA',version='1.4.1');asset=child(doc,'asset')
 child(asset,'created','2026-10-03T00:00:00Z');child(asset,'modified','2026-10-03T00:00:00Z');child(asset,'up_axis','Z_UP')
 images=child(doc,'library_images');child(child(images,'image',id='stone-image'),'init_from','textures/veyra/frontier/frontier_stone.dds')
 effect=child(child(doc,'library_effects'),'effect',id='stone-effect');profile=child(effect,'profile_COMMON')
 child(child(child(profile,'newparam',sid='stone-surface'),'surface',type='2D'),'init_from','stone-image')
 child(child(child(profile,'newparam',sid='stone-sampler'),'sampler2D'),'source','stone-surface')
 phong=child(child(profile,'technique',sid='common'),'phong')
 child(child(phong,'emission'),'color','0 0 0 1');child(child(phong,'ambient'),'color','.55 .55 .55 1')
 child(child(phong,'diffuse'),'texture',texture='stone-sampler',texcoord='UVMap')
 child(child(phong,'specular'),'color','.025 .025 .025 1');child(child(phong,'shininess'),'float','8')
 child(child(child(doc,'library_materials'),'material',id='stone-material'),'instance_effect',url='#stone-effect')
 m=child(child(child(doc,'library_geometries'),'geometry',id='own-mesh'),'mesh')
 for suffix,values,axes in(('p',mesh.positions,'XYZ'),('n',mesh.normals,'XYZ'),('uv',mesh.uvs,'ST')):
  source=child(m,'source',id='own-'+suffix)
  child(source,'float_array',' '.join(format(v,'.9g')for row in values for v in row),id='own-'+suffix+'-array',count=str(len(values)*len(axes)))
  accessor=child(child(source,'technique_common'),'accessor',source='#own-'+suffix+'-array',count=str(len(values)),stride=str(len(axes)))
  for axis in axes:child(accessor,'param',name=axis,type='float')
 child(child(m,'vertices',id='own-vertices'),'input',semantic='POSITION',source='#own-p')
 triangles=child(m,'triangles',count=str(len(mesh.indices)//3),material='stone-slot')
 for offset,semantic,source in((0,'VERTEX','own-vertices'),(1,'NORMAL','own-n'),(2,'TEXCOORD','own-uv')):
  attrs={'semantic':semantic,'source':'#'+source,'offset':str(offset)}
  if semantic=='TEXCOORD':attrs['set']='0'
  child(triangles,'input',**attrs)
 child(triangles,'p',' '.join(str(i)+' '+str(i)+' '+str(i)for i in mesh.indices))
 scene=child(child(doc,'library_visual_scenes'),'visual_scene',id='Scene');node=child(scene,'node',id='own-solid-node')
 instance=child(node,'instance_geometry',url='#own-mesh')
 material=child(child(child(instance,'bind_material'),'technique_common'),'instance_material',symbol='stone-slot',target='#stone-material')
 child(material,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set='0')
 child(child(doc,'scene'),'instance_visual_scene',url='#Scene')
 path.parent.mkdir(parents=True,exist_ok=True);ET.ElementTree(doc).write(path,encoding='utf-8',xml_declaration=True)

def sub(kind,data):return struct.pack('<4sI',kind,len(data))+data
def record(kind,data):return struct.pack('<4sIII',kind,len(data),0,0)+data
def string(value):return value.encode('ascii')+b'\0'

def write_plugin(master,frontier,placements):
 bodies=[record(b'STAT',sub(b'NAME',string(rid))+sub(b'MODL',string('veyra/plaza/'+rid+'.dae')))for rid in IDS]
 for coordinate in((65,-63),(66,-62)):
  data=sub(b'NAME',string('LEVIATH Frontier Entry'if coordinate==(65,-63)else''))
  data+=sub(b'DATA',struct.pack('<Iii',2,*coordinate))+sub(b'RGNN',string('veyra_frontier_region'))
  for placement in placements:
   if tuple(placement['coordinates'])!=coordinate:continue
   data+=sub(b'FRMR',struct.pack('<I',placement['reference']))+sub(b'NAME',string(placement['id']))
   data+=sub(b'XSCL',struct.pack('<f',1.))+sub(b'DATA',struct.pack('<6f',*placement['position'],0.,0.,placement['rotationZ']))
  bodies.append(record(b'CELL',data))
 header=sub(b'HEDR',struct.pack('<fI32s256sI',1.3,0,b'LEVIATH Workshop',b'Own arrival approach arena; references only in owned Frontier cells',len(bodies)))
 for path,name in((master,'Morrowind.esm'),(frontier,'LEVIATH-Frontier.esp')):
  header+=sub(b'MAST',string(name))+sub(b'DATA',struct.pack('<Q',path.stat().st_size))
 (MOD/'LEVIATH-Plaza.esp').write_bytes(record(b'TES3',header)+b''.join(bodies))

def validate_geometry(meshes,placements):
 checks=[]
 for rid,mesh in meshes.items():
  assert len(mesh.positions)==len(mesh.normals)==len(mesh.uvs)==len(mesh.indices)
  assert all(math.isfinite(v)for row in mesh.positions+mesh.normals+mesh.uvs for v in row)
  assert all(abs(sum(v*v for v in n)-1)<1e-6 for n in mesh.normals)
  assert all(i==value for i,value in enumerate(mesh.indices))
  low=[min(p[i]for p in mesh.positions)for i in range(3)];high=[max(p[i]for p in mesh.positions)for i in range(3)]
  position=next(row['position']for row in placements if row['id']==rid)
  assert low[2]==-64 and high[2]<=1280
  assert all(math.hypot(position[0]+p[0]-CENTRE[0],position[1]+p[1]-CENTRE[1])<=6200 for p in mesh.positions)
  checks.append({'id':rid,'triangles':len(mesh.indices)//3,'vertices':len(mesh.positions),'localBounds':[low,high],
   'worldBounds':[[position[i]+point[i]for i in range(3)]for point in(low,high)]})
 assert len({p['reference']for p in placements})==3 and all(p['reference']>>24==0 for p in placements)
 return checks

def preview(meshes):
 image=Image.new('RGB',(1300,780),(23,31,36));draw=ImageDraw.Draw(image)
 draw.text((24,18),'OWN PLAZA GEOMETRY / SOUTHWEST AND TOP VIEWS / NOT ENGINE',fill=(237,235,222))
 mesh=meshes[IDS[2]]
 for mode in range(2):
  triangles=[]
  for index in range(0,len(mesh.indices),3):
   p=mesh.positions[index:index+3];normal=mesh.normals[index]
   if mode==0:
    projected=[((v[0]-v[1])*.7071068,(v[0]+v[1])*.3535534+v[2],(v[0]+v[1])*.7071068)for v in p]
   else:projected=[(v[0],v[1],v[2])for v in p]
   triangles.append((sum(v[2]for v in projected)/3,projected,normal))
  triangles.sort(key=lambda t:t[0],reverse=mode==0)
  for depth,projected,normal in triangles:
   brightness=.6+.35*max(0,normal[2])+ .08*normal[0]
   if mode==1:brightness*=.78+.22*min(1,max(0,depth)/1280)
   color=tuple(int(v*brightness)for v in(169,164,143))
   points=[(325+mode*650+v[0]*.085,(520 if mode==0 else 400)-v[1]*.085)for v in projected]
   draw.polygon(points,fill=color)
  draw.text((180+mode*650,724),'southwest elevation'if mode==0 else'top plan',fill=(190,201,202))
 image.save(BASE/'PLAZA_GEOMETRY_PREVIEW.png')

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-config',type=Path,required=True);args=parser.parse_args()
 frontier=FRONTIER/'mod/LEVIATH-Frontier.esp';entry=FRONTIER/'ENTRY.json';binder=FRONTIER/'build-frontier.py'
 if sha(frontier)!=FRONTIER_SHA or sha(entry)!=ENTRY_SHA or sha(binder)!=BINDER_SHA:raise ValueError('Frozen Frontier base differs')
 stone=BASE.parent/'frontier-texture-candidate/mod/Textures/veyra/frontier/frontier_stone.dds'
 if sha(stone)!=STONE_SHA:raise ValueError('Bound own stone material differs')
 # Read the frozen own module without creating __pycache__ inside its folder.
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('frontier_base_binder',binder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 master,snapshots,sources=module.bind_base(args.base_config,FRONTIER/'BASE_CONTENT_COLLISION_RECEIPT.json')
 for name,path in module.resolve_config(args.base_config)[0]:
  for kind,flags,data in module.records(path):
   if kind!=b'STAT':continue
   for key,value in module.subs(data):
    if key==b'NAME':
     if module.text(value).casefold()in IDS:raise ValueError('Own STAT namespace collision in '+name)
     break
 snapshots.update({frontier:FRONTIER_SHA,entry:ENTRY_SHA,binder:BINDER_SHA,stone:STONE_SHA})
 meshes,placements,layout=build_geometry();checks=validate_geometry(meshes,placements)
 MOD.mkdir(parents=True,exist_ok=True)
 for rid,mesh in meshes.items():collada(MOD/'Meshes/veyra/plaza'/(rid+'.dae'),mesh)
 write_plugin(master,frontier,placements);preview(meshes)
 if any(sha(p)!=digest for p,digest in snapshots.items()):raise ValueError('Source changed during build')
 manifest={'schema':'veyra.plaza-placement.v1','version':'0.1.0','frontierPluginSha256':FRONTIER_SHA,
  'frontierEntrySha256':ENTRY_SHA,'plugin':'LEVIATH-Plaza.esp','pluginSha256':sha(MOD/'LEVIATH-Plaza.esp'),
  'worldFloorZ':328,'worldModelOriginZ':320,'visibleGeometryBaseLocalZ':-64,'placements':placements,
  'placementPositionEncoding':'TES3_FLOAT32_ROUND_TO_NEAREST_BOUND_IN_MANIFEST',
  'materialDependency':{'path':'Textures/veyra/frontier/frontier_stone.dds','sha256':STONE_SHA,'source':'OWN_TEXTURE_CANDIDATE_MIT'},
  'collision':'PENDING_ROOT_NATIVE_RAY_AND_PLAYER_WALK','automaticTeleport':False,'networkEffects':0}
 (BASE/'PLACEMENTS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 receipt={'schema':'veyra.plaza-build.v1','version':'0.1.0','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'generatorSha256':sha(Path(__file__)),'binderSha256':BINDER_SHA,'baseConfigSha256':sha(args.base_config),
  'boundOriginalSources':sources,'frontierPluginSha256':FRONTIER_SHA,'entryManifestSha256':ENTRY_SHA,
  'recordCounts':{'TES3':1,'STAT':3,'CELL':2,'FRMR':3},'originalCellsChanged':0,'ownedFrontierCellsWithNewRefs':2,
  'geometryChecks':checks,'layout':layout,'sourceFilesUnchanged':len(snapshots),'profileChanges':0,
  'sourceLicense':'MIT','originalMeshesCopied':0,'generatedTextures':0,'nativeEngineStarted':False,
  'generatedHashes':{p.relative_to(MOD).as_posix():sha(p)for p in MOD.rglob('*')if p.is_file()},
  'placementManifestSha256':sha(BASE/'PLACEMENTS.json'),'previewSha256':sha(BASE/'PLAZA_GEOMETRY_PREVIEW.png'),
  'claimCeiling':'OWN_ADDON_MESH_AND_REFERENCE_STRUCTURE_NATIVE_PENDING'}
 (BASE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print('PLAZA_BUILD_PASS STAT3 ownedCELL2 uniqueRefs3 triangles',sum(row['triangles']for row in checks),'nativePENDING')

if __name__=='__main__':main()
