"""Verify serialized mesh/plugin/material contracts before the native probe."""
from pathlib import Path
import hashlib
import json
import math
import struct
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parent
mod=root/'mod'
receipt=json.loads((root/'BUILD_RECEIPT.json').read_text(encoding='utf8'))
assert hashlib.sha256((root/'build-vegetation.py').read_bytes()).hexdigest()==receipt['generatorSha256']
for filename,digest in receipt['generatedHashes'].items():
    assert hashlib.sha256((mod/filename).read_bytes()).hexdigest()==digest,filename
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
doc=ET.parse(mod/'Meshes/veyra/swamp_tree_01.dae')
ids=[node.attrib['id'] for node in doc.iter() if 'id' in node.attrib]
assert len(ids)==len(set(ids))
id_set=set(ids)
for node in doc.iter():
    for key in ('url','source','target'):
        value=node.attrib.get(key,'')
        if value.startswith('#'): assert value[1:] in id_set,(key,value)
triangle_counts=[]
for mesh in doc.findall('.//c:geometry/c:mesh',ns):
    sources={}
    for source in mesh.findall('c:source',ns):
        array=source.find('c:float_array',ns)
        values=[float(value) for value in array.text.split()]
        assert len(values)==int(array.attrib['count'])
        assert all(math.isfinite(value) for value in values)
        accessor=source.find('c:technique_common/c:accessor',ns)
        stride=int(accessor.attrib['stride'])
        count=int(accessor.attrib['count'])
        assert len(values)==count*stride
        sources[source.attrib['id']]=(count,stride,values)
        if source.attrib['id'].endswith('n'):
            assert all(abs(sum(v*v for v in values[i:i+3])-1)<2e-6 for i in range(0,len(values),3))
    vertices=mesh.find('c:vertices',ns)
    vertex_source=vertices.find('c:input',ns).attrib['source'][1:]
    for triangles in mesh.findall('c:triangles',ns):
        count=int(triangles.attrib['count'])
        inputs=triangles.findall('c:input',ns)
        assert {node.attrib['semantic'] for node in inputs}=={'VERTEX','NORMAL','TEXCOORD'}
        stride=1+max(int(node.attrib['offset']) for node in inputs)
        indices=[int(value) for value in triangles.find('c:p',ns).text.split()]
        assert len(indices)==count*3*stride
        for node in inputs:
            source=vertex_source if node.attrib['semantic']=='VERTEX' else node.attrib['source'][1:]
            limit=sources[source][0]
            assert all(0<=index<limit for index in indices[int(node.attrib['offset'])::stride])
        triangle_counts.append(count)
assert triangle_counts==receipt['checks']['triangles']

files={p.relative_to(mod).as_posix().lower():p for p in mod.rglob('*') if p.is_file()}
texture_refs=[]
for image in doc.findall('.//c:library_images/c:image',ns):
    name=image.find('c:init_from',ns).text
    assert name.lower() in files,name
    texture_refs.append(name)
for filename,(width,height) in {'Textures/veyra/swamp_bark.dds':(1024,1024),
    'Textures/veyra/swamp_bark_n.dds':(1024,1024),'Textures/veyra/swamp_leaf.dds':(128,128)}.items():
    data=(mod/filename).read_bytes()
    assert data[:4]==b'DDS '
    actual_height,actual_width=struct.unpack_from('<II',data,12)
    assert (actual_width,actual_height)==(width,height)
    assert struct.unpack_from('<I',data,28)[0]==int(math.log2(width))+1

def records(data):
    cursor=0
    while cursor<len(data):
        assert cursor+16<=len(data)
        kind,size,_,_=struct.unpack_from('<4sIII',data,cursor)
        cursor+=16
        assert cursor+size<=len(data)
        yield kind,data[cursor:cursor+size]
        cursor+=size

def subs(data):
    cursor=0
    while cursor<len(data):
        assert cursor+8<=len(data)
        kind,size=struct.unpack_from('<4sI',data,cursor)
        cursor+=8
        assert cursor+size<=len(data)
        yield kind,data[cursor:cursor+size]
        cursor+=size

plugin_receipts=[]
for filename,expected_id in [('Veyra-Vegetation.esp',b'veyra_swamp_tree_01'),
    ('Veyra-Vegetation-Tree02.esp',b'flora_bc_tree_02')]:
    rows=list(records((mod/filename).read_bytes()))
    assert [row[0] for row in rows]==[b'TES3',b'STAT']
    header=dict(subs(rows[0][1]))
    assert header[b'MAST'].rstrip(bytes([0]))==b'Morrowind.esm'
    assert struct.unpack_from('<I',header[b'HEDR'],296)[0]==1
    target=dict(subs(rows[1][1]))
    assert target[b'NAME'].rstrip(bytes([0]))==expected_id
    assert target[b'MODL'].rstrip(bytes([0]))==b'veyra/swamp_tree_01.dae'
    plugin_receipts.append({'file':filename,'recordTypes':['TES3','STAT'],
        'staticId':expected_id.decode('ascii'),'cellRecords':0})

result={'schema':'veyra.vegetation-serialized-check.v1',
    'status':'SERIALIZED_STRUCTURE_PASS_NATIVE_PENDING','generatorDigestMatches':True,
    'outputDigestsMatch':len(receipt['generatedHashes']),'triangleCounts':triangle_counts,
    'resolvedTextureReferences':texture_refs,'plugins':plugin_receipts,
    'native':'PENDING_ROOT_PROBE','claimCeiling':'XML_TES3_DDS_CONTRACT_ONLY'}
(root/'CHECK_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('VEGETATION_SERIALIZED_PASS',sum(triangle_counts),'triangles;',len(texture_refs),'textures;',len(plugin_receipts),'plugins')
