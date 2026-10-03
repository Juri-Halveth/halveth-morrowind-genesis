"""Own deterministic swamp-tree geometry and a narrowly scoped TES3 candidate.

Code/geometry: MIT. Bark input: Poly Haven Bark Brown 02, Rob Tuytel, CC0.
No original game meshes/textures are copied into the generated mod.
"""
from pathlib import Path
from dataclasses import dataclass, field
import argparse
import hashlib
import io
import json
import math
import random
import struct
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
MOD = ROOT / 'mod'
SEED = 20261003
NS = 'http://www.collada.org/2005/11/COLLADASchema'
ET.register_namespace('', NS)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def mul(a, s):
    return tuple(x*s for x in a)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def unit(a):
    length = math.sqrt(sum(x*x for x in a))
    if length < 1e-9:
        raise ValueError('degenerate direction')
    return mul(a, 1/length)


def basis(tangent):
    tangent = unit(tangent)
    reference = (0, 0, 1) if abs(tangent[2]) < .94 else (0, 1, 0)
    u = unit(cross(reference, tangent))
    return u, unit(cross(tangent, u))


@dataclass
class Part:
    material: int
    positions: list = field(default_factory=list)
    normals: list = field(default_factory=list)
    uvs: list = field(default_factory=list)
    indices: list = field(default_factory=list)

    def triangle(self, a, b, c, ua, ub, uc, double=False):
        normal = unit(cross(sub(b, a), sub(c, a)))
        for p, uv in zip((a, b, c), (ua, ub, uc)):
            self.indices.append(len(self.positions))
            self.positions.append(p)
            self.normals.append(normal)
            self.uvs.append(uv)
        if double:
            for p, uv in zip((c, b, a), (uc, ub, ua)):
                self.indices.append(len(self.positions))
                self.positions.append(p)
                self.normals.append(mul(normal, -1))
                self.uvs.append(uv)

    def tube(self, path, radii, sides):
        rings = []
        traveled = 0
        for i, center in enumerate(path):
            tangent = sub(path[min(len(path)-1, i+1)], path[max(0, i-1)])
            u, v = basis(tangent)
            if i:
                traveled += math.sqrt(sum(x*x for x in sub(path[i], path[i-1])))
            ring = []
            for j in range(sides+1):
                angle = j*math.tau/sides
                radial = add(mul(u, math.cos(angle)), mul(v, math.sin(angle)))
                irregular = 1 + .065*math.sin(angle*3 + i*.19)
                position = add(center, mul(radial, radii[i]*irregular))
                index = len(self.positions)
                self.positions.append(position)
                self.normals.append(radial)
                self.uvs.append((j/sides*2, traveled/230))
                ring.append(index)
            rings.append(ring)
        for i in range(len(rings)-1):
            for j in range(sides):
                a, b = rings[i][j], rings[i][j+1]
                c, d = rings[i+1][j+1], rings[i+1][j]
                self.indices.extend((a, b, c, a, c, d))
        for ring, center in ((rings[0], path[0]), (rings[-1], path[-1])):
            # Tiny end caps close woody geometry; no collision proxies inferred.
            for j in range(sides):
                a, b = self.positions[ring[j]], self.positions[ring[j+1]]
                if center == path[0]:
                    self.triangle(center, b, a, (.5, .5), (1, 0), (0, 0))
                else:
                    self.triangle(center, a, b, (.5, .5), (0, 0), (1, 0))


def leaf(part, center, direction, length, width, tilt):
    direction = unit(direction)
    u, v = basis(direction)
    transverse = add(mul(u, math.cos(tilt)), mul(v, math.sin(tilt)))
    normal = unit(cross(transverse, direction))
    outline = [(0, 0), (-.39, .20), (-.5, .56), (0, 1), (.5, .56), (.39, .20)]
    points = [add(center, add(mul(transverse, x*width), mul(direction, y*length)))
              for x, y in outline]
    folded = add(center, add(mul(direction, length*.48), mul(normal, width*.12)))
    for i in range(len(points)):
        j = (i+1) % len(points)
        part.triangle(points[i], points[j], folded,
            (outline[i][0]+.5, outline[i][1]), (outline[j][0]+.5, outline[j][1]),
            (.5, .48), double=True)


