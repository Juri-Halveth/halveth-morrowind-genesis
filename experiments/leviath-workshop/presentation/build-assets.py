"""MIT. Produce a 32x32 owned RGBA PNG for native UI tint rectangles."""
from pathlib import Path
import hashlib
import json
import struct
import zlib

root = Path(__file__).resolve().parent
target = root / 'mod/Textures/veyra/white.png'
target.parent.mkdir(parents=True, exist_ok=True)
def chunk(kind, payload):
    return struct.pack('>I',len(payload)) + kind + payload + struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)

width = height = 32
pixels = (b'\x00' + b'\xff\xff\xff\xff'*width)*height
data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
        + chunk(b'IDAT',zlib.compress(pixels,9)) + chunk(b'IEND',b''))
target.write_bytes(data)
receipt = {'schema':'veyra.own-ui-texture.v2','version':'0.1.2',
           'asset': 'Textures/veyra/white.png', 'width': width, 'height': height,
           'format':'PNG','channels': 'RGBA', 'bitDepth':8,'bytes': len(data),
           'sha256': hashlib.sha256(data).hexdigest(), 'source': 'procedural own code',
           'license': 'MIT', 'thirdPartyAssets': 0,
           'generatorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'nativeDecoding':'PENDING_ROOT_PROBE',
           'replaces':'white.tga failed native loader code1 in probe-20261003T014334'}
(root / 'ASSET_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
print('OWN_ASSET_PASS', len(data), 'bytes')
