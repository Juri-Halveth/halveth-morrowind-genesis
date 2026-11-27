#!/usr/bin/env python3
"""MIT. Own dense broadleaf crown, no original class/CELL override."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,math,random,struct,sys
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw
import PIL
BASE=Path(__file__).resolve().parent
MOD=BASE/'mod'
RID='veyra_swamp_crown_01'
SEED=2026100351
KERNEL_SHA='19a1aae1b87e0555b747622dd11f3a7d6a13140623211e19b73bb964b5292c81'
MASTER_SHA='5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647'
BARK={'Textures/veyra/swamp_bark.dds':'76dabf30eb286fcd2cbb4f964aa45fcd2b4a63e53a4b2a611128828c20845e2d',
      'Textures/veyra/swamp_bark_n.dds':'33c12d7cb40671721fc22861fb45d1eb9ab8c7ab9beb8d4f659b3eedf139b722'}
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def kernel():
 path=BASE/'geometry-kernel.py'
 if sha(path)!=KERNEL_SHA:raise ValueError('Exact own geometry kernel differs')
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('veyra_crown_kernel',path)
 k=importlib.util.module_from_spec(spec);sys.modules[spec.name]=k;spec.loader.exec_module(k)
 return k

def broad_leaf(part,k,center,direction,length,width,tilt):
 direction=k.unit(direction);u,v=k.basis(direction)
 transverse=k.add(k.mul(u,math.cos(tilt)),k.mul(v,math.sin(tilt)))
 normal=k.unit(k.cross(transverse,direction))
 outline=[(0,0),(.5,.45),(0,1),(-.5,.45)]
 points=[k.add(center,k.add(k.mul(transverse,x*width),k.mul(direction,y*length)))for x,y in outline]
 ridge=k.add(center,k.add(k.mul(direction,length*.48),k.mul(normal,width*.11)))
 for i in range(4):
  j=(i+1)%4
  part.triangle(points[i],points[j],ridge,(outline[i][0]+.5,outline[i][1]),
                (outline[j][0]+.5,outline[j][1]),(.5,.48),double=True)

def geometry(k):
 rng=random.Random(SEED);wood=k.Part(0);leaves=k.Part(1)
 def stem(z):
  t=max(0,z)/1900
  return(88*math.sin(t*2.5)+78*t*t,36*math.sin(t*4.7)+114*t*t,z)
 trunk=[stem(-64+i*(1964/24))for i in range(25)]
 radii=[90*(1-i/24)**1.31+.38 for i in range(25)]
 wood.tube(trunk,radii,18)
 for i in range(7):
  angle=i*math.tau/7+rng.uniform(-.12,.12)
  path=[(math.cos(angle)*r,math.sin(angle)*r,z)for r,z in((12,155),(70,65),(148,-28),(210,-63))]
  wood.tube(path,[29,24,13,2],7)
 clusters=[];branch_info=[]
 for i in range(8):
  angle=i*2.3999632297+.21
  height=580+i*126;origin=stem(height)
  reach=(635-i*20)+rng.uniform(-40,60)
  end=(origin[0]+math.cos(angle)*reach,origin[1]+math.sin(angle)*reach,
       1110+(i%4)*184+rng.uniform(-30,60))
  path=[]
  for j in range(10):
   t=j/9;point=k.add(k.mul(origin,1-t),k.mul(end,t))
   point=k.add(point,(-math.sin(angle)*62*math.sin(t*math.pi),
                     math.cos(angle)*62*math.sin(t*math.pi),95*math.sin(t*math.pi)))
   path.append(point)
  wood.tube(path,[36*(1-j/9)**1.27+.65 for j in range(10)],10)
  branch_info.append({'originHeight':height,'azimuth':angle,'endpoint':end})
  for j in range(4):
   a=angle+(j-1.5)*.36
   start=path[3+j];length=rng.uniform(130,220)
   centre_source=path[4] if j==0 else path[6] if j==1 else end
   reach=70 if j==0 else 95 if j==1 else length
   tip=k.add(centre_source,(math.cos(a)*reach,math.sin(a)*reach,(j-1.5)*58+rng.uniform(-25,40)))
   middle=k.add(k.mul(start,.48),k.mul(tip,.52));middle=k.add(middle,(0,0,37))
   wood.tube([start,k.add(k.mul(start,.6),k.mul(middle,.4)),middle,k.add(k.mul(middle,.4),k.mul(tip,.6)),tip],
             [12,9,6,3,.4],6)
   clusters.append({'centre':tip,'radius':[rng.uniform(160,210),rng.uniform(145,205),rng.uniform(135,185)],'role':'OUTER_LOBE'})
 for height in(1260,1500,1730,1920):
  clusters.append({'centre':stem(height),'radius':[225,195,190],'role':'STEM_AND_TIP_COVER'})
 count=0
 for cluster in clusters:
  center=cluster['centre'];rx,ry,rz=cluster['radius']
  for _ in range(83):
   angle=rng.uniform(0,math.tau);z=rng.uniform(-1,1);radial=math.sqrt(1-z*z);r=rng.random()**(1/3)
   position=k.add(center,(math.cos(angle)*radial*rx*r,math.sin(angle)*radial*ry*r,z*rz*r))
   direction=(math.cos(angle)*.78,math.sin(angle)*.78,rng.uniform(-.72,.45))
   broad_leaf(leaves,k,position,direction,rng.uniform(78,115),rng.uniform(45,74),rng.uniform(0,math.tau));count+=1
 return[wood,leaves],branch_info,clusters,count,trunk[-1],radii[-1]

def leaf_texture(k):
 image=Image.new('RGB',(256,256));pixels=image.load();rng=random.Random(SEED+9)
 for y in range(256):
  for x in range(256):
   ridge=math.exp(-((x-128)/4.4)**2)*8
   edge=-7*(abs(x-128)/128)**1.4
   grain=rng.uniform(-2.2,2.2)
   pixels[x,y]=(int(70+ridge*.65+edge*.8+grain),int(108+ridge+edge+grain),int(44+ridge*.4+edge*.5+grain))
 folder=MOD/'Textures/veyra';folder.mkdir(parents=True,exist_ok=True)
 path=folder/'crown_leaf_01.dds';k.dds(image,path)
 return path

def write_mesh(k,parts,path):
 k.collada(path,parts)
 doc=ET.parse(path)
 # Only the own new leaf path/material changes. Existing bark bindings stay.
 doc.find("c:library_images/c:image[@id='m1-image']/c:init_from",NS).text='textures/veyra/crown_leaf_01.dds'
 phong=doc.find("c:library_effects/c:effect[@id='m1-effect']/c:profile_COMMON/c:technique/c:phong",NS)
 phong.find('c:emission/c:color',NS).text='.025 .035 .015 1'
 phong.find('c:ambient/c:color',NS).text='.65 .72 .55 1'
 phong.find('c:specular/c:color',NS).text='.008 .008 .008 1'
 phong.find('c:shininess/c:float',NS).text='2'
 doc.write(path,encoding='utf-8',xml_declaration=True)

def bind_master(master,k):
 if sha(master)!=MASTER_SHA:raise ValueError('Bound master differs')
 for kind,data in k.records(master):
  if kind==b'STAT':
   rid=next((value.rstrip(b'\0').decode('cp1252')for key,value in k.subrecords(data)if key==b'NAME'),'')
   if rid.casefold()==RID:raise ValueError('New own STAT collides with master')

def plugin(k,master):
 body=k.record(b'STAT',k.subrecord(b'NAME',k.string(RID))+k.subrecord(b'MODL',k.string('veyra/'+RID+'.dae')))
 header=k.subrecord(b'HEDR',struct.pack('<fI32s256sI',1.3,0,b'LEVIATH Workshop',b'Own dense crown candidate, no class or cell override',1))
 header+=k.subrecord(b'MAST',k.string('Morrowind.esm'))+k.subrecord(b'DATA',struct.pack('<Q',master.stat().st_size))
 path=MOD/'Veyra-Dense-Crown.esp';path.write_bytes(k.record(b'TES3',header)+body);return path

def verify(parts):
 all_positions=[p for part in parts for p in part.positions]
 for part in parts:
  assert len(part.positions)==len(part.normals)==len(part.uvs)
  assert len(part.indices)%3==0 and all(0<=i<len(part.positions)for i in part.indices)
  assert all(math.isfinite(v)for row in part.positions+part.normals+part.uvs for v in row)
  assert all(abs(sum(v*v for v in normal)-1)<1e-6 for normal in part.normals)
 bounds=[[min(v[i]for v in all_positions)for i in range(3)],[max(v[i]for v in all_positions)for i in range(3)]]
 triangles=[len(part.indices)//3 for part in parts]
 assert sum(triangles)<=30000 and -72<bounds[0][2]<0 and 1900<bounds[1][2]<2350
 return{'bounds':bounds,'triangles':triangles,'totalTriangles':sum(triangles),'vertices':[len(p.positions)for p in parts]}

def preview(parts):
 image=Image.new('RGB',(1920,1120),(228,232,223));draw=ImageDraw.Draw(image)
 draw.text((24,16),'OWN DENSE-CROWN GEOMETRY / THREE AZIMUTHS AND TOP / NOT ENGINE',fill=(30,44,33))
 metrics=[]
 for panel,angle in enumerate((0,math.pi/2,math.pi*.75)):
  triangles=[];mask=Image.new('1',(600,620));mdraw=ImageDraw.Draw(mask)
  for part in parts:
   for index in range(0,len(part.indices),3):
    points=[part.positions[j]for j in part.indices[index:index+3]]
    points=[(p[0]*math.cos(angle)+p[1]*math.sin(angle),p[2],-p[0]*math.sin(angle)+p[1]*math.cos(angle))for p in points]
    triangles.append((sum(p[2]for p in points)/3,points,part.material))
  for depth,points,material in sorted(triangles,key=lambda t:t[0]):
   screen=[(320+panel*640+p[0]*.25,655-p[1]*.25)for p in points]
   draw.polygon(screen,fill=(90,72,51)if material==0 else(65,102,43))
   if material==1:mdraw.polygon([(p[0]*.25+300,580-p[1]*.25)for p in points],fill=1)
  bounds=mask.getbbox();cropped=mask.crop(bounds);occupancy=sum(cropped.get_flattened_data())/(cropped.width*cropped.height)
  metrics.append({'azimuth':angle,'leafProjectedBoundingBoxPixels':bounds,'leafOccupancyWithinOwnProjectedBox':occupancy})
  draw.text((panel*640+28,702),'view '+str(panel+1)+' / projected leaf occupancy '+format(occupancy,'.1%'),fill=(31,44,34))
 for part in parts:
  for index in range(0,len(part.indices),3):
   points=[part.positions[j]for j in part.indices[index:index+3]]
   if part.material==1:draw.polygon([(318+p[0]*.20,927-p[1]*.20)for p in points],fill=(65,102,43))
 draw.text((620,830),'CONTINUOUS CURVED STEM / TIP RADIUS 0.38',fill=(31,44,34))
 draw.text((620,867),'8 primary branches /32 twigs /36 irregular overlapping lobes',fill=(31,44,34))
 draw.text((620,904),'2,988 broader folded leaves /explicit backfaces',fill=(31,44,34))
 draw.text((620,941),'Origin at ground0; roots buried64; no inherited -500 tree offset',fill=(31,44,34))
 draw.text((620,978),'Own brighter leaf material; unchanged bound CC0 bark dependency',fill=(31,44,34))
 draw.text((620,1015),'Native shading, anchor and performance remain a coordinated test',fill=(31,44,34))
 image.save(BASE/'CROWN_PREVIEW.png');return metrics

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--master',type=Path,required=True);parser.add_argument('--materials-mod',type=Path,required=True);args=parser.parse_args()
 k=kernel();bind_master(args.master,k);snapshots={args.master:MASTER_SHA}
 for name,digest in BARK.items():
  path=args.materials_mod/name
  if sha(path)!=digest:raise ValueError('CC0 bark dependency differs')
  snapshots[path]=digest
 (MOD/'Meshes/veyra').mkdir(parents=True,exist_ok=True)
 parts,branches,clusters,leaves,tip,radius=geometry(k);checks=verify(parts);leaf=leaf_texture(k)
 mesh=MOD/'Meshes/veyra'/(RID+'.dae');write_mesh(k,parts,mesh);esp=plugin(k,args.master);metrics=preview(parts)
 assert all(sha(path)==digest for path,digest in snapshots.items())
 manifest={'schema':'veyra.dense-crown-placement.v1','version':'0.1.0','recordId':RID,'model':'veyra/'+RID+'.dae',
  'plugin':'Veyra-Dense-Crown.esp','pluginSha256':sha(esp),'modelSha256':sha(mesh),
  'modelOriginLocalZ':0,'suggestedWorldOrigin':'ACTUAL_TERRAIN_HEIGHT','tree500OffsetRequired':False,
  'nominalRootCentreDepth':64,'actualGeometryMinimumLocalZ':checks['bounds'][0][2],
  'nativePlacement':'PENDING_ROOT_SPAWN','classOverrides':0,'cellReferences':0}
 (BASE/'PLACEMENT.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 receipt={'schema':'veyra.dense-crown-build.v1','version':'0.1.0','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'seed':SEED,'generatorSha256':sha(Path(__file__)),'geometryKernelSha256':KERNEL_SHA,
  'runtime':{'python':sys.version.split()[0],'pillow':PIL.__version__},'checks':checks,
  'primaryBranches':branches,'leafClusters':clusters,'individualLeaves':leaves,'foldedLeafTrianglesIncludingBackfaces':8,
  'stemTip':{'position':tip,'radius':radius,'coverClusterCentre':clusters[-1]['centre']},
  'projectedLeafRasterMetrics':metrics,'recordCounts':{'TES3':1,'STAT':1,'CELL':0},
  'materialDependencies':BARK,'materialFilesCopied':0,'newOwnLeafTexture':{'path':leaf.relative_to(MOD).as_posix(),'sha256':sha(leaf),'license':'MIT'},
  'sourceMasterSha256':MASTER_SHA,'sourceInputsUnchanged':len(snapshots),'existingClassesChanged':0,'profileChanges':0,
  'generatedHashes':{p.relative_to(MOD).as_posix():sha(p)for p in MOD.rglob('*')if p.is_file()},
  'placementManifestSha256':sha(BASE/'PLACEMENT.json'),'previewSha256':sha(BASE/'CROWN_PREVIEW.png'),
  'nativeEngineStarted':False,'nativeAppearanceCollisionPerformance':'PENDING_ROOT_PROBE',
  'claimCeiling':'OWN_CROWN_GEOMETRY_AND_DECLARED_RASTER_OCCUPANCY_ONLY'}
 (BASE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print('CROWN_BUILD_PASS',checks['totalTriangles'],'triangles;',leaves,'leaves; ownSTAT1 CELL0 nativePENDING')

if __name__=='__main__':main()
