"""MIT. Own bounded scenery, vertex-bound to frozen Frontier LAND; no engine."""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, math, random, shutil, struct, sys
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).resolve().parent; MOD=BASE/'mod'; SEED=2026100368
F_SHA='7484682d663d62a22dfe59c01d3dbce862a2e1897f66e1b563b5b455cb2a75ad'
C_SHA='e6aebdbcd627357cbc5fec6a2e4bc0b7d2ca90da7fd5cde9af257dd0dd1f7665'
C_MODEL_SHA='8fb613ab60740892f33c4094f817a45098e1fc9d12c9c873b5ba9b596a51c683'
K_SHA='19a1aae1b87e0555b747622dd11f3a7d6a13140623211e19b73bb964b5292c81'
F_BUILDER_SHA='300202c2d19493c715effe737fc6f08443512140993697706eab0747f9eef298'
CENTRE=(540672,-507904); ENTRY=(536576,-512000)
PATH=[(CENTRE[0]+x,CENTRE[1]+y)for x,y in[(-3712,512),(-4864,1536),(-5248,2304),(-4736,3456),(-3584,4480)]]
RID_TREE='veyra_swamp_crown_01'; RID_ROCK='veyra_frontier_stone_cluster_01'; RID_GRASS='veyra_frontier_grass_01'
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f32=lambda n:struct.unpack('<f',struct.pack('<f',n))[0]

def module(path,digest,name):
    if sha(path)!=digest:raise ValueError('Source module digest differs: '+path.name)
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def records(data):
    pos=0
    while pos<len(data):
        if pos+16>len(data):raise ValueError('Truncated record')
        kind,n,unknown,flags=struct.unpack_from('<4sIII',data,pos);pos+=16
        body=data[pos:pos+n]
        if len(body)!=n:raise ValueError('Truncated body')
        pos+=n;yield kind,body

def subs(data):
    pos=0
    while pos<len(data):
        if pos+8>len(data):raise ValueError('Truncated subrecord')
        kind,n=struct.unpack_from('<4sI',data,pos);pos+=8
        body=data[pos:pos+n]
        if len(body)!=n:raise ValueError('Truncated subrecord body')
        pos+=n;yield kind,body

def terrain(plugin):
    heights={};tiles={};cells={}
    for kind,body in records(plugin.read_bytes()):
        s=dict(subs(body))
        if kind==b'CELL':
            flags,x,y=struct.unpack('<Iii',s[b'DATA']);assert flags==2
            cells[(x,y)]=body
        if kind!=b'LAND':continue
        x,y=struct.unpack('<ii',s[b'INTV']); raw=s[b'VHGT'];assert len(raw)==4232
        offset=struct.unpack_from('<f',raw)[0];assert offset==int(offset)
        delta=struct.unpack_from('<4225b',raw,4);first=int(offset);grid=[]
        for row in range(65):
            first+=delta[row*65];v=first;line=[v*8]
            for d in delta[row*65+1:row*65+65]:v+=d;line.append(v*8)
            grid.append(line)
            for col,h in enumerate(line):
                key=(x*8192+col*128,y*8192+row*128)
                if key in heights:assert heights[key]==h
                heights[key]=h
        tiles[(x,y)]={'grid':grid,'vhgtSha256':hashlib.sha256(raw).hexdigest()}
    assert len(tiles)==len(cells)==16 and len(heights)==66049
    return heights,tiles,cells

def segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def path_distance(p):return min(segment_distance(p,a,b)for a,b in zip(PATH,PATH[1:]))

def crown_bounds(path):
    d=ET.parse(path);points=[]
    for source in d.findall('.//c:source',NS):
        if source.get('id')not in('g0p','g1p'):continue
        values=list(map(float,source.find('c:float_array',NS).text.split()))
        points.extend(tuple(values[i:i+3])for i in range(0,len(values),3))
    low=max(math.hypot(x,y)for x,y,z in points if z<=400)
    canopy=max(math.hypot(x,y)for x,y,z in points)
    return {'lowBelowLocal400Radius':low,'maximumHorizontalRadius':canopy,
        'sourcePoints':len(points),'minimumLocalZ':min(p[2]for p in points)}

