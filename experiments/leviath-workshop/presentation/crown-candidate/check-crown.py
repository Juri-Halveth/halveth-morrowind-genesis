#!/usr/bin/env python3
"""MIT. Independently decode the dense-crown model/STAT/leaf DDS."""
from pathlib import Path
import argparse,datetime,hashlib,json,math,struct,subprocess,sys
import xml.etree.ElementTree as ET
from PIL import Image
BASE=Path(__file__).resolve().parent
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def records(data):
 result=[];cursor=0
 while cursor<len(data):
  kind,size,unknown,flags=struct.unpack_from('<4sIII',data,cursor);cursor+=16
  assert unknown==flags==0 and cursor+size<=len(data)
  result.append((kind,data[cursor:cursor+size]));cursor+=size
 assert cursor==len(data);return result
def subs(data):
 result=[];cursor=0
 while cursor<len(data):
  kind,size=struct.unpack_from('<4sI',data,cursor);cursor+=8
  assert cursor+size<=len(data);result.append((kind,data[cursor:cursor+size]));cursor+=size
 assert cursor==len(data);return result

def check_model(path,build):
 doc=ET.parse(path);assert doc.getroot().get('version')=='1.4.1'
 assert doc.findtext('c:asset/c:up_axis',namespaces=NS)=='Z_UP'
 textures={image.findtext('c:init_from',namespaces=NS)for image in doc.findall('c:library_images/c:image',NS)}
 assert textures=={'textures/veyra/swamp_bark.dds','textures/veyra/crown_leaf_01.dds'}
 geometries=doc.findall('c:library_geometries/c:geometry',NS);assert len(geometries)==2
 results=[];total=0;all_positions=[]
 for number,geometry in enumerate(geometries):
  mesh=geometry.find('c:mesh',NS);arrays={}
  for source in mesh.findall('c:source',NS):
   array=source.find('c:float_array',NS);accessor=source.find('c:technique_common/c:accessor',NS)
   values=[float(v)for v in array.text.split()];stride=int(accessor.get('stride'))
   assert len(values)==int(array.get('count'))==int(accessor.get('count'))*stride
   assert all(math.isfinite(v)for v in values)
   arrays[source.get('id')]=[tuple(values[i:i+stride])for i in range(0,len(values),stride)]
  prefix='g'+str(number);positions=arrays[prefix+'p'];normals=arrays[prefix+'n'];uvs=arrays[prefix+'uv']
  assert len(positions)==len(normals)==len(uvs)
  assert all(abs(sum(v*v for v in normal)-1)<2e-6 for normal in normals)
  triangles=mesh.find('c:triangles',NS);count=int(triangles.get('count'));total+=count
  indices=[int(v)for v in triangles.findtext('c:p',namespaces=NS).split()]
  assert len(indices)==count*9 and count==build['checks']['triangles'][number]
  assert all(0<=value<len(positions)for value in indices)
  decoded=[]
  for i in range(0,len(indices),9):
   points=[positions[indices[i+j]]for j in(0,3,6)]
   a=[points[1][k]-points[0][k]for k in range(3)];b=[points[2][k]-points[0][k]for k in range(3)]
   cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
   assert sum(v*v for v in cross)>1e-8,'Serialized degenerate triangle'
   decoded.append(points)
  if number==1:
   assert count==build['individualLeaves']*8 and count%2==0
   for i in range(0,count,2):
    assert decoded[i]==list(reversed(decoded[i+1])),'Leaf backface does not reverse its paired triangle'
  all_positions.extend(positions);results.append({'geometry':number,'triangles':count,'vertices':len(positions),
                                                'explicitLeafBackfaces':'PASS'if number==1 else'NOT_LEAF_GEOMETRY'})
 assert total==build['checks']['totalTriangles']and 26000<=total<=29000
 bounds=[[min(p[i]for p in all_positions)for i in range(3)],[max(p[i]for p in all_positions)for i in range(3)]]
 assert all(abs(a-b)<.001 for current,expected in zip(bounds,build['checks']['bounds'])for a,b in zip(current,expected))
 assert build['stemTip']['radius']<.5 and len(build['leafClusters'])==36 and len(build['primaryBranches'])==8
 tip=build['stemTip']['position'];cluster=build['leafClusters'][-1]
 assert sum(((tip[i]-cluster['centre'][i])/cluster['radius'][i])**2 for i in range(3))<1,'Tapered tip outside planned crown lobe'
 return{'geometry':results,'totalTriangles':total,'bounds':bounds,'tipInsideTopCrownLobe':'STRUCTURE_PASS'}

