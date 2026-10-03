"""MIT. Independent serialized COLLADA/animation validation and own pose preview."""
from pathlib import Path
import xml.etree.ElementTree as ET
import math, hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parent
MODEL=ROOT/'mod/Meshes/veyra/creature/frontier_stag.dae'
TEXT=MODEL.with_suffix('.txt')
N={'c':'http://www.collada.org/2005/11/COLLADASchema'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def floats(s):return [float(v)for v in s.split()]
doc=ET.parse(MODEL)
checks=[]
def check(name, condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
ids={e.get('id'):e for e in doc.iter() if e.get('id')}
check('UNIQUE_IDS',len(ids)==sum(bool(e.get('id'))for e in doc.iter()))
def source(id):
    e=ids[id];a=e.find('c:float_array',N)
    if a is None:a=e.find('c:Name_array',N)
    vals=a.text.split();acc=e.find('c:technique_common/c:accessor',N)
    check('SOURCE_'+id,int(a.get('count'))==len(vals) and int(acc.get('count'))*int(acc.get('stride'))==len(vals))
    return vals,int(acc.get('stride'))
pos_raw,stride=source('animal-geometry-positions');norm_raw,_=source('animal-geometry-normals')
pos=[tuple(map(float,pos_raw[i:i+3]))for i in range(0,len(pos_raw),3)]
norm=[tuple(map(float,norm_raw[i:i+3]))for i in range(0,len(norm_raw),3)]
check('FINITE_POSITIONS',all(math.isfinite(v)for p in pos for v in p))
check('UNIT_NORMALS',len(pos)==len(norm) and all(abs(sum(v*v for v in n)-1)<1e-6 for n in norm))
tri_e=ids['animal-geometry'].find('c:mesh/c:triangles',N)
indices=list(map(int,tri_e.find('c:p',N).text.split()))
check('TRIANGLE_INDEX_COUNTS',len(indices)==int(tri_e.get('count'))*6 and all(0<=i<len(pos)for i in indices))
check('POSITION_NORMAL_INDEX_PAIRS',all(indices[i]==indices[i+1]for i in range(0,len(indices),2)))
tris=[tuple(indices[i+j]for j in (0,2,4))for i in range(0,len(indices),6)]
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
areas=[]
for t in tris:
    a,b,c=(pos[i]for i in t);n=cross(tuple(b[k]-a[k]for k in range(3)),tuple(c[k]-a[k]for k in range(3)))
    areas.append(math.sqrt(sum(v*v for v in n)))
check('NONDEGENERATE_TRIANGLES',min(areas)>1e-7)
names,_=source('skin-joints');bind_raw,stride=source('skin-bindposes');weights,_=source('skin-weights')
bind=[list(map(float,bind_raw[i:i+16]))for i in range(0,len(bind_raw),16)]
skin=ids['animal-skin'].find('c:skin',N);vweights=skin.find('c:vertex_weights',N)
vcount=list(map(int,vweights.find('c:vcount',N).text.split()));joints=list(map(int,vweights.find('c:v',N).text.split()))
check('SINGLE_WEIGHT_WITHIN_ENGINE_LIMIT',len(vcount)==len(pos) and all(v==1 for v in vcount) and len(joints)==len(pos)*2 and weights==['1'])
check('VALID_WEIGHT_JOINT_INDICES',all(0<=joints[i]<len(names) and joints[i+1]==0 for i in range(0,len(joints),2)))
scene=ids['AnimalScene'];joint_elems=scene.findall('.//c:node[@type="JOINT"]',N)
parents={child:parent for parent in scene.iter()for child in parent}
root_joints=[e for e in joint_elems if parents[e].get('type')!='JOINT']
check('ONE_BIP01_ROOT',len(root_joints)==1 and root_joints[0].get('name')=='Bip01')
check('EXACT_CONTROLLER_JOINTS',set(names)=={e.get('sid')for e in joint_elems} and len(names)==13)
check('COLLISION_CHILD_BOX',ids['Collision'].find('c:node/c:instance_geometry',N).get('url')=='#collision-geometry')
check('SKIN_SKELETON_BINDING',ids['AnimalMesh'].find('c:instance_controller/c:skeleton',N).text=='#Bip01' and parents[ids['AnimalMesh']].get('id')=='Armature')
def mul(a,b):return [sum(a[r*4+k]*b[k*4+c]for k in range(4))for r in range(4)for c in range(4)]
identity=[float(i//4==i%4)for i in range(16)]
rest_world={}
for e in joint_elems:
    name=e.get('sid');local=floats(e.find('c:matrix',N).text);parent=parents[e].get('sid')
    rest_world[name]=mul(rest_world[parent],local)if parent in rest_world else local
for i,name in enumerate(names):check('INVERSE_REST_'+name,max(abs(a-b)for a,b in zip(mul(rest_world[name],bind[i]),identity))<1e-6)
times=None;animations={}
for name in names:
    t,_=source(name+'-time');out,st=source(name+'-output');interp,_=source(name+'-interpolation');t=list(map(float,t))
    if times is None:times=t
    check('ANIMATION_'+name,len(t)==322 and t==times and all(t[i]<t[i+1]for i in range(len(t)-1)) and st==16 and interp==['LINEAR']*322)
    mats=[list(map(float,out[i:i+16]))for i in range(0,len(out),16)]
    check('AFFINE_ANIMATION_'+name,all(all(math.isfinite(v)for v in m) and m[12:]==[0,0,0,1]for m in mats))
    channel=ids[name+'-animation'].find('c:channel',N)
    check('CHANNEL_BINDING_'+name,channel.get('target')==name+'/transform')
    animations[name]=mats
keys={}
for line in TEXT.read_text().splitlines():
    group,kind,time=line.replace(':','').split();keys.setdefault(group,{})[kind]=float(time)
check('TEN_COMPLETE_TEXTKEY_GROUPS',len(keys)==10 and all(set(v)=={'start','stop'} and v['start']<v['stop']for v in keys.values()))
for group,amount in [('walkforward',140),('runforward',210)]:
    start=min(range(len(times)),key=lambda i:abs(times[i]-keys[group]['start']))
    stop=min(range(len(times)),key=lambda i:abs(times[i]-keys[group]['stop']))
    check('ROOT_MOTION_'+group,abs(animations['Bip01'][stop][7]-animations['Bip01'][start][7]-amount)<1e-5)
before={p.name:sha(p)for p in (MODEL,TEXT)}
subprocess.run([sys.executable,str(ROOT/'build-creature.py')],check=True,capture_output=True)
check('DETERMINISTIC_REBUILD',before=={p.name:sha(p)for p in (MODEL,TEXT)})
preview=None
try:
    from PIL import Image,ImageDraw
    im=Image.new('RGB',(1200,500),(16,23,30));draw=ImageDraw.Draw(im)
    for panel,(label,frame) in enumerate([('rest / idle',1),('walking / 1-4 cycle',74),('walking / 3-4 cycle',98),('attack',151)]):
        world={};transformed=[]
        for e in joint_elems:
            name=e.get('sid');parent=parents[e].get('sid');local=animations[name][frame-1]
            world[name]=mul(world[parent],local)if parent in world else local
        transforms=[mul(world[name],bind[i])for i,name in enumerate(names)]
        root_y=animations['Bip01'][frame-1][7]
        for i,p in enumerate(pos):
            m=transforms[joints[2*i]];v=[p[0],p[1],p[2],1]
            q=[sum(m[r*4+k]*v[k]for k in range(4))for r in range(3)];q[1]-=root_y
            transformed.append((panel*300+150+q[1]*1.7+q[0]*.5,360-q[2]*1.7+q[0]*.2))
        for tri in tris:draw.polygon([transformed[i]for i in tri],fill=(77,117,126),outline=(96,142,150))
        draw.text((panel*300+10,28),label,fill=(235,240,246))
    preview=ROOT/'OWN_POSE_PREVIEW.png';im.save(preview)
except ImportError:pass
receipt={'schema':'veyra.owned-creature-serialized-checks.v1','status':'SERIALIZED_MODEL_AND_TIMELINE_PASS','checks':checks,'checkCount':len(checks),'sourceSha256':sha(MODEL),'textkeysSha256':sha(TEXT),'previewSha256':sha(preview)if preview else None,'native':'NOT_RUN','claimCeiling':'SERIALIZED_STRUCTURE_AND_OWN_CPU_SKINNING_PREVIEW_NOT_ENGINE_RUNTIME'}
(ROOT/'STATIC_CHECKS.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(receipt['status'],len(checks))
