#!/usr/bin/env python3
"""MIT. Independent texture-only file/mip/base/determinism checks."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,datetime
import numpy as np
from PIL import Image
BASE=Path(__file__).resolve().parent
FRONTIER=BASE.parent/'frontier-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    before={p.relative_to(FRONTIER).as_posix():sha(p)for p in (FRONTIER/'mod').rglob('*')if p.is_file()}
    receipt=json.loads((BASE/'BUILD_RECEIPT.json').read_text())
    expected={'Textures/veyra/frontier/frontier_'+name+'.dds'for name in ('ground','stone','coast')}
    files={p.relative_to(BASE/'mod').as_posix():p for p in (BASE/'mod').rglob('*')if p.is_file()}
    assert set(files)==expected, 'Texture-only candidate has an unexpected file/record'
    first={name:sha(path)for name,path in files.items()}
    first['TEXTURE_COMPARISON.png']=sha(BASE/'TEXTURE_COMPARISON.png')
    checks=[]
    for name,path in files.items():
        row=next(row for row in receipt['textures']if row['path']==name)
        assert sha(path)==row['sha256']
        data=path.read_bytes()
        assert data[:4]==b'DDS ' and struct.unpack_from('<I',data,4)[0]==124
        assert struct.unpack_from('<II',data,12)==(1024,1024)
        assert struct.unpack_from('<I',data,28)[0]==11 and data[84:88]==b'DXT1'
        assert len(data)==128+sum(max(1,(1024//2**i+3)//4)**2*8 for i in range(11))
        pixels=np.asarray(Image.open(path).convert('RGB'),dtype=float)
        internal=float((np.abs(np.diff(pixels,axis=0)).mean()+np.abs(np.diff(pixels,axis=1)).mean())/2)
        border=float((np.abs(pixels[0]-pixels[-1]).mean()+np.abs(pixels[:,0]-pixels[:,-1]).mean())/2)
        assert border<max(3.,internal*3), 'Decoded seam jump disproportionate to local texture differences'
        assert row['newSixPeakEnergyFraction']<row['originalSixPeakEnergyFraction']*.25
        checks.append({'path':name,'sha256':sha(path),'decodedMeanRGB':pixels.mean(axis=(0,1)).tolist(),
                       'decodedMeanInternalNeighbourDifference':internal,'decodedMeanTileBorderDifference':border,
                       'borderBound':'less than max(3 RGB units, three times internal adjacent-pixel mean)',
                       'originalSineMotifReduction':'PASS_SCOPE_SIX_EXACT_FFT_PEAKS'})
    process=subprocess.run([sys.executable,str(BASE/'build-textures.py')],capture_output=True,text=True,timeout=90)
    assert process.returncode==0,process.stdout+process.stderr
    second={name:sha(path)for name,path in files.items()}
    second['TEXTURE_COMPARISON.png']=sha(BASE/'TEXTURE_COMPARISON.png')
    assert first==second,'Repeat texture-build bytes differ'
    after={p.relative_to(FRONTIER).as_posix():sha(p)for p in (FRONTIER/'mod').rglob('*')if p.is_file()}
    assert before==after,'Frozen Frontier changed'
    result={'schema':'veyra.frontier-texture-check.v1','version':'0.1.0',
            'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'checkerSha256':sha(Path(__file__)),'generatorSha256':sha(BASE/'build-textures.py'),
            'status':'TEXTURE_ONLY_DDS_AND_REPEAT_BYTES_PASS_NATIVE_PENDING','checks':checks,
            'comparedOutputHashes':second,'frozenFrontierFilesUnchanged':len(before),
            'newTES3Records':0,'geometryChanged':0,'nativeEngineStarted':False,
            'claimCeiling':'TEXTURE_BYTES_AND_DECLARED_LOCAL_PIXEL_METRICS_ONLY'}
    (BASE/'CHECK_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('TEXTURE_CHECK_PASS threeDDS11mips fourRepeatOutputs frozenFrontierUnchanged nativePENDING')

if __name__=='__main__':main()
