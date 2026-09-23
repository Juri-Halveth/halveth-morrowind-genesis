"""Read-only terrain-material atlas for a licensed TES3 plugin.

The output is local design input, never a texture, world hash or distributable
copy of the game's LAND records. Co-occurrence means same exterior cell; it
does not claim that two texture patches touch in world space.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.survey_universe import scan,decode


def atlas(source: Path) -> dict:
    names={}
    cells={}
    lands={}
    for tag,_,_,flags,parts,_ in scan(source):
        fields=dict(parts)
        if tag==b'LTEX' and len(fields.get(b'INTV',b''))==4:
            index=struct.unpack('<i',fields[b'INTV'])[0]
            names[index]=decode(fields.get(b'DATA',b'')).replace('\\','/').lower()
        elif tag==b'CELL' and len(fields.get(b'DATA',b''))>=12:
            flags,x,y=struct.unpack_from('<Iii',fields[b'DATA'])
            if not flags&1:
                cells[(x,y)]=decode(fields.get(b'NAME',b''))
        elif tag==b'LAND' and len(fields.get(b'INTV',b''))==8:
            xy=struct.unpack('<ii',fields[b'INTV'])
            raw=fields.get(b'VTEX',b'')
            if len(raw)==512:
                lands[xy]=Counter(struct.unpack('<256H',raw))
    usage=Counter()
    for counts in lands.values(): usage.update(counts)
    entries=[]
    for (x,y),counts in sorted(lands.items()):
        entries.append({'x':x,'y':y,'cell':cells.get((x,y),''),
            'terrainTiles':sum(counts.values()),
            'materials':[{'index':index,'texture':names.get(index,'UNKNOWN'),
                'tiles':n} for index,n in counts.most_common()]})
    return {'schema':'halveth.local.terrain-atlas/1',
        'recordedAt':datetime.now(timezone.utc).isoformat(),
        'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'sourceBytes':source.stat().st_size,
        'exteriorLandCells':len(entries),'terrainTiles':sum(usage.values()),
        'materialUsage':[{'index':index,'texture':names.get(index,'UNKNOWN'),
            'tiles':n} for index,n in usage.most_common()],
        'cells':entries,
        'interpretation':'Read-only source snapshot. A material count is not a visual comparison or proof that a new DDS wins the active load order.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esm',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'.local/cartography/terrain-atlas.json')
    args=parser.parse_args()
    source=args.esm.resolve()
    if not source.is_file() or source.suffix.lower() not in {'.esm','.esp'}:
        parser.error('Provide an existing licensed ESM or ESP.')
    result=atlas(source)
    target=args.output.resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(target),'sourceSha256':result['sourceSha256'],
        'exteriorLandCells':result['exteriorLandCells'],
        'terrainTiles':result['terrainTiles'],
        'materialKinds':len(result['materialUsage'])},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
