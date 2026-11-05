#!/usr/bin/env python3
"""MIT. Decode actual COLLADA/TES3 mesh and own-placement structure."""
from pathlib import Path
from collections import Counter
import argparse,datetime,hashlib,json,math,struct,subprocess,sys
import xml.etree.ElementTree as ET
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
def text(data):
 assert data[-1]==0 and 0 not in data[:-1];return data[:-1].decode('ascii')
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def check_mesh(path,row):
 doc=ET.parse(path);assert doc.getroot().get('version')=='1.4.1'
 assert doc.findtext('c:asset/c:up_axis',namespaces=NS)=='Z_UP'
 image=doc.findtext('c:library_images/c:image/c:init_from',namespaces=NS)
 assert image=='textures/veyra/frontier/frontier_stone.dds'
 mesh=doc.find('c:library_geometries/c:geometry/c:mesh',NS);assert mesh is not None
 arrays={}
 for source in mesh.findall('c:source',NS):
  array=source.find('c:float_array',NS);accessor=source.find('c:technique_common/c:accessor',NS)
  values=[float(v)for v in array.text.split()];stride=int(accessor.get('stride'))
  assert len(values)==int(array.get('count'))==int(accessor.get('count'))*stride
  assert all(math.isfinite(v)for v in values)
  arrays[source.get('id')]=[tuple(values[i:i+stride])for i in range(0,len(values),stride)]
 positions=arrays['own-p'];normals=arrays['own-n'];uvs=arrays['own-uv']
 assert len(positions)==len(normals)==len(uvs)
 low=[min(v[i]for v in positions)for i in range(3)];high=[max(v[i]for v in positions)for i in range(3)]
 assert all(abs(a-b)<1e-4 for current,expected in zip((low,high),row['localBounds'])for a,b in zip(current,expected))
 triangles=mesh.find('c:triangles',NS);count=int(triangles.get('count'))
 indices=[int(i)for i in triangles.findtext('c:p',namespaces=NS).split()]
 assert len(indices)==count*9 and count==row['triangles']
 assert len(triangles.findall('c:input',NS))==3
 upward=vertical=downward=0
 for i in range(0,len(indices),9):
  corners=[indices[i+j:i+j+3]for j in(0,3,6)]
  assert all(0<=p<len(positions)and 0<=n<len(normals)and 0<=uv<len(uvs)for p,n,uv in corners)
  p=[positions[c[0]]for c in corners];n=[normals[c[1]]for c in corners]
  a=tuple(p[1][k]-p[0][k]for k in range(3));b=tuple(p[2][k]-p[0][k]for k in range(3));normal=cross(a,b)
  length=math.sqrt(sum(v*v for v in normal));assert length>1e-3
  normalized=tuple(v/length for v in normal)
  assert all(abs(sum(v*v for v in item)-1)<1e-6 for item in n)
  assert all(sum(x*y for x,y in zip(normalized,item))>.99999 for item in n)
  if normalized[2]>.5:upward+=1
  elif normalized[2]<-.5:downward+=1
  else:vertical+=1
 assert upward and downward and vertical
 # Solid primitive faces must be paired as undirected geometric edges.
 # At shared primitive borders the count can be4rather than2; odd counts
 # would indicate an open face boundary in this exact generated geometry.
 edges=Counter()
 for i in range(0,len(indices),9):
  vertices=[positions[indices[i+j]]for j in(0,3,6)]
  for a,b in zip(vertices,vertices[1:]+vertices[:1]):edges[tuple(sorted((a,b)))]+=1
 assert all(value%2==0 for value in edges.values()), 'Open primitive face boundary'
 return {'triangles':count,'upwardTriangles':upward,'downwardTriangles':downward,'verticalTriangles':vertical,
         'geometricEdgeParity':'EVEN_ALL_EDGES','sha256':sha(path),'bounds':[low,high]}

