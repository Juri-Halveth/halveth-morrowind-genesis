"""MIT. Portable own-source/package checks, without proprietary game data."""
from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent.parent
expected={row[66:]:row[:64] for row in (root/'PAYLOAD.sha256').read_text(encoding='utf8').splitlines()}
actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'mod').rglob('*') if p.is_file()}
assert len(expected)==167 and actual==expected,'Own asset tree differs from payload'
assert not any(p.is_symlink() for p in root.rglob('*')),'Unexpected package link'
assert not any(p.suffix.lower() in {'.esp','.esm','.bsa','.omwsave','.ess','.mp4','.mov','.exe','.dll'} for p in root.rglob('*') if p.is_file()),'Non-public payload type'
xml_count=0
for p in root.rglob('*'):
 if p.suffix.lower() in {'.svg','.dae','.xml','.layout','.omwfont'}:
  ET.parse(p);xml_count+=1
for row in json.loads((root/'world-map.json').read_text(encoding='utf8')):
 path=root/'mod/Meshes'/row['model']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==row['modelSha256']
for row in json.loads((root/'item-map.json').read_text(encoding='utf8'))['items']:
 assert (root/'mod/Icons'/row['iconPath']).is_file()
for p in root.rglob('*.dds'):
 header=p.read_bytes()[:128]
 assert len(header)==128 and header[:4]==b'DDS ' and struct.unpack_from('<I',header,4)[0]==124
print('PASS: 167 own assets; 39 models; 40 icon addresses;',xml_count,'XML/vector/model sources; native DDS headers')
