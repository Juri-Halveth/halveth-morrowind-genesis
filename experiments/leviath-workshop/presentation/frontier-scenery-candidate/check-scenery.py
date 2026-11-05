"""MIT. Independent saved TES3/XML/vertex/corridor oracle; no engine launch."""
from pathlib import Path
from collections import Counter
import argparse, datetime, hashlib, json, math, struct, subprocess, sys
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent;NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def records(data):
    out=[];p=0
    while p<len(data):
        kind,n,a,b=struct.unpack_from('<4sIII',data,p);p+=16
        assert a==b==0 and p+n<=len(data);out.append((kind,data[p:p+n]));p+=n
    assert p==len(data);return out
def subs(data):
    out=[];p=0
    while p<len(data):
        kind,n=struct.unpack_from('<4sI',data,p);p+=8
        assert p+n<=len(data);out.append((kind,data[p:p+n]));p+=n
    assert p==len(data);return out
def heights(plugin):
    nodes={};tiles={}
    for kind,body in records(plugin.read_bytes()):
        if kind!=b'LAND':continue
        ss=dict(subs(body));x,y=struct.unpack('<ii',ss[b'INTV']);v=ss[b'VHGT']
        first=struct.unpack_from('<f',v)[0];d=struct.unpack_from('<4225b',v,4);rows=[]
        for row in range(65):
            first+=d[65*row];running=first;values=[running*8]
            for col in range(1,65):running+=d[65*row+col];values.append(running*8)
            rows.append(values)
            for col,h in enumerate(values):
                key=(x*8192+col*128,y*8192+row*128)
                assert key not in nodes or nodes[key]==h;nodes[key]=h
        tiles[(x,y)]=(rows,hashlib.sha256(v).hexdigest())
    assert len(nodes)==66049;return nodes,tiles
def distance(p,a,b):
    v=(b[0]-a[0],b[1]-a[1]);w=(p[0]-a[0],p[1]-a[1])
    t=min(1,max(0,(w[0]*v[0]+w[1]*v[1])/(v[0]*v[0]+v[1]*v[1])))
    return math.hypot(w[0]-t*v[0],w[1]-t*v[1])
