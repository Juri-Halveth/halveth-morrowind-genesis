#!/usr/bin/env python3
"""MIT. Own irregular terrain materials; texture-only override of frozen Frontier."""
from pathlib import Path
import datetime, hashlib, io, json, struct, sys
import numpy as np
from PIL import Image, ImageDraw
import PIL

BASE=Path(__file__).resolve().parent
FRONTIER=BASE.parent/'frontier-candidate'
SIZE=1024
SEED=2026100342
MOD=BASE/'mod'
OLD_HASHES={
 'ground':'54d831f1c8f8df209b7aa85a402a419be0b9769379b14a0de5378f914d2bb78a',
 'stone':'b275a2a32e41715ea11163a7e69ad30eddc255817132106679f837cab62daab3',
 'coast':'a3c3c6114ce3a3016827729f003150d5972ecbbd347b22517d9282945774cda7'}
PLUGIN_HASH='7484682d663d62a22dfe59c01d3dbce862a2e1897f66e1b563b5b455cb2a75ad'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def field(rng, sigma):
    # Periodic Gaussian convolution of independent random samples produces
    # coherent irregular patches without a repeated sine/checker motif.
    values=rng.normal(size=(SIZE,SIZE))
    frequency=np.fft.fftfreq(SIZE)
    kernel=np.exp(-2*np.pi**2*sigma**2*(frequency[:,None]**2+frequency[None,:]**2))
    values=np.fft.ifft2(np.fft.fft2(values)*kernel).real
    values-=values.mean()
    return values/values.std()

def warp(values,dx,dy):
    y,x=np.indices(values.shape,dtype=float)
    x=(x+dx)%SIZE;y=(y+dy)%SIZE
    ix=np.floor(x).astype(int);iy=np.floor(y).astype(int)
    fx=x-ix;fy=y-iy
    return (values[iy,ix]*(1-fx)*(1-fy)+values[iy,(ix+1)%SIZE]*fx*(1-fy)+
            values[(iy+1)%SIZE,ix]*(1-fx)*fy+values[(iy+1)%SIZE,(ix+1)%SIZE]*fx*fy)

def material(name, number):
    rng=np.random.default_rng(SEED+number*97)
    broad=field(rng,92)
    medium=field(rng,29)
    small=field(rng,8)
    grain=field(rng,1.3)
    dx=field(rng,48)*22;dy=field(rng,48)*22
    broad=warp(broad,dx,dy);medium=warp(medium,dx*.5,dy*.5)
    variation=np.clip(broad*5.8+medium*4.8+small*2.9+grain*1.2,-22,22)
    if name=='ground':
        earth=np.clip((warp(field(rng,46),dx,dy)-.25)*.44,0,.75)
        lush=np.array((79,91,57))[None,None,:]
        soil=np.array((91,81,58))[None,None,:]
        pixels=lush*(1-earth[:,:,None])+soil*earth[:,:,None]+variation[:,:,None]
        # Soft irregular grass-colour veins, not one recognizable tiled stamp.
        veins=np.clip((field(rng,3.2)-1.4)*2.0,0,4)
        pixels+=veins[:,:,None]*np.array((-.15,1.,-.25))
    elif name=='stone':
        fracture=np.exp(-(field(rng,19)*3.5)**2)*2.5
        pixels=np.array((96,94,83))[None,None,:]+variation[:,:,None]-fracture[:,:,None]
    else:
        pixels=np.array((137,124,92))[None,None,:]+variation[:,:,None]
        grains=np.clip(grain-1.9,0,1.4)*2
        pixels+=grains[:,:,None]
    return Image.fromarray(np.clip(np.rint(pixels),0,255).astype(np.uint8))

def dds(image,path):
    blobs=[]
    while True:
        out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT1');blobs.append(out.getvalue())
        if image.size==(1,1):break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    header=bytearray(blobs[0][:128]);struct.pack_into('<I',header,8,struct.unpack_from('<I',header,8)[0]|0x20000)
    struct.pack_into('<I',header,28,len(blobs));struct.pack_into('<I',header,108,0x401008)
    path.write_bytes(header+b''.join(b[128:] for b in blobs))

def signature(image):
    pixels=np.asarray(image.convert('RGB'),dtype=float)
    luminance=pixels[:,:,0]*.2126+pixels[:,:,1]*.7152+pixels[:,:,2]*.0722
    power=np.abs(np.fft.fft2(luminance-luminance.mean()))**2
    n=len(luminance)
    selected={(y%n,x%n)for y in(-4,4)for x in(-4,4)}|{(16%n,16%n),(-16%n,-16%n)}
    return float(sum(power[y,x]for y,x in selected)/power.sum())

