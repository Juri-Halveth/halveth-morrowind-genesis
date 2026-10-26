"""MIT. Deterministic owned skinned animal and animation timeline, no game geometry."""
from pathlib import Path
import hashlib,json,math,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
NS='http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('',NS)
def node(parent,tag,text=None,**attrs):
    n=ET.SubElement(parent,'{'+NS+'}'+tag,{k:str(v) for k,v in attrs.items()})
    if text is not None:n.text=str(text)
    return n
def numbers(values):return ' '.join(format(float(v),'.9g')for v in values)
def matrix(x=0,y=0,z=0,angle=0):
    c,s=math.cos(angle),math.sin(angle)
    # COLLADA serialized row-major affine matrix, not an OpenGL memory array.
    # Source binding: OpenMW exporter strmtx iterates matrix row then column.
    return [1,0,0,x,0,c,-s,y,0,s,c,z,0,0,0,1]
BONES=[('Bip01',None,(0,0,0)),('Torso','Bip01',(0,0,65)),
       ('Neck','Torso',(0,26,8)),('Head','Neck',(0,9,25)),('Tail','Torso',(0,-33,0))]
for label,x,y in [('FL',-14,26),('FR',14,26),('HL',-14,-26),('HR',14,-26)]:
    BONES.extend([(label+'_Upper','Bip01',(x,y,63)),(label+'_Lower',label+'_Upper',(0,0,-29))])
INDEX={b[0]:i for i,b in enumerate(BONES)}
REST={}
for name,parent,offset in BONES:
    base=REST.get(parent,(0,0,0));REST[name]=tuple(base[i]+offset[i] for i in range(3))
vertices=[];normals=[];joints=[];triangles=[]
def append_vertex(p,n,bone):
    i=len(vertices);vertices.append(p);normals.append(n);joints.append(INDEX[bone]);return i
def ellipsoid(centre,radii,bone,rings=8,segments=16):
    rows=[]
    for i in range(rings+1):
        theta=math.pi*i/rings;row=[]
        for j in range(segments):
            phi=math.tau*j/segments
            direction=(math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta))
            p=tuple(centre[k]+direction[k]*radii[k]for k in range(3))
            n=tuple(direction[k]/radii[k]for k in range(3));length=math.sqrt(sum(v*v for v in n))
            row.append(append_vertex(p,tuple(v/length for v in n),bone))
        rows.append(row)
    for i in range(rings):
        for j in range(segments):
            a,b,c,d=rows[i][j],rows[i][(j+1)%segments],rows[i+1][(j+1)%segments],rows[i+1][j]
            if i>0:triangles.append((a,d,b))
            if i<rings-1:triangles.append((b,d,c))