def reservations(p,foot,full):
    # Arena uses the full crown envelope. Roads reserve low collider footprint.
    values={
        'arenaFullEnvelope':math.dist(p,CENTRE)-(3100+full),
        'entryTownlifeFullEnvelope':math.dist(p,ENTRY)-(2600+full),
        'approachLowFootprint':segment_distance(p,ENTRY,
            (CENTRE[0]-3000/math.sqrt(2),CENTRE[1]-3000/math.sqrt(2)))-(360+foot+128),
        'forestPathLowFootprint':path_distance(p)-(600+foot+128),
        'northRampLowFootprint':segment_distance(p,(CENTRE[0],CENTRE[1]+1700),
            (CENTRE[0],CENTRE[1]+3100))-(350+foot+128),
        'constructionFixtureLowFootprint':math.dist(p,(536100,-512000))-(1000+foot),
    }
    return values

def anchor(p,heights,tiles,patch=256,max_delta=64):
    x,y=p;gx,gy=x//8192,y//8192
    if (gx,gy)!=(65,-62)or p not in heights:return None
    sample=[heights.get((x+dx,y+dy))for dx in range(-patch,patch+1,128)for dy in range(-patch,patch+1,128)]
    if any(h is None or h<40 for h in sample):return None
    if max(sample)-min(sample)>max_delta:return None
    return {'coordinates':[gx,gy],'vertex':[(x-gx*8192)//128,(y-gy*8192)//128],
        'height':heights[p],'patchHalfExtent':patch,'patchMinimum':min(sample),'patchMaximum':max(sample),
        'vhgtSha256':tiles[(gx,gy)]['vhgtSha256']}

def choose(heights,tiles,bounds,prop_radii):
    rng=random.Random(SEED)
    candidates=[(CENTRE[0]+x,CENTRE[1]+y)for x in range(-8064,-2047,128)for y in range(256,7169,128)]
    rng.shuffle(candidates);rows=[]
    for p in candidates:
        scale=f32(rng.uniform(.80,1.08));foot=bounds['lowBelowLocal400Radius']*scale
        margins=reservations(p,foot,bounds['maximumHorizontalRadius']*scale)
        proof=anchor(p,heights,tiles)
        if min(margins.values())<0 or not proof:continue
        if proof['height']-proof['patchMinimum']>50*scale:continue
        if any(math.dist(p,row['position'][:2])<1024 for row in rows):continue
        rows.append({'kind':'tree','recordId':RID_TREE,'position':[f32(p[0]),f32(p[1]),f32(proof['height'])],
            'scale':scale,'rotationZ':f32(rng.uniform(0,math.tau)),'anchor':proof,'freeMargins':margins,
            'lowFootprintRadius':foot,'fullEnvelopeRadius':bounds['maximumHorizontalRadius']*scale})
        if len(rows)==20:break
    if len(rows)!=20:raise ValueError('Bounded scene cannot fit 20 trees under these reservations')
    occupied={tuple(r['position'][:2])for r in rows}
    for kind,rid,target,max_delta in [('stone',RID_ROCK,20,32),('grass',RID_GRASS,28,0)]:
        foot=prop_radii[rid]*1.05+16
        choices=candidates.copy();rng.shuffle(choices);count=0
        for p in choices:
            if p in occupied:continue
            margins=reservations(p,foot,foot)
            proof=anchor(p,heights,tiles,patch=256,max_delta=max_delta)
            if min(margins.values())<0 or not proof:continue
            # Populate the same wooded banks, rather than isolated noise over all cells.
            if min(math.dist(p,r['position'][:2])for r in rows if r['kind']=='tree')>1000:continue
            rows.append({'kind':kind,'recordId':rid,'position':[f32(p[0]),f32(p[1]),f32(proof['height'])],
                'scale':f32(rng.uniform(.75,1.05)),'rotationZ':f32(rng.uniform(0,math.tau)),
                'anchor':proof,'freeMargins':margins,'lowFootprintRadius':foot,'fullEnvelopeRadius':foot})
            occupied.add(p);count+=1
            if count==target:break
        if count!=target:raise ValueError('Prop budget cannot fit under exact reservations')
    for i,row in enumerate(rows):row['reference']=0x501+i
    assert len(rows)==68 and len({r['reference']for r in rows})==68
    return rows

def meshes(k):
    rng=random.Random(SEED+1);rock=k.Part(0);grass=k.Part(1)
    for centre,rad in[((0,0,15),(135,105,80)),((130,40,-4),(75,65,58)),((-110,60,-10),(60,48,40))]:
        rings=[];n=14;lat=7
        for i in range(1,lat):
            theta=math.pi*i/lat;ring=[]
            for j in range(n):
                a=math.tau*j/n;w=1+rng.uniform(-.10,.10)
                ring.append((centre[0]+rad[0]*math.sin(theta)*math.cos(a)*w,
                    centre[1]+rad[1]*math.sin(theta)*math.sin(a)*w,centre[2]+rad[2]*math.cos(theta)))
            rings.append(ring)
        top=(centre[0],centre[1],centre[2]+rad[2]);bottom=(centre[0],centre[1],centre[2]-rad[2])
        def tri(a,b,c):rock.triangle(a,b,c,(a[0]/200,a[1]/200),(b[0]/200,b[1]/200),(c[0]/200,c[1]/200))
        for j in range(n):
            nxt=(j+1)%n;tri(top,rings[0][j],rings[0][nxt]);tri(bottom,rings[-1][nxt],rings[-1][j])
            for upper,lower in zip(rings,rings[1:]):
                tri(upper[j],lower[j],lower[nxt]);tri(upper[j],lower[nxt],upper[nxt])
    for _ in range(24):
        angle=rng.uniform(0,math.tau);x=rng.uniform(-115,115);y=rng.uniform(-115,115)
        height=rng.uniform(85,150);width=rng.uniform(7,15);lean=rng.uniform(15,45)
        axis=(math.cos(angle),math.sin(angle));side=(-axis[1],axis[0]);rows=[]
        for t in(0,.34,.70,1):
            cx=x+axis[0]*lean*t*t;cy=y+axis[1]*lean*t*t;w=width*(1-t)**.65
            rows.append(((cx-side[0]*w,cy-side[1]*w,-3+height*t),
                (cx+side[0]*w,cy+side[1]*w,-3+height*t)))
        for i in range(3):
            a,b=rows[i];c,d=rows[i+1]
            grass.triangle(a,b,d,(0,i/3),(1,i/3),(1,(i+1)/3),double=True)
            if i<2:grass.triangle(a,d,c,(0,i/3),(1,(i+1)/3),(0,(i+1)/3),double=True)
    return {RID_ROCK:rock,RID_GRASS:grass}

def write_mesh(k,part,path):
    k.collada(path,[part]);d=ET.parse(path)
    d.find("c:library_images/c:image[@id='m0-image']/c:init_from",NS).text='textures/veyra/frontier/frontier_stone.dds'
    d.find("c:library_images/c:image[@id='m1-image']/c:init_from",NS).text='textures/veyra/crown_leaf_01.dds'
    for effect in d.findall('c:library_effects/c:effect',NS):
        p=effect.find('c:profile_COMMON/c:technique/c:phong',NS)
        p.find('c:specular/c:color',NS).text='.008 .008 .008 1';p.find('c:shininess/c:float',NS).text='2'
    d.write(path,encoding='utf-8',xml_declaration=True)

def plugin(k,masters,cells,rows):
    bodies=[]
    for rid in(RID_ROCK,RID_GRASS):
        bodies.append(k.record(b'STAT',k.subrecord(b'NAME',k.string(rid))+
            k.subrecord(b'MODL',k.string('veyra/frontier_scenery/'+rid+'.dae'))))
    body=cells[(65,-62)]
    for row in rows:
        body+=k.subrecord(b'FRMR',struct.pack('<I',row['reference']))+k.subrecord(b'NAME',k.string(row['recordId']))
        body+=k.subrecord(b'XSCL',struct.pack('<f',row['scale']))
        body+=k.subrecord(b'DATA',struct.pack('<6f',*row['position'],0,0,row['rotationZ']))
    bodies.append(k.record(b'CELL',body))
    header=k.subrecord(b'HEDR',struct.pack('<fI32s256sI',1.3,0,b'LEVIATH Workshop',
        b'Own bounded forest scenery; own Frontier cell only, no terrain changes',len(bodies)))
    for name,path in masters:
        header+=k.subrecord(b'MAST',k.string(name))+k.subrecord(b'DATA',struct.pack('<Q',path.stat().st_size))
    target=MOD/'LEVIATH-Frontier-Scenery.esp';target.write_bytes(k.record(b'TES3',header)+b''.join(bodies));return target

def preview(rows,heights):
    im=Image.new('RGB',(1500,1380),(235,235,225));d=ImageDraw.Draw(im);d.font=ImageFont.load_default(size=18)
    def point(p):return(160+(p[0]-CENTRE[0]+10000)*.07,100+(8500-(p[1]-CENTRE[1]))*.07)
    d.text((24,18),'OWN FRONTIER SCENERY / TERRAIN-VERTEX PLAN / NOT ENGINE',fill=(35,50,38))
    for x in range(CENTRE[0]-9600,CENTRE[0]+4097,256):
        for y in range(CENTRE[1]-5120,CENTRE[1]+8193,256):
            h=heights.get((x,y),-2048);p=point((x,y))
            color=(91,132,155)if h<0 else(187,194+min(22,h//24),143)
            d.rectangle((p[0],p[1]-18,p[0]+18,p[1]),fill=color)
    def circle(p,r,color,outline):
        x,y=point(p);d.ellipse((x-r*.07,y-r*.07,x+r*.07,y+r*.07),fill=color,outline=outline,width=2)
    circle(CENTRE,3100,(220,213,194),(134,119,100));circle(ENTRY,2600,None,(142,91,115))
    d.line([point(p)for p in PATH],fill=(229,220,190),width=84)
    d.line([point(p)for p in PATH],fill=(156,137,112),width=3)
    for r in rows:
        p=r['position'];color={'tree':(48,94,47),'stone':(99,106,111),'grass':(109,143,63)}[r['kind']]
        radius={'tree':230,'stone':85,'grass':45}[r['kind']];circle(p,radius,color,color)
        if r['kind']=='tree':
            x,y=point(p);d.text((x+20,y-12),str(r['reference']-0x500),fill=(23,60,25))
    for i,p in enumerate(PATH):
        x,y=point(p);d.text((x+10,y+10),'P'+str(i+1),fill=(45,45,34))
    d.text((30,1210),'20 own Crown refs /20 own stone clusters /28 own grass groups /one owned CELL(65,-62)',fill=(32,50,38))
    d.text((30,1240),'Reserved: arena+canopy envelope /entry-townlife /approach /north ramp /construction fixture',fill=(32,50,38))
    d.text((30,1270),'Forest route:600 half-width + measured low collider +128 margin; crowns above it remain native QA',fill=(32,50,38))
    d.text((30,1300),'Encoded height and diagram are static evidence; walking, shading, collision and frametime pending',fill=(32,50,38))
    im.save(BASE/'SCENERY_PREVIEW.png')

def main():
    p=argparse.ArgumentParser();p.add_argument('--base-config',type=Path,required=True)
    p.add_argument('--frontier-directory',type=Path,required=True);p.add_argument('--crown-directory',type=Path,required=True)
    p.add_argument('--plaza-directory',type=Path,required=True);p.add_argument('--townlife-binding',type=Path,required=True)
    p.add_argument('--portal-binding',type=Path,required=True);p.add_argument('--construction-config',type=Path,required=True)
    p.add_argument('--construction-probe',type=Path,required=True);p.add_argument('--texture-directory',type=Path,required=True)
    a=p.parse_args();frontier=a.frontier_directory/'mod/LEVIATH-Frontier.esp';crown=a.crown_directory/'mod/Veyra-Dense-Crown.esp'
    crown_model=a.crown_directory/'mod/Meshes/veyra/veyra_swamp_crown_01.dae'
    assert sha(frontier)==F_SHA and sha(crown)==C_SHA and sha(crown_model)==C_MODEL_SHA
    k=module(BASE/'geometry-kernel.py',K_SHA,'veyra_scenery_kernel')
    fb=module(a.frontier_directory/'build-frontier.py',F_BUILDER_SHA,'veyra_scenery_frontier_binding')
    master,snapshots,source_rows=fb.bind_base(a.base_config,a.frontier_directory/'BASE_CONTENT_COLLISION_RECEIPT.json')
    for name,path in fb.resolve_config(a.base_config)[0]:
        for kind,flags,body in fb.records(path):
            if kind==b'TES3':continue
            for key,value in fb.subs(body):
                if key==b'NAME'and fb.text(value).casefold()in(RID_ROCK,RID_GRASS):
                    raise ValueError('Own new ID already present in bound base: '+name)
    deps=[frontier,crown,crown_model,a.crown_directory/'PLACEMENT.json',a.plaza_directory/'PLACEMENTS.json',
        a.townlife_binding,a.portal_binding,a.construction_config,a.construction_probe,
        a.texture_directory/'mod/Textures/veyra/frontier/frontier_stone.dds',
        a.crown_directory/'mod/Textures/veyra/crown_leaf_01.dds']
    snapshots.update({path:sha(path)for path in deps})
    assert sha(deps[-2])=='d54f2025d173e9ade36d1e011c20b0f2e4667e2afe353013a5f05cff1b0bad31'
    assert sha(deps[-1])=='81b760ed106f75ba542f053e5a892082cf1d9f84604bf7fba711925c4b36283f'
    town=json.loads(a.townlife_binding.read_text(encoding='utf-8'))
    assert town['config']['entry']['x']==ENTRY[0]and town['config']['entry']['y']==ENTRY[1]
    assert town['config']['entry']['radius']==2200
    heights,tiles,cells=terrain(frontier);bounds=crown_bounds(crown_model);parts=meshes(k)
    prop_radii={rid:max(math.hypot(v[0],v[1])for v in part.positions)for rid,part in parts.items()}
    rows=choose(heights,tiles,bounds,prop_radii)
    folder=MOD/'Meshes/veyra/frontier_scenery';folder.mkdir(parents=True,exist_ok=True)
    geometry={}
    for rid,part in parts.items():
        target=folder/(rid+'.dae');write_mesh(k,part,target)
        geometry[rid]={'triangles':len(part.indices)//3,'vertices':len(part.positions),'sha256':sha(target),
            'bounds':[[min(q[i]for q in part.positions)for i in range(3)],[max(q[i]for q in part.positions)for i in range(3)]]}
    esp=plugin(k,[('Morrowind.esm',master),('LEVIATH-Frontier.esp',frontier),('Veyra-Dense-Crown.esp',crown)],cells,rows)
    samples=[]
    for i,(start,end)in enumerate(zip(PATH,PATH[1:])):
        steps=math.ceil(math.dist(start,end)/128)
        for j in range(steps+1):
            t=j/steps;point=tuple(round((start[n]*(1-t)+end[n]*t)/128)*128 for n in(0,1))
            proof=anchor(point,heights,tiles,patch=128,max_delta=64)
            assert proof and min(heights[(point[0]+dx,point[1]+dy)]for dx in(-512,0,512)for dy in(-512,0,512))>40
            samples.append({'segment':i,'position':[point[0],point[1],proof['height']], 'anchor':proof})
    assert all(sha(path)==digest for path,digest in snapshots.items())
    manifest={'schema':'veyra.frontier-scenery.v1','version':'0.1.0','seed':SEED,'referenceBudget':128,
        'counts':{'tree':20,'stone':20,'grass':28,'totalReferences':68,'ownSTAT':2,'CELL':1},
        'plugin':esp.name,'pluginSha256':sha(esp),'coordinates':[65,-62],
        'terrainGrid':{'step':128,'heightQuantum':8,'sharedGlobalVertices':len(heights),'inputPluginSha256':F_SHA},
        'crownGeometryEnvelope':bounds,'references':rows,'forestPath':{'halfWidth':600,'extraClearance':128,
            'controlPoints':PATH,'gridVertexSamples':samples,'nativeWalk':'PENDING'},
        'reservations':{'arenaFullCanopyRadius':3100,'entryTownlifeFullCanopyRadius':2600,
            'townlifeActualRadius':2200,'northRampHalfWidth':350,'constructionFixtureRadius':1000,
            'approachHalfWidth':360,'dynamicFutureBeds':'Not globally excluded; current reserved build zone remains free'},
        'geometry':geometry,'sourceContent':source_rows,
        'ownDependencies':[{'role':q.name,'sha256':snapshots[q],'bytes':q.stat().st_size}for q in deps],
        'newLAND':0,'originalCELLOverrides':0,'ownFrontierCELLReferenceAddition':1,'copiedOriginalMeshes':0,
        'downloads':0,'profileChanges':0,'networkEffects':0,'nativeRenderingCollisionFrametime':'PENDING_ROOT_PROBE'}
    (BASE/'SCENERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    preview(rows,heights)
    receipt={'schema':'veyra.frontier-scenery-build.v1','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generatorSha256':sha(Path(__file__)),'kernelSha256':K_SHA,'inputSourcesUnchanged':len(snapshots),
        'boundBaseContentIdsScanned':len(source_rows),'manifestSha256':sha(BASE/'SCENERY_MANIFEST.json'),
        'sourceChecksOnly':True,'newFilesNative':'PENDING_ROOT_PROBE'}
    (BASE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'SCENERY_BUILT_STATIC_68_NATIVE_PENDING','pluginSha256':sha(esp),
        'treeZRange':[min(r['position'][2]for r in rows if r['kind']=='tree'),max(r['position'][2]for r in rows if r['kind']=='tree')],
        'geometry':geometry,'minimumFreeMargin':min(min(r['freeMargins'].values())for r in rows)},indent=2))

if __name__=='__main__':main()
