#!/usr/bin/env python3
"""MIT. Check the complete owned PNG contract without third-party packages."""
from pathlib import Path
import hashlib
import json
import struct
import zlib

root=Path(__file__).resolve().parent
path=root/'mod/Textures/veyra/white.png'
data=path.read_bytes()
assert data[:8]==b'\x89PNG\r\n\x1a\n'
offset=8
chunks=[]
while offset<len(data):
    size=struct.unpack('>I',data[offset:offset+4])[0]
    kind=data[offset+4:offset+8]
    payload=data[offset+8:offset+8+size]
    crc=struct.unpack('>I',data[offset+8+size:offset+12+size])[0]
    assert crc==(zlib.crc32(kind+payload)&0xffffffff)
    chunks.append((kind,payload));offset+=size+12
assert offset==len(data)
assert [kind for kind,_ in chunks]==[b'IHDR',b'IDAT',b'IEND']
width,height,depth,color,compression,filter_,interlace=struct.unpack('>IIBBBBB',chunks[0][1])
assert (width,height,depth,color,compression,filter_,interlace)==(32,32,8,6,0,0,0)
assert chunks[-1][1]==b''
decoded=zlib.decompress(chunks[1][1])
assert decoded==(b'\x00'+b'\xff\xff\xff\xff'*width)*height
receipt=json.loads((root/'ASSET_RECEIPT.json').read_text())
assert receipt['sha256']==hashlib.sha256(data).hexdigest() and receipt['bytes']==len(data)
print('PNG_STRUCTURE_PASS width=32 height=32 rgba=white crc=PASS bytes='+str(len(data)))