def tube(a,b,radius,bone,segments=8):
    delta=tuple(b[k]-a[k]for k in range(3));length=math.sqrt(sum(v*v for v in delta));axis=tuple(v/length for v in delta)
    helper=(0,0,1)if abs(axis[2])<.9 else(0,1,0)
    cross=lambda u,v:(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    side=cross(axis,helper);ln=math.sqrt(sum(v*v for v in side));side=tuple(v/ln for v in side);up=cross(axis,side)
    rows=[]
    for endpoint in (a,b):
        row=[]
        for j in range(segments):
            angle=math.tau*j/segments;n=tuple(side[k]*math.cos(angle)+up[k]*math.sin(angle)for k in range(3))
            row.append(append_vertex(tuple(endpoint[k]+radius*n[k]for k in range(3)),n,bone))
        rows.append(row)
    for j in range(segments):
        n=(j+1)%segments;triangles.extend([(rows[0][j],rows[0][n],rows[1][j]),(rows[0][n],rows[1][n],rows[1][j])])
def source(parent,id,values,stride,params,kind='float'):
    s=node(parent,'source',id=id);array_id=id+'-array'
    node(s,'Name_array'if kind=='Name'else'float_array',
         ' '.join(values)if kind=='Name'else numbers(values),id=array_id,count=len(values))
    acc=node(node(s,'technique_common'),'accessor',source='#'+array_id,count=len(values)//stride,stride=stride)
    for name,type in params:node(acc,'param',name=name,type=type)
    return s
ellipsoid((0,0,65),(21,37,16),'Torso',10,20)
ellipsoid((0,28,86),(10,11,20),'Neck')
ellipsoid((0,37,101),(10,16,8),'Head')
ellipsoid((0,48,97),(7,10,5),'Head',6,12)
for label,x,y in [('FL',-14,26),('FR',14,26),('HL',-14,-26),('HR',14,-26)]:
    ellipsoid((x,y,49),(4.5,5,15),label+'_Upper',6,12)
    ellipsoid((x,y,20),(3,3.6,15),label+'_Lower',6,12)
    ellipsoid((x,y+2,4),(4.5,6.5,3),label+'_Lower',4,12)
for sign in (-1,1):
    ellipsoid((sign*11,34,109),(4,7,2.5),'Head',4,10)
    a=(sign*6,40,108);b=(sign*17,40,131);tube(a,b,2,'Head')
    tube(b,(sign*24,44,140),1.4,'Head')
    tube((sign*11,40,118),(sign*21,30,129),1.2,'Head')
    tube((sign*14,40,125),(sign*7,46,135),1.1,'Head')
tube((0,-33,67),(0,-46,53),3,'Tail')
root=ET.Element('{'+NS+'}COLLADA',version='1.4.1')
asset=node(root,'asset');node(asset,'created','2026-10-03T00:00:00Z');node(asset,'modified','2026-10-03T00:00:00Z')
node(asset,'unit',name='engine_unit',meter=1);node(asset,'up_axis','Z_UP')
effects=node(root,'library_effects');effect=node(effects,'effect',id='animal-effect')
phong=node(node(node(effect,'profile_COMMON'),'technique',sid='common'),'phong')
for tag,color in [('emission','0.02 0.025 0.035 1'),('ambient','0.3 0.3 0.3 1'),('diffuse','0.33 0.48 0.52 1'),('specular','0.05 0.05 0.05 1')]:
    node(node(phong,tag),'color',color)
node(node(phong,'shininess'),'float',12)
materials=node(root,'library_materials');node(node(materials,'material',id='animal-material',name='Own muted blue grey hide'),'instance_effect',url='#animal-effect')
geometries=node(root,'library_geometries')
def write_geometry(id,vs,ns,ts):
    mesh=node(node(geometries,'geometry',id=id),'mesh')
    source(mesh,id+'-positions',[v for p in vs for v in p],3,[('X','float'),('Y','float'),('Z','float')])
    source(mesh,id+'-normals',[v for p in ns for v in p],3,[('X','float'),('Y','float'),('Z','float')])
    verts=node(mesh,'vertices',id=id+'-vertices');node(verts,'input',semantic='POSITION',source='#'+id+'-positions')
    t=node(mesh,'triangles',count=len(ts),material='body-material')
    node(t,'input',semantic='VERTEX',source='#'+id+'-vertices',offset=0);node(t,'input',semantic='NORMAL',source='#'+id+'-normals',offset=1)
    node(t,'p',' '.join(str(v)for triangle in ts for i in triangle for v in(i,i)))
write_geometry('animal-geometry',vertices,normals,triangles)
# Explicit nonrendered Collision child box, rather than animated model bounds.
box=[(x,y,z)for z in(0,114)for y in(-43,53)for x in(-22,22)]
box_ts=[(0,2,1),(1,2,3),(4,5,6),(5,7,6),(0,1,4),(1,5,4),(2,6,3),(3,6,7),(0,4,2),(2,4,6),(1,3,5),(3,7,5)]
write_geometry('collision-geometry',box,[(0,0,1)]*8,box_ts)
controllers=node(root,'library_controllers');skin=node(node(controllers,'controller',id='animal-skin'),'skin',source='#animal-geometry')
node(skin,'bind_shape_matrix',numbers(matrix()))
source(skin,'skin-joints',[b[0]for b in BONES],1,[('JOINT','Name')],'Name')
source(skin,'skin-bindposes',[v for name,_,_ in BONES for v in matrix(*tuple(-x for x in REST[name]))],16,[('TRANSFORM','float4x4')])
source(skin,'skin-weights',[1],1,[('WEIGHT','float')])
skin_joints=node(skin,'joints');node(skin_joints,'input',semantic='JOINT',source='#skin-joints');node(skin_joints,'input',semantic='INV_BIND_MATRIX',source='#skin-bindposes')
weights=node(skin,'vertex_weights',count=len(vertices));node(weights,'input',semantic='JOINT',source='#skin-joints',offset=0);node(weights,'input',semantic='WEIGHT',source='#skin-weights',offset=1)
node(weights,'vcount',' '.join('1'for _ in vertices));node(weights,'v',' '.join(str(v)for j in joints for v in(j,0)))
scenes=node(root,'library_visual_scenes');scene=node(scenes,'visual_scene',id='AnimalScene')
armature=node(scene,'node',id='Armature',name='Armature');bone_nodes={}
for name,parent,offset in BONES:
    bn=node(bone_nodes[parent]if parent else armature,'node',id=name,sid=name,name=name,type='JOINT')
    node(bn,'matrix',numbers(matrix(*offset)),sid='transform');bone_nodes[name]=bn
body=node(armature,'node',id='AnimalMesh',name='AnimalMesh')
ic=node(body,'instance_controller',url='#animal-skin');node(ic,'skeleton','#Bip01')
bindings=node(node(ic,'bind_material'),'technique_common');node(bindings,'instance_material',symbol='body-material',target='#animal-material')
collision=node(scene,'node',id='Collision',name='Collision');colmesh=node(collision,'node',id='CollisionMesh',name='CollisionMesh')
node(colmesh,'instance_geometry',url='#collision-geometry')
clips=[('idle',1,61),('walkforward',62,110),('runforward',111,135),('attack1',136,166),('hit1',167,179),
       ('death1',180,210),('knockdown',211,229),('knockout',230,260),('deathknockdown',261,291),('deathknockout',292,322)]
times=[];values={name:[]for name,_,_ in BONES};textkeys=[]
for group,first,last in clips:
    textkeys.extend([f'{group}: start {first/30:.9f}',f'{group}: stop {last/30:.9f}'])
    for frame in range(first,last+1):
        t=frame/30;u=(frame-first)/(last-first);times.append(t)
        for name,parent,offset in BONES:
            x,y,z=offset;angle=0
            if name=='Bip01' and group in('walkforward','runforward'):
                y=u*(140 if group=='walkforward' else 210)
            elif name=='Torso' and group in('walkforward','runforward'):
                z+=abs(math.sin(u*math.tau))*1.4
            elif name=='Torso' and group in('death1','knockout','knockdown','deathknockdown','deathknockout'):
                z-=42*min(1,u*1.4);angle=-1.15*min(1,u*1.4)
            elif name.startswith(('FL_','FR_','HL_','HR_')) and group in('walkforward','runforward'):
                phase=0 if name[:2]in('FL','HR')else math.pi
                amplitude=.44 if group=='walkforward'else.7
                angle=math.sin(u*math.tau+phase)*amplitude
                if name.endswith('Lower'):angle=-max(0,math.sin(u*math.tau+phase))*.65
            elif name=='Neck':
                angle=math.sin(u*math.tau)*(.3 if group=='attack1'else .045)
            elif name=='Head' and group=='hit1':angle=-math.sin(u*math.pi)*.3
            elif name=='Tail':angle=math.sin(u*math.tau)*.1
            values[name].extend(matrix(x,y,z,angle))
animations=node(root,'library_animations')
for name,_,_ in BONES:
    a=node(animations,'animation',id=name+'-animation',name=name+'-animation')
    source(a,name+'-time',times,1,[('TIME','float')]);source(a,name+'-output',values[name],16,[('TRANSFORM','float4x4')])
    source(a,name+'-interpolation',['LINEAR']*len(times),1,[('INTERPOLATION','Name')],'Name')
    sampler=node(a,'sampler',id=name+'-sampler')
    for semantic,ref in [('INPUT','time'),('OUTPUT','output'),('INTERPOLATION','interpolation')]:node(sampler,'input',semantic=semantic,source='#'+name+'-'+ref)
    node(a,'channel',source='#'+name+'-sampler',target=name+'/transform')
node(node(root,'scene'),'instance_visual_scene',url='#AnimalScene')
dest=ROOT/'mod/Meshes/veyra/creature';dest.mkdir(parents=True,exist_ok=True)
ET.indent(root);model=dest/'frontier_stag.dae';ET.ElementTree(root).write(model,encoding='utf-8',xml_declaration=True)
(dest/'frontier_stag.txt').write_text('\n'.join(textkeys)+'\n',encoding='utf-8',newline='\n')
data={'schema':'veyra.owned-creature-build.v1','version':'0.1.0','vertices':len(vertices),'triangles':len(triangles),
      'joints':len(BONES),'weightsPerVertex':1,'animationGroups':[c[0]for c in clips],'timelineSamples':len(times),
      'ownProceduralGeometry':True,'commercialAssetBytes':0,'modelBounds':[[min(p[k]for p in vertices)for k in range(3)],[max(p[k]for p in vertices)for k in range(3)]],
      'collisionBox':[[-22,-43,0],[22,53,114]],'nativeStatus':'NOT_RUN',
      'outputs':{p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in (model,dest/'frontier_stag.txt')}}
(ROOT/'BUILD_RECEIPT.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
print('OWN_SKINNED_CREATURE_BUILT',data['vertices'],data['triangles'],data['joints'],len(times))