def geometry():
    rng = random.Random(SEED)
    wood, green = Part(0), Part(1)
    trunk = [(17*math.sin(i*.42), 12*math.cos(i*.55)-12, -500+i*91) for i in range(13)]
    wood.tube(trunk, [87*(1-i/16)**1.16+9 for i in range(13)], 18)
    # Visible root flares reach into the same pre-existing -500 base envelope.
    for i in range(7):
        angle = i*math.tau/7+.19
        root = [(math.cos(angle)*r, math.sin(angle)*r, z)
                for r, z in ((10, -275), (68, -375), (155, -468), (205, -499))]
        wood.tube(root, [31, 28, 17, 4], 8)
    clusters = []
    for i in range(10):
        angle = i*2.3999632297+.32
        z = 230 + (i % 4)*92
        start = (13*math.sin(i), 11*math.cos(i), z)
        reach = 375 + rng.uniform(-48, 85)
        endpoint = (math.cos(angle)*reach, math.sin(angle)*reach, 775+(i % 3)*47)
        path = []
        for j in range(7):
            t = j/6
            point = add(mul(start, 1-t), mul(endpoint, t))
            point = add(point, (-math.sin(angle)*40*math.sin(t*math.pi),
                                math.cos(angle)*40*math.sin(t*math.pi),
                                62*math.sin(t*math.pi)))
            path.append(point)
        wood.tube(path, [34*(1-j/6)**1.2+5 for j in range(7)], 9)
        for j in range(3):
            a = angle + (j-1)*.43
            origin = path[4+j//2]
            end = add(endpoint, (math.cos(a)*110, math.sin(a)*110, -33+(j % 2)*56))
            wood.tube([origin, add(mul(origin,.45),mul(end,.55)), end], [11, 6, 2], 6)
            clusters.append(end)
    for center in clusters:
        # Fine, folded individual leaves create irregular gaps and softer outlines.
        for _ in range(31):
            angle = rng.uniform(0, math.tau)
            z = rng.uniform(-1, 1)
            radial = math.sqrt(1-z*z)
            radius = rng.random()**(1/3)
            offset = (math.cos(angle)*radial*118*radius,
                      math.sin(angle)*radial*100*radius, z*98*radius)
            location = add(center, offset)
            direction = (math.cos(angle)*.76, math.sin(angle)*.76, rng.uniform(-.6,.5))
            leaf(green, location, direction, rng.uniform(44,72), rng.uniform(25,40), rng.uniform(0,math.tau))
    return [wood, green], len(clusters)*31


def child(parent, tag, text=None, **attrs):
    result = ET.SubElement(parent, '{'+NS+'}'+tag, attrs)
    if text is not None:
        result.text = str(text)
    return result


def collada(path, parts):
    doc = ET.Element('{'+NS+'}COLLADA', version='1.4.1')
    asset = child(doc, 'asset')
    child(asset, 'created', '2026-10-03T00:00:00Z')
    child(asset, 'modified', '2026-10-03T00:00:00Z')
    child(asset, 'up_axis', 'Z_UP')
    images, effects, materials, geometries = [child(doc, n) for n in
        ('library_images', 'library_effects', 'library_materials', 'library_geometries')]
    scene = child(child(doc, 'library_visual_scenes'), 'visual_scene', id='Scene')
    for i, texture in enumerate(('swamp_bark.dds', 'swamp_leaf.dds')):
        mid = 'm'+str(i)
        child(child(images, 'image', id=mid+'-image'), 'init_from', 'textures/veyra/'+texture)
        profile = child(child(effects, 'effect', id=mid+'-effect'), 'profile_COMMON')
        surface = child(child(profile, 'newparam', sid=mid+'-surface'), 'surface', type='2D')
        child(surface, 'init_from', mid+'-image')
        sampler = child(child(profile, 'newparam', sid=mid+'-sampler'), 'sampler2D')
        child(sampler, 'source', mid+'-surface')
        phong = child(child(profile, 'technique', sid='common'), 'phong')
        child(child(phong, 'emission'), 'color', '0 0 0 1')
        child(child(phong, 'ambient'), 'color', '.55 .55 .55 1')
        child(child(phong, 'diffuse'), 'texture', texture=mid+'-sampler', texcoord='UVMap')
        child(child(phong, 'specular'), 'color', '.025 .025 .025 1')
        child(child(phong, 'shininess'), 'float', '8')
        child(child(materials, 'material', id=mid+'-material'), 'instance_effect', url='#'+mid+'-effect')
    for i, part in enumerate(parts):
        gid, mid = 'g'+str(i), 'm'+str(part.material)
        mesh = child(child(geometries, 'geometry', id=gid), 'mesh')
        for suffix, values, axes in [('p', part.positions, 'XYZ'), ('n', part.normals, 'XYZ'), ('uv', part.uvs, 'ST')]:
            source = child(mesh, 'source', id=gid+suffix)
            child(source, 'float_array', ' '.join(format(v,'.7g') for row in values for v in row),
                id=gid+suffix+'-array', count=str(len(values)*len(axes)))
            accessor = child(child(source,'technique_common'), 'accessor',
                source='#'+gid+suffix+'-array', count=str(len(values)), stride=str(len(axes)))
            for axis in axes:
                child(accessor, 'param', name=axis, type='float')
        vertices = child(mesh, 'vertices', id=gid+'-vertices')
        child(vertices, 'input', semantic='POSITION', source='#'+gid+'p')
        triangles = child(mesh, 'triangles', count=str(len(part.indices)//3), material=mid+'-slot')
        for offset, semantic, suffix in [(0,'VERTEX','-vertices'), (1,'NORMAL','n'), (2,'TEXCOORD','uv')]:
            attrs={'semantic':semantic,'source':'#'+gid+suffix,'offset':str(offset)}
            if semantic=='TEXCOORD': attrs['set']='0'
            child(triangles,'input',**attrs)
        child(triangles,'p',' '.join(str(index)+' '+str(index)+' '+str(index) for index in part.indices))
        instance = child(child(scene,'node',id=gid+'-node'),'instance_geometry',url='#'+gid)
        binding = child(child(child(instance,'bind_material'),'technique_common'),'instance_material',
            symbol=mid+'-slot',target='#'+mid+'-material')
        child(binding,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set='0')
    child(child(doc,'scene'),'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(doc).write(path,encoding='utf8',xml_declaration=True)


def dds(image, path, alpha=False):
    image = image.convert('RGBA' if alpha else 'RGB')
    blobs=[]
    while True:
        out=io.BytesIO()
        image.save(out,format='DDS',pixel_format='DXT5' if alpha else 'DXT1')
        blobs.append(out.getvalue())
        if image.size==(1,1): break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    header=bytearray(blobs[0][:128])
    struct.pack_into('<I',header,8,struct.unpack_from('<I',header,8)[0]|0x20000)
    struct.pack_into('<I',header,28,len(blobs))
    struct.pack_into('<I',header,108,0x401008)
    path.write_bytes(header+b''.join(blob[128:] for blob in blobs))


def textures(source):
    out=MOD/'Textures/veyra'
    out.mkdir(parents=True,exist_ok=True)
    diffuse=Image.open(source/'Diffuse.jpg').convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS)
    dds(diffuse,out/'swamp_bark.dds')
    # Existing source is DirectX tangent normal convention. Preserve channels.
    normal=Image.open(source/'nor_dx.png').convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
    dds(normal,out/'swamp_bark_n.dds',alpha=True)
    leaf_image=Image.new('RGB',(128,128))
    pixels=leaf_image.load()
    for y in range(128):
        for x in range(128):
            vein=math.exp(-((x-64)/2.4)**2)*19
            fine=5*math.sin((x+y*.63)*.22)
            shade=(1-abs(x-64)/64)*8
            pixels[x,y]=(int(47+vein+fine+shade),int(76+vein+fine+shade),int(31+vein*.6+fine*.6))
    dds(leaf_image,out/'swamp_leaf.dds')
    return [p for p in out.iterdir() if p.is_file()]


def bind_bark_source(source):
    metadata=json.loads((source/'files.json').read_text(encoding='utf8'))
    result=[]
    for channel,filename in [('Diffuse','Diffuse.jpg'),('nor_dx','nor_dx.png')]:
        path=source/filename
        with Image.open(path) as image:
            width,height=image.size
        if width!=height or width not in (1024,2048,4096,8192):
            raise ValueError('unbound input texture resolution')
        resolution=str(width//1024)+'k'
        format=path.suffix.lstrip('.')
        bound=metadata[channel][resolution][format]
        digest=hashlib.md5(path.read_bytes()).hexdigest()
        if digest!=bound['md5'] or path.stat().st_size!=bound['size']:
            raise ValueError('bark bytes do not match local source download metadata')
        result.append({'channel':channel,'file':filename,'resolution':resolution,
            'md5MatchesLocalDownloadMetadata':digest,'sourceUrl':bound['url'],
            'sha256':sha(path)})
    return {'downloadMetadataSha256':sha(source/'files.json'),'boundInputs':result}


def subrecord(kind,payload):
    return struct.pack('<4sI',kind,len(payload))+payload


def record(kind,payload):
    return struct.pack('<4sIII',kind,len(payload),0,0)+payload


def string(value):
    return value.encode('ascii')+bytes([0])


def records(path):
    with path.open('rb') as stream:
        while header:=stream.read(16):
            if len(header)!=16: raise ValueError('truncated TES3 header')
            kind,size,_,_=struct.unpack('<4sIII',header)
            payload=stream.read(size)
            if len(payload)!=size: raise ValueError('truncated TES3 body')
            yield kind,payload


def subrecords(payload):
    cursor=0
    while cursor<len(payload):
        if cursor+8>len(payload): raise ValueError('truncated subrecord header')
        kind,size=struct.unpack_from('<4sI',payload,cursor)
        cursor+=8
        if cursor+size>len(payload): raise ValueError('truncated subrecord body')
        yield kind,payload[cursor:cursor+size]
        cursor+=size


def write_plugin(path,ids,master):
    body=[]
    for rid in ids:
        body.append(record(b'STAT',subrecord(b'NAME',string(rid))+
            subrecord(b'MODL',string('veyra/swamp_tree_01.dae'))))
    header=subrecord(b'HEDR',struct.pack('<fI32s256sI',1.3,0,b'LEVIATH Workshop',
        b'Own swamp-tree candidate; no cell or actor overrides',len(body)))
    header+=subrecord(b'MAST',string('Morrowind.esm'))+subrecord(b'DATA',struct.pack('<Q',master.stat().st_size))
    path.write_bytes(record(b'TES3',header)+b''.join(body))


def inspect_base(master,bases):
    target='flora_bc_tree_02'
    stat, references, local=[] ,0,[]
    for kind,payload in records(master):
        if kind==b'STAT':
            ss=dict(subrecords(payload))
            rid=ss.get(b'NAME',b'').rstrip(bytes([0])).decode('cp1252')
            if rid==target:
                stat.append({'id':rid,'sourceRecordSha256':hashlib.sha256(payload).hexdigest(),
                    'originalModel':ss.get(b'MODL',b'').rstrip(bytes([0])).decode('cp1252')})
        elif kind==b'CELL':
            ss=list(subrecords(payload))
            name=ss[0][1].rstrip(bytes([0])).decode('cp1252') if ss and ss[0][0]==b'NAME' else ''
            current=None
            for key,value in ss:
                if key==b'FRMR': current=None
                elif key==b'NAME':
                    current=value.rstrip(bytes([0])).decode('cp1252')
                    if current==target:references+=1
                elif key==b'DATA' and current==target and len(value)==24 and name=='Seyda Neen':
                    local.append([round(x,3) for x in struct.unpack('<6f',value)[:3]])
    if len(stat)!=1: raise ValueError('target base STAT was not found exactly once')
    return {'masterSha256':sha(master),'targetStatic':stat[0],
        'targetReferencesInMaster':references,'seydaNeenReferencePositions':local,
        'previousCandidateMeshes':[{'name':p.name,'sha256':sha(p)} for p in bases]}


def verify(parts):
    vertices=[v for p in parts for v in p.positions]
    assert all(math.isfinite(value) for row in vertices for value in row)
    assert all(0<=index<len(p.positions) for p in parts for index in p.indices)
    assert all(len(p.indices)%3==0 and len(p.positions)==len(p.normals)==len(p.uvs) for p in parts)
    assert all(abs(sum(x*x for x in n)-1)<1e-6 for p in parts for n in p.normals)
    low=[min(row[i] for row in vertices) for i in range(3)]
    high=[max(row[i] for row in vertices) for i in range(3)]
    assert low[2]>=-510 and high[2]<1100
    assert len(parts[1].indices)//3<15000
    return {'bounds':[low,high],'triangles':[len(p.indices)//3 for p in parts],
        'vertices':[len(p.positions) for p in parts]}


def preview(parts):
    canvas=Image.new('RGB',(1350,620),(226,229,225))
    draw=ImageDraw.Draw(canvas)
    draw.text((24,12),'AUTHOR GEOMETRY PREVIEW / NOT OPENMW RENDER',(32,43,35))
    for panel,angle in enumerate((0,math.pi/3,math.pi/2)):
        triangles=[]
        for part in parts:
            for i in range(0,len(part.indices),3):
                vertices=[part.positions[index] for index in part.indices[i:i+3]]
                points=[(p[0]*math.cos(angle)+p[1]*math.sin(angle),p[2],
                         -p[0]*math.sin(angle)+p[1]*math.cos(angle)) for p in vertices]
                triangles.append((sum(p[2] for p in points)/3,points,part.material))
        triangles.sort(key=lambda value:value[0])
        for _,points,material in triangles:
            pixels=[(225+panel*450+p[0]*.30,555-(p[1]+500)*.32) for p in points]
            draw.polygon(pixels,fill=(82,71,53) if material==0 else (62,83,45))
        draw.text((165+panel*450,584),'view '+str(panel+1),(32,43,35))
    canvas.save(ROOT/'SILHOUETTE_PREVIEW.png')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bark-source',required=True,type=Path)
    parser.add_argument('--master',required=True,type=Path)
    parser.add_argument('--base-mesh',action='append',required=True,type=Path)
    args=parser.parse_args()
    inputs=[args.master,*args.base_mesh,args.bark_source/'Diffuse.jpg',args.bark_source/'nor_dx.png']
    before={str(p.resolve()):sha(p) for p in inputs}
    bark_binding=bind_bark_source(args.bark_source)
    MOD.mkdir(parents=True,exist_ok=True)
    parts,leaves=geometry()
    checks=verify(parts)
    textures(args.bark_source)
    mesh=MOD/'Meshes/veyra/swamp_tree_01.dae'
    collada(mesh,parts)
    write_plugin(MOD/'Veyra-Vegetation.esp',['veyra_swamp_tree_01'],args.master)
    write_plugin(MOD/'Veyra-Vegetation-Tree02.esp',['flora_bc_tree_02'],args.master)
    preview(parts)
    base=inspect_base(args.master,args.base_mesh)
    assert all(sha(Path(p))==digest for p,digest in before.items())
    generated={p.relative_to(MOD).as_posix():sha(p) for p in MOD.rglob('*') if p.is_file()}
    receipt={'schema':'veyra.vegetation-candidate.v1','version':'0.1.0','seed':SEED,
        'generatorSha256':sha(Path(__file__)),
        'status':'STATIC_GEOMETRY_STRUCTURE_PASS_NATIVE_PENDING','checks':checks,
        'individualLeaves':leaves,'leafBackfaces':'EXPLICIT_REVERSED_GEOMETRY',
        'baseEnvelope':'retain previous candidate base offset near -500; anchoring remains native QA',
        'baseSourceBinding':base,'inputHashesUnchanged':len(inputs),
        'bark':{'author':'Rob Tuytel','asset':'Bark Brown 02','license':'CC0-1.0',
            'source':'https://polyhaven.com/a/bark_brown_02','licenseSource':'https://polyhaven.com/license',
            'inputDiffuseSha256':sha(args.bark_source/'Diffuse.jpg'),
            'inputNormalSha256':sha(args.bark_source/'nor_dx.png'),'outputResolution':[1024,1024]},
        'barkSourceBinding':bark_binding,
        'geometryLicense':'MIT','foliageTextureSource':'own deterministic code','generatedHashes':generated,
        'installedProfilesChanged':0,'existingCellsChanged':0,'nativeRendering':'PENDING',
        'collisionAndAnchoring':'PENDING','performance':'PENDING',
        'claimCeiling':'OWN_AUTHORED_STATIC_MESH_AND_PLUGIN_STRUCTURE_ONLY'}
    (ROOT/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print('VEGETATION_STRUCTURE_PASS',sum(checks['triangles']),'triangles;',leaves,'leaves; native pending')


if __name__=='__main__':
    main()