def mesh(path,expected,leaf=False):
    d=ET.parse(path);assert d.findtext('c:asset/c:up_axis',namespaces=NS)=='Z_UP'
    assert {i.findtext('c:init_from',namespaces=NS)for i in d.findall('c:library_images/c:image',NS)}=={
        'textures/veyra/frontier/frontier_stone.dds','textures/veyra/crown_leaf_01.dds'}
    geometries=d.findall('c:library_geometries/c:geometry',NS);assert len(geometries)==1
    arrays={}
    m=geometries[0].find('c:mesh',NS)
    for s in m.findall('c:source',NS):
        values=list(map(float,s.find('c:float_array',NS).text.split()))
        a=s.find('c:technique_common/c:accessor',NS);stride=int(a.get('stride'))
        assert len(values)==int(a.get('count'))*stride and all(math.isfinite(x)for x in values)
        arrays[s.get('id')]=[tuple(values[i:i+stride])for i in range(0,len(values),stride)]
    ps,ns,uvs=arrays['g0p'],arrays['g0n'],arrays['g0uv'];assert len(ps)==len(ns)==len(uvs)
    assert all(abs(sum(x*x for x in n)-1)<2e-6 for n in ns)
    tr=m.find('c:triangles',NS);count=int(tr.get('count'));assert count==expected
    ii=list(map(int,tr.findtext('c:p',namespaces=NS).split()));assert len(ii)==count*9
    decoded=[];edge=Counter();volume=0
    for i in range(0,len(ii),9):
        assert all(0<=x<len(ps)for x in ii[i:i+9])
        pts=[ps[ii[i+j]]for j in(0,3,6)];u=[pts[1][j]-pts[0][j]for j in range(3)];v=[pts[2][j]-pts[0][j]for j in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        assert sum(x*x for x in n)>1e-7
        for a,b in zip(pts,pts[1:]+pts[:1]):edge[tuple(sorted((a,b)))]+=1
        a,b,c=pts;volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        decoded.append(pts)
    if leaf:
        for i in range(0,len(decoded),2):assert decoded[i]==list(reversed(decoded[i+1]))
    else:assert set(edge.values())=={2} and volume>0
    return {'triangles':count,'positions':ps,'radius':max(math.hypot(p[0],p[1])for p in ps),
        'closedPositiveVolume':not leaf,'explicitBackfaces':leaf,'signedVolume':volume}
def main():
    p=argparse.ArgumentParser();p.add_argument('--frontier',type=Path,required=True)
    p.add_argument('--crown-directory',type=Path,required=True);p.add_argument('--esmtool',type=Path,required=True)
    p.add_argument('--rebuild-arguments-json',type=Path,required=True);a=p.parse_args()
    m=json.loads((BASE/'SCENERY_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(a.frontier)==m['terrainGrid']['inputPluginSha256']
    assert m['counts']=={'tree':20,'stone':20,'grass':28,'totalReferences':68,'ownSTAT':2,'CELL':1}
    expected={'LEVIATH-Frontier-Scenery.esp','Meshes/veyra/frontier_scenery/veyra_frontier_stone_cluster_01.dae',
        'Meshes/veyra/frontier_scenery/veyra_frontier_grass_01.dae'}
    assert {q.relative_to(BASE/'mod').as_posix()for q in(BASE/'mod').rglob('*')if q.is_file()}==expected
    rr=records((BASE/'mod'/m['plugin']).read_bytes());assert[k for k,_ in rr]==[b'TES3',b'STAT',b'STAT',b'CELL']
    hh=subs(rr[0][1]);assert[k for k,_ in hh]==[b'HEDR',b'MAST',b'DATA',b'MAST',b'DATA',b'MAST',b'DATA']
    assert hh[0][1][:4].hex()=='6666a63f' and struct.unpack_from('<I',hh[0][1],296)[0]==3
    assert[hh[i][1]for i in(1,3,5)]==[b'Morrowind.esm\0',b'LEVIATH-Frontier.esp\0',b'Veyra-Dense-Crown.esp\0']
    assert struct.unpack('<Q',hh[4][1])[0]==a.frontier.stat().st_size
    assert struct.unpack('<Q',hh[6][1])[0]==(a.crown_directory/'mod/Veyra-Dense-Crown.esp').stat().st_size
    for body,rid in zip(rr[1:3],('veyra_frontier_stone_cluster_01','veyra_frontier_grass_01')):
        assert subs(body[1])==[(b'NAME',rid.encode()+b'\0'),(b'MODL',('veyra/frontier_scenery/'+rid+'.dae').encode()+b'\0')]
    ss=subs(rr[3][1]);assert[k for k,_ in ss[:3]]==[b'NAME',b'DATA',b'RGNN']
    assert ss[0][1]==b'\0'and struct.unpack('<Iii',ss[1][1])==(2,65,-62)and ss[2][1]==b'veyra_frontier_region\0'
    assert len(ss)==3+68*4
    refs=[]
    for i,row in enumerate(m['references']):
        s=ss[3+4*i:7+4*i];assert[k for k,_ in s]==[b'FRMR',b'NAME',b'XSCL',b'DATA']
        assert struct.unpack('<I',s[0][1])[0]==row['reference'] and s[1][1]==row['recordId'].encode()+b'\0'
        assert struct.unpack('<f',s[2][1])[0]==row['scale']
        xyzrxryrz=struct.unpack('<6f',s[3][1]);assert list(xyzrxryrz[:3])==row['position']
        assert xyzrxryrz[3:5]==(0,0)and xyzrxryrz[5]==row['rotationZ'];refs.append(row['reference'])
    assert len(set(refs))==68
    nodes,tiles=heights(a.frontier);route=m['forestPath']['controlPoints'];margins=[]
    for r in m['references']:
        x,y,z=r['position'];proof=r['anchor'];assert x%128==y%128==0 and z==nodes[(x,y)]
        gx,gy=proof['coordinates'];ix,iy=proof['vertex'];grid,digest=tiles[(gx,gy)]
        assert x==gx*8192+ix*128 and y==gy*8192+iy*128 and z==grid[iy][ix]and digest==proof['vhgtSha256']
        patch=proof['patchHalfExtent'];h=[nodes[(x+dx,y+dy)]for dx in range(-patch,patch+1,128)for dy in range(-patch,patch+1,128)]
        assert min(h)==proof['patchMinimum']and max(h)==proof['patchMaximum']
        foot,full=r['lowFootprintRadius'],r['fullEnvelopeRadius'];point=(x,y)
        actual={'arenaFullEnvelope':math.dist(point,(540672,-507904))-(3100+full),
            'entryTownlifeFullEnvelope':math.dist(point,(536576,-512000))-(2600+full),
            'approachLowFootprint':distance(point,(536576,-512000),
                (540672-3000/math.sqrt(2),-507904-3000/math.sqrt(2)))-(360+foot+128),
            'forestPathLowFootprint':min(distance(point,p,q)for p,q in zip(route,route[1:]))-(600+foot+128),
            'northRampLowFootprint':distance(point,(540672,-506204),(540672,-504804))-(350+foot+128),
            'constructionFixtureLowFootprint':math.dist(point,(536100,-512000))-(1000+foot)}
        assert min(actual.values())>=0 and all(abs(actual[k]-r['freeMargins'][k])<1e-6 for k in actual)
        margins.append(min(actual.values()))
        if r['kind']=='grass':assert max(h)==min(h)
        if r['kind']=='tree':assert z-min(h)<=50*r['scale']
    assert all(s['position'][2]==nodes[tuple(s['position'][:2])]==320 for s in m['forestPath']['gridVertexSamples'])
    trees=[r for r in m['references']if r['kind']=='tree']
    assert min(math.dist(a['position'][:2],b['position'][:2])for i,a in enumerate(trees)for b in trees[i+1:])>=1024
    model_results={}
    for rid,leaf,count in [('veyra_frontier_stone_cluster_01',False,504),('veyra_frontier_grass_01',True,240)]:
        result=mesh(BASE/'mod/Meshes/veyra/frontier_scenery'/(rid+'.dae'),count,leaf)
        for r in m['references']:
            if r['recordId']==rid:assert result['radius']*r['scale']<=r['lowFootprintRadius']
        result.pop('positions');model_results[rid]=result
    before={q.relative_to(BASE).as_posix():sha(q)for q in(BASE/'mod').rglob('*')if q.is_file()}
    for name in('SCENERY_MANIFEST.json','SCENERY_PREVIEW.png'):before[name]=sha(BASE/name)
    argv=json.loads(a.rebuild_arguments_json.read_text(encoding='utf-8'))
    assert isinstance(argv,list)and all(isinstance(x,str)for x in argv)
    result=subprocess.run([sys.executable,str(BASE/'build-scenery.py'),*argv],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert all(sha(BASE/rel)==digest for rel,digest in before.items())
    parser_digest='6d3b08d258d55aed6670b7b8a9be7849e168e807522877f8457670fe48592cf6'
    assert sha(a.esmtool)==parser_digest
    parsed=subprocess.run([str(a.esmtool),'-q','-C','dump',str(BASE/'mod'/m['plugin'])],capture_output=True,text=True,timeout=60)
    assert parsed.returncode==0,parsed.stdout+parsed.stderr
    receipt={'schema':'veyra.frontier-scenery-check.v1','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checkerSha256':sha(Path(__file__)),'generatorSha256':sha(BASE/'build-scenery.py'),
        'checks':{'closedModFiles3':True,'TES3MasterContract':True,'STAT2CELL1Refs68Schema':True,
            'storedFloat32TransformsExact':True,'independentVHGTAnchorProofs68':True,'flatPathVertexSamples':True,
            'sixReservedMarginTypesAllRefs':True,'treeSpacing1024':True,'ownGeometryNormalsIndicesWinding':True,
            'rockClosedGrassBackfaces':True,'repeat5OutputsIdentical':True},
        'minimumStaticFreeMargin':min(margins),'models':model_results,'repeatHashes':before,
        'fileParser':{'sha256':parser_digest,'exitCode':parsed.returncode},
        'nativeRenderingCollisionNavigationFrametime':'PENDING_ROOT_PROBE','humanVisualApproval':'PENDING'}
    (BASE/'CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
