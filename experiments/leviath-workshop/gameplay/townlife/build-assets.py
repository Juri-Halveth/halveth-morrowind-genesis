"""MIT. Generate the own white RGBA texture required by the resident panel."""
from pathlib import Path
import hashlib
import struct
import zlib

def chunk(name, raw):
    return struct.pack('>I', len(raw)) + name + raw + struct.pack('>I', zlib.crc32(name + raw))

def main():
    raw = b'\x89PNG\r\n\x1a\n'
    raw += chunk(b'IHDR', struct.pack('>IIBBBBB', 32, 32, 8, 6, 0, 0, 0))
    raw += chunk(b'IDAT', zlib.compress((b'\0' + b'\xff' * 128) * 32, 9))
    raw += chunk(b'IEND', b'')
    output = Path(__file__).resolve().parent / 'mod/Textures/veyra_townlife/white.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_bytes() != raw:
        raise ValueError('Existing own texture differs; retain for review')
    if not output.exists():
        with output.open('xb') as stream:
            stream.write(raw)
    print('OWN_TOWN_PANEL_PNG_PASS', len(raw), hashlib.sha256(raw).hexdigest())

if __name__ == '__main__':
    main()