def check_plugin(path,master):
 rr=records(path.read_bytes());assert [kind for kind,_ in rr]==[b'TES3',b'STAT']
 hh=subs(rr[0][1]);assert [kind for kind,_ in hh]==[b'HEDR',b'MAST',b'DATA']
 assert hh[0][1][:4].hex()=='6666a63f'and struct.unpack_from('<I',hh[0][1],296)[0]==1
 assert hh[1][1]==b'Morrowind.esm\0'and struct.unpack('<Q',hh[2][1])[0]==master.stat().st_size
 ss=subs(rr[1][1]);assert ss==[(b'NAME',b'veyra_swamp_crown_01\0'),(b'MODL',b'veyra/veyra_swamp_crown_01.dae\0')]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--master',type=Path,required=True);parser.add_argument('--materials-mod',type=Path,required=True);parser.add_argument('--esmtool',type=Path,required=True);args=parser.parse_args()
 build=json.loads((BASE/'BUILD_RECEIPT.json').read_text());placement=json.loads((BASE/'PLACEMENT.json').read_text())
 assert sha(BASE/'build-crown.py')==build['generatorSha256']and sha(args.master)==build['sourceMasterSha256']
 assert sha(BASE/'geometry-kernel.py')==build['geometryKernelSha256']
 for name,digest in build['materialDependencies'].items():assert sha(args.materials_mod/name)==digest
 expected={'Veyra-Dense-Crown.esp','Meshes/veyra/veyra_swamp_crown_01.dae','Textures/veyra/crown_leaf_01.dds'}
 actual={p.relative_to(BASE/'mod').as_posix()for p in (BASE/'mod').rglob('*')if p.is_file()};assert actual==expected
 model=BASE/'mod/Meshes/veyra/veyra_swamp_crown_01.dae';mesh_check=check_model(model,build)
 plugin=BASE/'mod/Veyra-Dense-Crown.esp';check_plugin(plugin,args.master)
 assert sha(plugin)==placement['pluginSha256']and sha(model)==placement['modelSha256']
 assert placement['modelOriginLocalZ']==0 and placement['tree500OffsetRequired']is False
 dds=BASE/'mod/Textures/veyra/crown_leaf_01.dds';data=dds.read_bytes()
 assert data[:4]==b'DDS 'and data[84:88]==b'DXT1'and struct.unpack_from('<II',data,12)==(256,256)
 assert struct.unpack_from('<I',data,28)[0]==9 and len(data)==128+sum(max(1,(256//2**i+3)//4)**2*8 for i in range(9))
 image=Image.open(dds);assert image.size==(256,256)and image.mode=='RGBA'and image.getextrema()[3]==(255,255)
 first={p.relative_to(BASE).as_posix():sha(p)for p in (BASE/'mod').rglob('*')if p.is_file()}
 for name in('PLACEMENT.json','CROWN_PREVIEW.png'):first[name]=sha(BASE/name)
 result=subprocess.run([sys.executable,str(BASE/'build-crown.py'),'--master',str(args.master),'--materials-mod',str(args.materials_mod)],
                       capture_output=True,text=True,timeout=90)
 assert result.returncode==0,result.stdout+result.stderr
 second={p.relative_to(BASE).as_posix():sha(p)for p in (BASE/'mod').rglob('*')if p.is_file()}
 for name in('PLACEMENT.json','CROWN_PREVIEW.png'):second[name]=sha(BASE/name)
 assert first==second,'Repeat crown bytes differ'
 binding=json.loads((BASE.parent/'frontier-candidate/PARSER_BINDING.json').read_text());assert sha(args.esmtool)==binding['toolSha256']
 native=subprocess.run([str(args.esmtool),'-q','-C','dump',str(plugin)],capture_output=True,text=True,timeout=60)
 assert native.returncode==0,native.stdout+native.stderr
 receipt={'schema':'veyra.dense-crown-check.v1','version':'0.1.0','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'status':'SERIALIZED_CROWN_STAT_DDS_REPEAT_PASS_NATIVE_PENDING','checkerSha256':sha(Path(__file__)),
  'generatorSha256':sha(BASE/'build-crown.py'),'modelChecks':mesh_check,'repeatOutputHashes':second,
  'textureDdsMips':9,'newSTATCount':1,'classOverrides':0,'CELLCount':0,
  'nativeFileParser':{'toolSha256':sha(args.esmtool),'exitCode':native.returncode},
  'nativeEngineStarted':False,'nativeAppearanceCollisionPerformance':'PENDING_ROOT_PROBE',
  'claimCeiling':'OWN_STRUCTURE_AND_BYTE_EQUALITY_ONLY'}
 (BASE/'CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
 print('CROWN_CHECK_PASS triangles',mesh_check['totalTriangles'],'leafBackfaces mip9 repeat5 STAT1 CELL0 ESMToolPASS nativePENDING')

if __name__=='__main__':main()