def check_plugin(path,build,placements):
 rr=records(path.read_bytes());assert Counter(k for k,_ in rr)=={b'TES3':1,b'STAT':3,b'CELL':2}
 hh=subs(rr[0][1]);assert [k for k,_ in hh]==[b'HEDR',b'MAST',b'DATA',b'MAST',b'DATA']
 assert hh[0][1][:4].hex()=='6666a63f' and struct.unpack_from('<I',hh[0][1],296)[0]==5
 assert [text(hh[i][1])for i in(1,3)]==['Morrowind.esm','LEVIATH-Frontier.esp']
 master=next(r for r in build['boundOriginalSources']if r['content']=='Morrowind.esm')
 assert struct.unpack('<Q',hh[2][1])[0]==master['bytes']
 assert struct.unpack('<Q',hh[4][1])[0]==(BASE.parent/'frontier-candidate/mod/LEVIATH-Frontier.esp').stat().st_size
 own_ids={p['id']for p in placements['placements']};stats=set();refs=[];cell_coordinates=[]
 for kind,body in rr[1:]:
  ss=subs(body)
  if kind==b'STAT':
   assert [k for k,_ in ss]==[b'NAME',b'MODL'];rid=text(ss[0][1]);assert rid in own_ids and rid not in stats
   assert text(ss[1][1])=='veyra/plaza/'+rid+'.dae';stats.add(rid)
  else:
   assert [k for k,_ in ss[:3]]==[b'NAME',b'DATA',b'RGNN']
   flags,x,y=struct.unpack('<Iii',ss[1][1]);assert flags==2 and(x,y)in((65,-63),(66,-62))
   assert text(ss[0][1])==('LEVIATH Frontier Entry'if(x,y)==(65,-63)else'')
   assert text(ss[2][1])=='veyra_frontier_region';cell_coordinates.append((x,y))
   for cursor in range(3,len(ss),4):
    group=ss[cursor:cursor+4];assert [k for k,_ in group]==[b'FRMR',b'NAME',b'XSCL',b'DATA']
    ref=struct.unpack('<I',group[0][1])[0];rid=text(group[1][1]);scale=struct.unpack('<f',group[2][1])[0]
    transform=struct.unpack('<6f',group[3][1]);assert ref>>24==0 and scale==1.
    p=next(p for p in placements['placements']if p['id']==rid)
    assert ref==p['reference']and[x,y]==p['coordinates']
    assert list(transform[:3])==p['position']and transform[3:]==(0.,0.,p['rotationZ'])
    assert [math.floor(transform[0]/8192),math.floor(transform[1]/8192)]==[x,y]
    refs.append(ref)
 assert stats==own_ids and len(refs)==len(set(refs))==3 and len(set(cell_coordinates))==2
 return {'recordCounts':{'TES3':1,'STAT':3,'CELL':2},'uniqueNewReferences':refs,'ownedCells':cell_coordinates,'sha256':sha(path)}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base-config',type=Path,required=True);parser.add_argument('--esmtool',type=Path,required=True);args=parser.parse_args()
 build=json.loads((BASE/'BUILD_RECEIPT.json').read_text());placements=json.loads((BASE/'PLACEMENTS.json').read_text())
 assert sha(BASE/'build-plaza.py')==build['generatorSha256']and sha(BASE/'PLACEMENTS.json')==build['placementManifestSha256']
 assert sha(args.base_config)==build['baseConfigSha256']
 mesh_checks={row['id']:check_mesh(BASE/'mod/Meshes/veyra/plaza'/(row['id']+'.dae'),row)for row in build['geometryChecks']}
 plugin=BASE/'mod/LEVIATH-Plaza.esp';plugin_check=check_plugin(plugin,build,placements)
 assert sha(plugin)==placements['pluginSha256']
 first={p.relative_to(BASE).as_posix():sha(p)for p in (BASE/'mod').rglob('*')if p.is_file()}
 for name in('PLACEMENTS.json','PLAZA_GEOMETRY_PREVIEW.png'):first[name]=sha(BASE/name)
 process=subprocess.run([sys.executable,str(BASE/'build-plaza.py'),'--base-config',str(args.base_config)],capture_output=True,text=True,timeout=90)
 assert process.returncode==0,process.stdout+process.stderr
 second={p.relative_to(BASE).as_posix():sha(p)for p in (BASE/'mod').rglob('*')if p.is_file()}
 for name in('PLACEMENTS.json','PLAZA_GEOMETRY_PREVIEW.png'):second[name]=sha(BASE/name)
 assert first==second,'Own mesh/reference rebuild bytes differ'
 binding=json.loads((BASE.parent/'frontier-candidate/PARSER_BINDING.json').read_text());assert sha(args.esmtool)==binding['toolSha256']
 native=subprocess.run([str(args.esmtool),'-q','-C','dump',str(plugin)],capture_output=True,text=True,timeout=60)
 assert native.returncode==0,native.stdout+native.stderr
 result={'schema':'veyra.plaza-check.v1','version':'0.1.0','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'status':'OWN_COLLADA_REFERENCE_AND_NATIVE_RECORD_PARSER_PASS_WORLD_PENDING',
  'checkerSha256':sha(Path(__file__)),'generatorSha256':sha(BASE/'build-plaza.py'),
  'meshChecks':mesh_checks,'pluginCheck':plugin_check,'repeatOutputHashes':second,
  'nativeFileParser':{'sha256':sha(args.esmtool),'exitCode':native.returncode,'formatVersion':'ESMTool1.3','loadCells':True},
  'nativeEngineStarted':False,'nativeCollisionAndWalk':'PENDING_ROOT_PROBE',
  'claimCeiling':'OWN_SOLID_MESH_AND_ADDON_PLACEMENT_STRUCTURE_ONLY'}
 (BASE/'CHECK_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print('PLAZA_CHECK_PASS threeCOLLADA fiveBodyRecords uniqueRefs3 repeatOutputs6 ESMToolPASS worldPENDING')

if __name__=='__main__':main()
