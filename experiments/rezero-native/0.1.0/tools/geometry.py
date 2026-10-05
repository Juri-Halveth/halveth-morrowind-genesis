"""Small native geometry library. Fresh forms live in build_rezero.py. MIT.
COLLADA format knowledge retained from previous native pipeline; no old forms imported.
"""
from pathlib import Path
from collections import Counter
from dataclasses import dataclass,field
from datetime import datetime,timezone
import math,xml.etree.ElementTree as ET
NS='http://www.collada.org/2005/11/COLLADASchema';ET.register_namespace('',NS)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def normal(v):
    length=math.sqrt(sum(x*x for x in v))
    if length<1e-9:raise ValueError('Degenerate geometry')
    return tuple(x/length for x in v)
@dataclass
class Mesh:
    p:list=field(default_factory=list);n:list=field(default_factory=list);uv:list=field(default_factory=list)
    def tri(self,a,b,c,uv=None,n=None,tile=70):
        axisnormal=normal(cross(sub(b,a),sub(c,a)))
        omit=max(range(3),key=lambda j:abs(axisnormal[j]));axes=[j for j in range(3) if j!=omit]
        for i,p in enumerate((a,b,c)):
            self.p.append(p);self.n.append(n[i] if n else axisnormal)
            self.uv.append(uv[i] if uv else (p[axes[0]]/tile,p[axes[1]]/tile))
    def quad(self,a,b,c,d,uv=None,n=None,tile=70):
        for ids in [(0,1,2),(0,2,3)]:
            self.tri(*[(a,b,c,d)[i] for i in ids],
                [uv[i] for i in ids] if uv else None,[n[i] for i in ids] if n else None,tile)
    def box(self,c,size,tile=70):
        points=[tuple(c[j]+size[j]*q[j]/2 for j in range(3)) for q in
            [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.quad(*(points[i] for i in ids),tile=tile)
    def transformed(self,f,fn=None):
        return Mesh([f(p) for p in self.p],[fn(n) if fn else n for n in self.n],self.uv.copy())
    def extend(self,other):self.p+=other.p;self.n+=other.n;self.uv+=other.uv
    def bounds(self):return [[min(p[j] for p in self.p) for j in range(3)],[max(p[j] for p in self.p) for j in range(3)]]
def revolve(mesh,profile,c=(0,0,0),segments=64,tile=25):
    """Closed solid if both profile endpoints are on axis. Interior is real geometry."""
    if profile[0][1]!=0 or profile[-1][1]!=0:raise ValueError('Revolve needs two closed axis endpoints')
    for i in range(len(profile)-1):
        z0,r0=profile[i];z1,r1=profile[i+1];dz=z1-z0;dr=r1-r0
        if dz==0 and dr==0:raise ValueError('Repeated profile station')
        def point(z,r,a):return(c[0]+r*math.cos(a),c[1]+r*math.sin(a),c[2]+z)
        def norm(a):return normal((dz*math.cos(a),dz*math.sin(a),-dr))
        for j in range(segments):
            a=j*math.tau/segments;b=(j+1)*math.tau/segments
            ps=[point(z0,r0,a),point(z0,r0,b),point(z1,r1,b),point(z1,r1,a)]
            uv=[(a/math.tau,z0/tile),(b/math.tau,z0/tile),(b/math.tau,z1/tile),(a/math.tau,z1/tile)]
            # A flat cap cannot use angular/height UVs: every UV would lie on
            # one line and produce an undefined normal-map tangent frame.
            # Axis triangles also use a real planar disk map.
            if abs(dz)<1e-9 or r0==0 or r1==0:
                radius=max(r0,r1)
                uv=[((p[0]-c[0])/(2*radius)+.5,(p[1]-c[1])/(2*radius)+.5) for p in ps]
            ns=[norm(a),norm(b),norm(b),norm(a)]
            if r0==0:mesh.tri(ps[0],ps[2],ps[3],[uv[k] for k in [0,2,3]],[ns[k] for k in [0,2,3]])
            elif r1==0:mesh.tri(ps[0],ps[1],ps[2],[uv[k] for k in [0,1,2]],[ns[k] for k in [0,1,2]])
            else:mesh.quad(*ps,uv=uv,n=ns)
def rounded_slab(mesh,w,d,lo,hi,r=3,bevel=.75,tile=70,c=(0,0)):
    """One solid supporting surface, a bevel and a closed underside."""
    rings=[]
    for z,inset in [(lo,bevel),(lo+bevel,0),(hi-bevel,0),(hi,bevel)]:
        rw=w/2-inset;rd=d/2-inset;rr=max(.3,r-inset);ring=[]
        for center,angle in [((rw-rr,rd-rr),0),((-rw+rr,rd-rr),90),((-rw+rr,-rd+rr),180),((rw-rr,-rd+rr),270)]:
            for j in range(7):
                a=math.radians(angle+j*90/6)
                ring.append((c[0]+center[0]+rr*math.cos(a),c[1]+center[1]+rr*math.sin(a),z))
        rings.append(ring)
    for i in range(len(rings)-1):
        for j in range(len(rings[i])):
            jj=(j+1)%len(rings[i]);mesh.quad(rings[i][j],rings[i][jj],rings[i+1][jj],rings[i+1][j],tile=tile)
    for ring,reverse in [(rings[0],True),(rings[-1],False)]:
        center=(c[0],c[1],ring[0][2])
        for j in range(len(ring)):
            jj=(j+1)%len(ring)
            a,b=(ring[jj],ring[j]) if reverse else (ring[j],ring[jj])
            mesh.tri(center,a,b,tile=tile)
def tube(mesh,points,r=1,segments=10,tile=50):
    """Closed swept branch or metalwork; orientation follows each path tangent."""
    rings=[]
    for i,p in enumerate(points):
        tangent=normal(sub(points[min(i+1,len(points)-1)],points[max(0,i-1)]))
        basis=(0,0,1) if abs(tangent[2])<.95 else (0,1,0)
        u=normal(cross(tangent,basis));v=cross(tangent,u)
        rings.append([tuple(p[k]+r*(u[k]*math.cos(j*math.tau/segments)+v[k]*math.sin(j*math.tau/segments)) for k in range(3)) for j in range(segments)])
    for i in range(len(points)-1):
        for j in range(segments):
            jj=(j+1)%segments;mesh.quad(rings[i][j],rings[i][jj],rings[i+1][jj],rings[i+1][j],tile=tile)
    for index,rev in [(0,True),(-1,False)]:
        for j in range(segments):
            jj=(j+1)%segments;a,b=(rings[index][jj],rings[index][j]) if rev else(rings[index][j],rings[index][jj])
            mesh.tri(points[index],a,b,tile=tile)
def manifold(mesh):
    """Welded edge incidence for one generated component, plus signed volume."""
    quant=lambda p:tuple(round(x,6) for x in p)
    edges=Counter();volume=0
    for i in range(0,len(mesh.p),3):
        a,b,c=mesh.p[i:i+3];qa,qb,qc=map(quant,(a,b,c))
        for x,y in [(qa,qb),(qb,qc),(qc,qa)]:edges[tuple(sorted((x,y)))]+=1
        volume+=sum(a[j]*cross(b,c)[j] for j in range(3))/6
    return {'triangles':len(mesh.p)//3,'boundaryEdges':sum(n==1 for n in edges.values()),
            'nonManifoldEdges':sum(n!=2 for n in edges.values()),'signedVolume':volume,'bounds':mesh.bounds()}
def export(path,parts,materials,collision=None):
    doc=ET.Element('{'+NS+'}COLLADA',version='1.4.1')
    def e(parent,tag,text=None,**attrs):
        child=ET.SubElement(parent,'{'+NS+'}'+tag,attrs)
        if text is not None:child.text=str(text)
        return child
    asset=e(doc,'asset');e(asset,'created',datetime.now(timezone.utc).isoformat())
    e(asset,'unit',name='OpenMWUnit',meter='0.014285714');e(asset,'up_axis','Z_UP')
    images=e(doc,'library_images');effects=e(doc,'library_effects');mats=e(doc,'library_materials');geometries=e(doc,'library_geometries')
    scene=e(e(doc,'library_visual_scenes'),'visual_scene',id='Scene');visual=e(scene,'node',id='rezero-visual',name='OwnRezeroGeometry')
    for name in parts:
        mat=materials[name];e(e(images,'image',id=name+'-image'),'init_from','textures/rezero/'+name+'.dds')
        profile=e(e(effects,'effect',id=name+'-effect'),'profile_COMMON')
        e(e(e(profile,'newparam',sid=name+'-surface'),'surface',type='2D'),'init_from',name+'-image')
        e(e(e(profile,'newparam',sid=name+'-sampler'),'sampler2D'),'source',name+'-surface')
        phong=e(e(profile,'technique',sid='common'),'phong')
        e(e(phong,'emission'),'color',' '.join(str(x) for x in (*mat.get('emission',(0,0,0)),1)))
        e(e(phong,'ambient'),'color','.5 .5 .5 1')
        e(e(phong,'diffuse'),'texture',texture=name+'-sampler',texcoord='UVMap')
        e(e(phong,'specular'),'color',' '.join(str(x) for x in [mat['spec']]*3+[1]))
        e(e(phong,'shininess'),'float',mat['shine'])
        e(e(mats,'material',id=name+'-material'),'instance_effect',url='#'+name+'-effect')
    def output_mesh(name,mesh,node,mat=None):
        if len(mesh.p)%3 or not len(mesh.p)==len(mesh.n)==len(mesh.uv):raise ValueError('Mesh attribute arity')
        if not all(math.isfinite(x) for row in mesh.p+mesh.n+mesh.uv for x in row):raise ValueError('Nonfinite mesh')
        if mat:
            for i in range(0,len(mesh.uv),3):
                a,b,c=mesh.uv[i:i+3]
                determinant=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(determinant)<1e-12:raise ValueError('Undefined material UV tangent '+name+' triangle '+str(i//3))
        m=e(e(geometries,'geometry',id=name),'mesh')
        for suffix,values,axes in [('p',mesh.p,'XYZ'),('n',mesh.n,'XYZ'),('uv',mesh.uv,'ST')]:
            source=e(m,'source',id=name+'-'+suffix);e(source,'float_array',' '.join(format(x,'.9g') for row in values for x in row),id=name+'-'+suffix+'-array',count=str(len(values)*len(axes)))
            accessor=e(e(source,'technique_common'),'accessor',source='#'+name+'-'+suffix+'-array',count=str(len(values)),stride=str(len(axes)))
            for axis in axes:e(accessor,'param',name=axis,type='float')
        e(e(m,'vertices',id=name+'-vertices'),'input',semantic='POSITION',source='#'+name+'-p')
        attrs={'count':str(len(mesh.p)//3)}
        if mat:attrs['material']=mat+'-slot'
        triangle=e(m,'triangles',**attrs)
        for off,semantic,suffix in [(0,'VERTEX','vertices'),(1,'NORMAL','n'),(2,'TEXCOORD','uv')]:
            attrs={'offset':str(off),'semantic':semantic,'source':'#'+name+'-'+suffix}
            if semantic=='TEXCOORD':attrs['set']='0'
            e(triangle,'input',**attrs)
        e(triangle,'p',' '.join(f'{i} {i} {i}' for i in range(len(mesh.p))))
        ins=e(node,'instance_geometry',url='#'+name)
        if mat:
            binding=e(e(e(ins,'bind_material'),'technique_common'),'instance_material',symbol=mat+'-slot',target='#'+mat+'-material')
            e(binding,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set='0')
    stats={}
    for mat,mesh in parts.items():
        if not mesh.p:continue
        output_mesh('rezero-'+mat,mesh,e(visual,'node',id='node-'+mat,name=mat),mat);stats[mat]=len(mesh.p)//3
    if collision and collision.p:
        output_mesh('rezero-collision',collision,e(scene,'node',id='collision',name='collision'));stats['collision']=len(collision.p)//3
    e(e(doc,'scene'),'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True);ET.ElementTree(doc).write(path,encoding='utf8',xml_declaration=True)
    return stats
