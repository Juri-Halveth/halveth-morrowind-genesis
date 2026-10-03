"""Produce the owned, uncompressed white TGA used to tint native UI rectangles."""
from pathlib import Path
import hashlib
import json
import struct

root = Path(__file__).resolve().parent
target = root / 'mod/Textures/veyra/white.tga'
target.parent.mkdir(parents=True, exist_ok=True)
header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, 1, 1, 32, 0x28)
data = header + bytes((255, 255, 255, 255))
target.write_bytes(data)
receipt = {'asset': 'Textures/veyra/white.tga', 'width': 1, 'height': 1,
           'channels': 'BGRA', 'bytes': len(data),
           'sha256': hashlib.sha256(data).hexdigest(), 'source': 'procedural own code',
           'license': 'MIT', 'thirdPartyAssets': 0}
(root / 'ASSET_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
print('OWN_ASSET_PASS', len(data), 'bytes')
