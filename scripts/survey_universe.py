"""Enumerate every record/subrecord in the active TES3 load order, read-only.

The private SQLite catalogue binds bytes, record revisions and source positions.
The summary counts coverage; it does not claim to optimize or understand every
script, asset, possible runtime variable or quest branch. No source is executed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.import_lore import from_config


def scan(path):
    with Path(path).open('rb') as source:
        total=Path(path).stat().st_size
        while source.tell()<total:
            offset=source.tell();header=source.read(16)
            if len(header)!=16: raise ValueError('Incomplete TES3 record header')
            tag,size,unknown,flags=struct.unpack('<4sIII',header)
            if size>64*1024*1024 or source.tell()+size>total: raise ValueError('Invalid TES3 record bounds')
            raw=source.read(size);parts=[];cursor=0
            while cursor<len(raw):
                if len(raw)-cursor<8: raise ValueError('Incomplete TES3 subrecord header')
                key,length=struct.unpack_from('<4sI',raw,cursor);cursor+=8
                if cursor+length>len(raw): raise ValueError('Invalid TES3 subrecord bounds')
                parts.append((key,raw[cursor:cursor+length]));cursor+=length
            yield tag,offset,size+16,flags,parts,hashlib.sha256(header+raw).hexdigest()


def decode(value): return value.rstrip(b'\0').decode('cp1252',errors='replace')


def identity(tag,parts,topic,ordinal):
    fields={}
    for key,value in parts: fields.setdefault(key,value)
    if tag==b'TES3': return 'header',True
    if tag==b'INFO': return topic.casefold()+':'+decode(fields.get(b'INAM',b'')).casefold(),bool(fields.get(b'INAM'))
    if tag in (b'SKIL',b'MGEF') and len(fields.get(b'INDX',b''))==4:
        return str(struct.unpack('<i',fields[b'INDX'])[0]),True
    if tag==b'SCPT' and b'SCHD' in fields: return decode(fields[b'SCHD'][:32]).casefold(),True
    if tag==b'LAND' and len(fields.get(b'INTV',b''))==8:
        return ','.join(map(str,struct.unpack('<ii',fields[b'INTV']))),True
    if tag==b'CELL' and len(fields.get(b'DATA',b''))>=12:
        flags,x,y=struct.unpack_from('<Iii',fields[b'DATA'])
        return ('interior:'+decode(fields.get(b'NAME',b'')).casefold() if flags&1 else f'exterior:{x},{y}'),True
    # Path grids can share names with distinct exterior coordinates.
    if tag==b'PGRD':
        return f"{decode(fields.get(b'NAME',b'')).casefold()}:{fields.get(b'DATA',b'')[:8].hex()}",True
    if fields.get(b'NAME'): return decode(fields[b'NAME']).casefold(),True
    return 'source-position:'+str(ordinal),False


def survey(paths,destination):
    destination=Path(destination)
    if destination.exists(): raise FileExistsError('Use a fresh survey directory to preserve earlier observations')
    destination.mkdir(parents=True)
    db=sqlite3.connect(destination/'records.sqlite3')
    db.executescript('''CREATE TABLE records(source TEXT, ordinal INTEGER, kind TEXT, identity TEXT,
        sourceOffset INTEGER, bytes INTEGER, flags INTEGER, deleted INTEGER, sha256 TEXT,
        subrecordLayout TEXT, semanticIdentity INTEGER);
        CREATE INDEX record_identity ON records(kind,identity);
        CREATE TABLE effective(kind TEXT, identity TEXT, source TEXT, ordinal INTEGER, PRIMARY KEY(kind,identity));''')
    families=Counter();subrecords=Counter();sources=[];byte_count=0;count=0;deleted=0;fallback=0
    effective={};npc_heads={};body_models={}
    try:
        with db:
            for path in map(Path,paths):
                topic='';kinds=Counter();source_count=0;source_bytes=0
                for ordinal,(tag,offset,length,flags,parts,digest) in enumerate(scan(path)):
                    kind=tag.decode('ascii');fields={}
                    for key,value in parts: fields.setdefault(key,value)
                    if tag==b'DIAL': topic=decode(fields.get(b'NAME',b''))
                    record_id,semantic=identity(tag,parts,topic,ordinal)
                    is_deleted=b'DELE' in fields or bool(flags&0x20)
                    layout=[(key.decode('ascii'),len(value)) for key,value in parts]
                    db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (path.name,ordinal,kind,record_id,offset,length,flags,int(is_deleted),digest,json.dumps(layout),int(semantic)))
                    count+=1;source_count+=1;byte_count+=length;source_bytes+=length;kinds[kind]+=1;families[kind]+=1
                    subrecords.update(key for key,_ in layout);deleted+=is_deleted;fallback+=not semantic
                    if tag!=b'TES3' and semantic:
                        key=(kind,record_id)
                        if is_deleted: effective.pop(key,None)
                        else: effective[key]=(path.name,ordinal)
                    if tag==b'NPC_':
                        if is_deleted: npc_heads.pop(record_id,None)
                        else: npc_heads[record_id]=(decode(fields.get(b'BNAM',b'')).casefold(),decode(fields.get(b'KNAM',b'')).casefold())
                    if tag==b'BODY':
                        if is_deleted: body_models.pop(record_id,None)
                        else: body_models[record_id]=(decode(fields.get(b'MODL',b'')),path.name)
                if source_bytes!=path.stat().st_size: raise ValueError('Byte coverage mismatch: '+path.name)
                sources.append({'file':path.name,'bytes':source_bytes,'records':source_count,'recordTypes':dict(sorted(kinds.items())),
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            db.executemany('INSERT INTO effective VALUES(?,?,?,?)',[(kind,id,source,ordinal) for (kind,id),(source,ordinal) in effective.items()])
        effective_counts=Counter(kind for kind,_ in effective)
        enhanced_heads=sum(bool(head and body_models.get(head,('',''))[1]=='HALVETH-Beautiful-Heads.esp') for head,hair in npc_heads.values())
        enhanced_hair=sum(bool(hair and body_models.get(hair,('',''))[1]=='HALVETH-Beautiful-Heads.esp') for head,hair in npc_heads.values())
        summary={'schema':'halveth.morrowind.universe-survey/1','recordedAt':datetime.now(timezone.utc).isoformat(),
            'sourceFiles':sources,'sourceBytesCovered':byte_count,'recordsWalked':count,'recordTypeCount':len(families),
            'recordTypes':dict(sorted(families.items())),'subrecordsWalked':sum(subrecords.values()),
            'subrecordTypes':dict(sorted(subrecords.items())),'semanticIdentityFallbacks':fallback,'deletionRecords':deleted,
            'effectiveRecordCounts':dict(sorted(effective_counts.items())),
            'appearance':{'npcDefinitions':len(npc_heads),'headsUsingInstalledAdapter':enhanced_heads,'hairUsingInstalledAdapter':enhanced_hair,
                          'scope':'Resolved BODY model assignments in active load order; not a visual check of every NPC.'},
            'coverage':'Every byte of the listed TES3 plugins walked as record/subrecord structure. Effective identities tracked for supported records.',
            'unknownFrontiers':['BSA texture/mesh/sound decoding','Every possible runtime branch of scripts and quests','Rendered appearance and animation of every NPC','Engine C++ source not included in game records'],
            'sourceMutations':0}
        (destination/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
        return summary
    finally: db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summary=survey(from_config(args.config),args.output)
    print(json.dumps({key:summary[key] for key in ('sourceBytesCovered','recordsWalked','subrecordsWalked','recordTypeCount','semanticIdentityFallbacks','effectiveRecordCounts','appearance')},indent=2))
