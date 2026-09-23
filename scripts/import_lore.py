"""Index owned local TES3 books/dialogue/character records; never execute script text.
Generated copyrighted corpus stays inside .local and is excluded from release archives.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store


def records(path):
    with Path(path).open('rb') as stream:
        total=Path(path).stat().st_size
        while header:=stream.read(16):
            if len(header)!=16:
                raise ValueError('Incomplete TES3 header')
            tag,size,_,flags=struct.unpack('<4sIII',header)
            if size>64*1024*1024 or stream.tell()+size>total:
                raise ValueError('Invalid TES3 record length')
            payload=stream.read(size)
            if tag not in {b'TES3',b'BOOK',b'DIAL',b'INFO',b'NPC_',b'CREA',b'CELL'}:
                continue
            sub={}
            cursor=0
            while cursor<len(payload):
                if cursor+8>len(payload):
                    raise ValueError('Incomplete TES3 subrecord')
                key,n=struct.unpack_from('<4sI',payload,cursor)
                cursor+=8
                if cursor+n>len(payload):
                    raise ValueError('Invalid TES3 subrecord length')
                sub.setdefault(key,[]).append(payload[cursor:cursor+n])
                cursor+=n
            yield tag,flags,sub


def text(sub,key):
    return sub.get(key,[b''])[0].rstrip(b'\0').decode('cp1252',errors='replace')


def index(paths,state_dir):
    store=Store(Path(state_dir)/'universe.sqlite3')
    rows={}
    receipts=[]
    import re
    for path in paths:
        path=Path(path)
        receipt={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'records':0}
        topic=''
        for tag,flags,sub in records(path):
            receipt['records']+=1
            if tag==b'DIAL':
                topic=text(sub,b'NAME')
                continue
            if tag==b'BOOK':
                identity='book:'+text(sub,b'NAME')
                title=text(sub,b'FNAM')
                body=html.unescape(re.sub('<[^>]+>',' ',text(sub,b'TEXT')))
            elif tag==b'INFO':
                identity='dialogue:'+topic+':'+text(sub,b'INAM')
                actor=text(sub,b'ONAM')
                title=topic+(' · '+actor if actor else '')
                body=text(sub,b'NAME')
                body+='\nDialogfilter: '+json.dumps({key.decode():text(sub,key) for key in (b'ONAM',b'RNAM',b'CNAM',b'FNAM',b'ANAM') if text(sub,key)},ensure_ascii=False)
                # These are source dialogue candidates, NOT evaluated runtime availability.
                body+='\nVerfügbarkeit im aktuellen Spielzustand: nicht ausgewertet.'
            elif tag in {b'NPC_',b'CREA'}:
                identity='actor:'+text(sub,b'NAME')
                title=text(sub,b'FNAM') or text(sub,b'NAME')
                body=json.dumps({key.decode():text(sub,key) for key in (b'NAME',b'FNAM',b'RNAM',b'CNAM',b'ANAM',b'BNAM') if text(sub,key)},ensure_ascii=False)
            else:
                continue
            if b'DELE' in sub or flags&0x20:
                rows.pop(identity,None)
            elif body.strip():
                rows[identity]=(identity,title,body,path.name)
        receipts.append(receipt)
    with store.connect() as db:
        db.execute('DELETE FROM lore')
        db.executemany('INSERT INTO lore VALUES(?,?,?,?)',rows.values())
        db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('lore_import',json.dumps(receipts)))
    receipt={'schema':'halveth.lore.import.v1','entries':len(rows),'sources':receipts,
             'scope':'Books, dialogue and actor definitions from listed load-order files; dialogue conditions not evaluated; no BSA textures or scripts executed.'}
    Path(state_dir).mkdir(parents=True,exist_ok=True)
    (Path(state_dir)/'lore-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


def from_config(path):
    import re
    directories=[]
    contents=[]
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if line.startswith('data='):
            directory=Path(line[5:].strip().strip('"').replace('&"','"').replace('&&','&'))
            directories.append(directory if directory.is_absolute() else Path(path).parent/directory)
        elif line.startswith('content=') and line.lower().endswith(('.esm','.esp','.omwaddon','.omwgame')):
            contents.append(line[8:].strip())
    result=[]
    for name in contents:
        found=next((directory/name for directory in reversed(directories) if (directory/name).is_file()),None)
        if found is None:
            raise ValueError('Active content file missing: '+name)
        result.append(found)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path)
    parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('files',type=Path,nargs='*')
    args=parser.parse_args()
    paths=from_config(args.config) if args.config else args.files
    if not paths:
        parser.error('No source files selected')
    print(json.dumps(index(paths,args.state_dir),indent=2))