def preview(images):
    canvas=Image.new('RGB',(1240,1090),(22,29,35));draw=ImageDraw.Draw(canvas)
    draw.text((24,16),'OWN TERRAIN MATERIAL COMPARISON / DECODED DDS / NOT ENGINE',fill=(233,234,224))
    for col,name in enumerate(('ground','stone','coast')):
        x=24+col*408
        draw.text((x,48),name.upper()+' / ORIGINAL FROZEN SINE PATTERN',fill=(182,194,195))
        old=Image.open(FRONTIER/'mod/Textures/veyra/frontier'/('frontier_'+name+'.dds')).convert('RGB')
        canvas.paste(old.resize((384,384)),(x,76))
        draw.text((x,478),name.upper()+' / OWN IRREGULAR MULTI-SCALE',fill=(232,218,168))
        canvas.paste(images[name].resize((384,384)),(x,506))
    draw.text((24,922),'The new files override three existing own texture paths only; ESP/LAND remain frozen.',fill=(183,195,196))
    draw.text((24,948),'A repeatable texture still repeats; native distance/filtering comparison is required.',fill=(183,195,196))
    draw.text((24,974),'No downloaded image, original game texture, normal map or global profile change.',fill=(183,195,196))
    canvas.save(BASE/'TEXTURE_COMPARISON.png')

def main():
    plugin=FRONTIER/'mod/LEVIATH-Frontier.esp'
    if sha(plugin)!=PLUGIN_HASH:raise ValueError('Frozen Frontier plugin differs')
    for name,expected in OLD_HASHES.items():
        if sha(FRONTIER/'mod/Textures/veyra/frontier'/('frontier_'+name+'.dds'))!=expected:
            raise ValueError('Frozen Frontier texture differs')
    folder=MOD/'Textures/veyra/frontier';folder.mkdir(parents=True,exist_ok=True)
    rows=[];images={}
    for number,name in enumerate(('ground','stone','coast')):
        path=folder/('frontier_'+name+'.dds');dds(material(name,number),path)
        images[name]=Image.open(path).convert('RGB')
        old=Image.open(FRONTIER/'mod/Textures/veyra/frontier'/path.name).convert('RGB')
        old_signature=signature(old);new_signature=signature(images[name])
        if not new_signature<old_signature*.25:raise ValueError('Original periodic signature not sufficiently reduced')
        data=path.read_bytes()
        if data[84:88]!=b'DXT1'or len(data)!=699192:raise ValueError('DDS/mip chain size')
        rows.append({'path':path.relative_to(MOD).as_posix(),'sha256':sha(path),'bytes':len(data),
                     'originalSha256':OLD_HASHES[name],'resolution':[1024,1024],'mips':11,
                     'originalSixPeakEnergyFraction':old_signature,'newSixPeakEnergyFraction':new_signature,
                     'frequencyScope':'old sine motif exact FFT bins(+/-4,+/-4) and(+/-16,+/-16); not a general tiling proof'})
        print('TEXTURE_PASS',name,'oldSignature',round(old_signature,5),'newSignature',round(new_signature,5))
    preview(images)
    if sha(plugin)!=PLUGIN_HASH:raise ValueError('Frozen Frontier changed during build')
    for name,expected in OLD_HASHES.items():
        if sha(FRONTIER/'mod/Textures/veyra/frontier'/('frontier_'+name+'.dds'))!=expected:
            raise ValueError('Frozen texture changed during build')
    receipt={'schema':'veyra.frontier-texture.v1','version':'0.1.0','seed':SEED,
             'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'generatorSha256':sha(Path(__file__)),'python':sys.version.split()[0],
             'pillow':PIL.__version__,'numpy':np.__version__,'textures':rows,
             'frontierPluginSha256':PLUGIN_HASH,'frontierFilesChanged':0,
             'generatedRecords':0,'geometryChanges':0,'sourceProfileChanges':0,
             'source':'OWN_PERIODIC_GAUSSIAN_MULTISCALE_NOISE_AND_DOMAIN_WARP',
             'sourceLicense':'MIT','nativeVisualComparison':'PENDING_ROOT_PROBE',
             'previewSha256':sha(BASE/'TEXTURE_COMPARISON.png'),
             'claimCeiling':'OWN_TEXTURE_STRUCTURE_AND_ORIGINAL_MOTIF_REDUCTION_ONLY'}
    (BASE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
