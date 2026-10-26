#!/usr/bin/env python3
"""MIT. Independent byte decoder and bounded additive-world acceptance checks."""
from pathlib import Path
from collections import Counter
import argparse
import datetime
import hashlib
import json
import math
import struct

BASE = Path(__file__).resolve().parent
TARGET = {(x, y) for x in range(64, 68) for y in range(-64, -60)}
OWN_IDS = {'veyra_frontier_region', 'veyra_frontier_ground',
           'veyra_frontier_stone', 'veyra_frontier_coast', 'leviath frontier entry'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def parse_records(data):
    result = []
    cursor = 0
    while cursor < len(data):
        require(cursor + 16 <= len(data), 'Truncated record header')
        kind, size, unknown, flags = struct.unpack_from('<4sIII', data, cursor)
        cursor += 16
        require(cursor + size <= len(data), 'Truncated record body')
        result.append((kind, unknown, flags, data[cursor:cursor+size]))
        cursor += size
    require(cursor == len(data), 'Trailing bytes')
    return result

def parse_subs(data):
    result = []
    cursor = 0
    while cursor < len(data):
        require(cursor + 8 <= len(data), 'Truncated subrecord header')
        kind, size = struct.unpack_from('<4sI', data, cursor)
        cursor += 8
        require(cursor + size <= len(data), 'Truncated subrecord body')
        result.append((kind, data[cursor:cursor+size]))
        cursor += size
    require(len({k for k, _ in result}) == len(result), 'Unexpected repeated candidate subrecord')
    return result

def string(data):
    require(data.endswith(b'\0') and b'\0' not in data[:-1], 'Invalid terminated candidate string')
    return data[:-1].decode('ascii')

def weather_contract(version_bytes, weather):
    # The own candidate promises the 0.51 writer convention: VER_120 has8;
    # VER_130 has10. The engine reader also tolerates8 under newer headers.
    expected = {struct.pack('<f', 1.2): 8, struct.pack('<f', 1.3): 10}
    require(version_bytes in expected, 'Unsupported candidate HEDR version')
    require(len(weather) == expected[version_bytes], 'HEDR/WEAT writer-contract mismatch')
    require(sum(weather) == 100, 'Weather probability sum differs')

def decode_heights(payload):
    require(len(payload) == 4232, 'VHGT length')
    offset = struct.unpack_from('<f', payload)[0]
    require(math.isfinite(offset) and offset == int(offset), 'Invalid VHGT offset')
    require(payload[-3:] == b'\0\0\0', 'VHGT reserved bytes')
    delta = struct.unpack_from('<4225b', payload, 4)
    result = []
    row_start = int(offset)
    for row in range(65):
        row_start += delta[row * 65]
        accumulator = row_start
        decoded = [accumulator * 8]
        for value in delta[row*65+1:row*65+65]:
            accumulator += value
            decoded.append(accumulator * 8)
        result.append(decoded)
    return result, delta

def decode_palette(payload):
    require(len(payload) == 512, 'VTEX length')
    block = struct.unpack('<256H', payload)
    # Calculate a row-major destination's source address from its4x4 block.
    return [[block[((y//4)*4+x//4)*16+(y%4)*4+x%4]
             for x in range(16)] for y in range(16)]

def check_dds(path):
    data = path.read_bytes()
    require(data[:4] == b'DDS ' and len(data) >= 128, 'DDS signature')
    require(struct.unpack_from('<I', data, 4)[0] == 124, 'DDS header size')
    flags, height, width = struct.unpack_from('<III', data, 8)
    mips = struct.unpack_from('<I', data, 28)[0]
    require((width, height, mips) == (512, 512, 10), 'DDS dimensions/mips')
    require(flags & 0x20000, 'DDS mip count flag')
    require(struct.unpack_from('<I', data, 76)[0] == 32 and data[84:88] == b'DXT1', 'DDS DXT1 pixel format')
    require(struct.unpack_from('<I', data, 108)[0] == 0x401008, 'DDS mip caps')
    expected = 128 + sum(max(1, (512//(2**i)+3)//4)**2*8 for i in range(10))
    require(len(data) == expected, 'DDS chain byte length')
    return {'sha256': digest(path), 'bytes': len(data), 'format': 'DXT1',
            'width': width, 'height': height, 'mips': mips}

def validate_plugin(data, build, entry, mod):
    records = parse_records(data)
    require(Counter(r[0] for r in records) ==
            {b'TES3': 1, b'REGN': 1, b'LTEX': 3, b'CELL': 16, b'LAND': 16}, 'Record counts/types')
    require(all(r[1] == r[2] == 0 for r in records), 'Unknown/flagged/deleted candidate record')
    require(records[0][0] == b'TES3', 'Missing first TES3 header')
    header = parse_subs(records[0][3])
    require([k for k, _ in header] == [b'HEDR', b'MAST', b'DATA'], 'TES3 header schema')
    h = dict(header)
    require(len(h[b'HEDR']) == 300, 'HEDR length')
    version = h[b'HEDR'][:4]
    require(version.hex() == '6666a63f', 'Exact authored TES3_1.3 bytes')
    require(struct.unpack_from('<I', h[b'HEDR'], 4)[0] == 0, 'ESP file type')
    require(struct.unpack_from('<I', h[b'HEDR'], 296)[0] == 36, 'HEDR body record count')
    require(string(h[b'MAST']) == 'Morrowind.esm' and len(h[b'DATA']) == 8, 'Master dependency')
    master = next(r for r in build['contentBinding'] if r['content'] == 'Morrowind.esm')
    require(struct.unpack('<Q', h[b'DATA'])[0] == master['bytes'], 'Master size binding')
    ids = set()
    cells = {}
    lands = {}
    ltex = {}
    for kind, _, _, body in records[1:]:
        ordered = parse_subs(body)
        s = dict(ordered)
        require(b'DELE' not in s and b'FRMR' not in s, 'Deleted/source cell reference imported')
        if b'NAME' in s and string(s[b'NAME']):
            own_id = string(s[b'NAME']).casefold()
            require(own_id in OWN_IDS and own_id not in ids, 'Unexpected/duplicate own ID')
            ids.add(own_id)
        if kind == b'REGN':
            require([k for k, _ in ordered] == [b'NAME', b'FNAM', b'WEAT', b'CNAM'], 'REGN schema')
            require(string(s[b'NAME']) == 'veyra_frontier_region', 'Region ID')
            require(string(s[b'FNAM']) == 'LEVIATH Frontier' and len(s[b'CNAM']) == 4, 'Region display/map colour')
            weather_contract(version, s[b'WEAT'])
            require(s[b'WEAT'] == bytes((60,30,10,0,0,0,0,0,0,0)), 'Own weather contract')
        elif kind == b'LTEX':
            require([k for k, _ in ordered] == [b'NAME', b'INTV', b'DATA'], 'LTEX schema')
            require(len(s[b'INTV']) == 4, 'LTEX INTV size')
            index = struct.unpack('<I', s[b'INTV'])[0]
            require(index not in ltex and index in range(3), 'LTEX local index')
            material = ('ground', 'stone', 'coast')[index]
            require(string(s[b'NAME']) == 'veyra_frontier_' + material, 'LTEX index/ID contract')
            require(string(s[b'DATA']) == 'veyra/frontier/frontier_' + material + '.dds', 'LTEX own path')
            ltex[index] = check_dds(mod / 'Textures' / string(s[b'DATA']))
        elif kind == b'CELL':
            require([k for k, _ in ordered] == [b'NAME', b'DATA', b'RGNN'], 'CELL schema; reference-free terrain')
            require(len(s[b'DATA']) == 12, 'CELL DATA size')
            flags, x, y = struct.unpack('<Iii', s[b'DATA'])
            require(flags == 2 and (x,y) in TARGET and (x,y) not in cells, 'Exterior CELL flags/coordinate')
            require(string(s[b'RGNN']) == 'veyra_frontier_region', 'CELL region link')
            require(string(s[b'NAME']) == ('LEVIATH Frontier Entry' if (x,y)==(65,-63) else ''), 'CELL entry name')
            cells[x,y] = s
        elif kind == b'LAND':
            require([k for k, _ in ordered] == [b'INTV', b'DATA', b'VNML', b'VHGT', b'WNAM', b'VCLR', b'VTEX'], 'LAND schema')
            require(len(s[b'INTV']) == 8 and len(s[b'DATA']) == 4, 'LAND header size')
            coordinate = struct.unpack('<ii', s[b'INTV'])
            require(coordinate in TARGET and coordinate not in lands, 'LAND coordinate')
            require(struct.unpack('<I', s[b'DATA'])[0] == 7, 'LAND data flags')
            require(len(s[b'VNML']) == len(s[b'VCLR']) == 12675 and len(s[b'WNAM']) == 81, 'LAND normal/colour/LOD length')
            require(s[b'VCLR'] == b'\xff'*12675, 'Own white vertex colours')
            grid, delta = decode_heights(s[b'VHGT'])
            row = next(r for r in build['cells'] if r['coordinates'] == list(coordinate))
            packed = struct.pack('<4225i', *(v for line in grid for v in line))
            require(hashlib.sha256(packed).hexdigest() == row['heightGridSha256'], 'Serialized VHGT differs from build height grid')
            require([min(delta), max(delta)] == row['heightDeltaRange'], 'VHGT delta range')
            palette = decode_palette(s[b'VTEX'])
            require({v for line in palette for v in line} <= {1,2,3}, 'VTEX palette imports default/foreign material')
            lod = struct.unpack('<81b', s[b'WNAM'])
            for index, value in enumerate(lod):
                # Explicit engine WNAM sample addressing and truncating cast.
                hgt = grid[int((index//9)*64/9)][int((index%9)*64/9)]
                expected = max(-128, min(127, int(hgt/(128 if hgt > 0 else 16))))
                require(value == expected, 'WNAM sample differs from height field')
            normals = struct.unpack('<12675b', s[b'VNML'])
            for i in range(0, len(normals), 3):
                nx,ny,nz = normals[i:i+3]
                require(nz > 0 and abs(math.sqrt(nx*nx+ny*ny+nz*nz)-127) <= 1.0, 'Invalid quantized upward terrain normal')
            lands[coordinate] = {'grid':grid, 'normal':normals, 'palette':palette}
    require(ids == OWN_IDS and set(cells) == set(lands) == TARGET and set(ltex) == {0,1,2}, 'ID/cell/LAND/palette closure')
    global_grid = [[None]*257 for _ in range(257)]
    global_normals = [[None]*257 for _ in range(257)]
    repeated_vertices = 0
    for (x,y), land in lands.items():
        for local_y, line in enumerate(land['grid']):
            for local_x, height in enumerate(line):
                gx, gy = (x-64)*64+local_x, (y+64)*64+local_y
                normal = land['normal'][(local_y*65+local_x)*3:(local_y*65+local_x)*3+3]
                if global_grid[gy][gx] is not None:
                    require(global_grid[gy][gx] == height, 'Shared height edge seam')
                    require(global_normals[gy][gx] == normal, 'Shared normal edge seam')
                    repeated_vertices += 1
                else:
                    global_grid[gy][gx] = height
                    global_normals[gy][gx] = normal
    require(all(v is not None for line in global_grid for v in line), 'Global heightfield hole')
    require(all(global_grid[0][i] == global_grid[-1][i] == global_grid[i][0] == global_grid[i][-1] == -2048 for i in range(257)), 'Outer border mismatch')
    flat_count = 0
    for y in range(257):
        for x in range(257):
            if math.hypot((x-128)*128, (y-128)*128) <= 6200:
                require(global_grid[y][x] == 320, 'Central architecture pad not flat')
                flat_count += 1
    require(entry['cellCoordinates'] == [65,-63] and entry['cellName'] == 'LEVIATH Frontier Entry', 'Entry cell contract')
    position = entry['position']
    require(position == {'x':536576,'y':-512000,'z':576}, 'Entry position changed')
    require(global_grid[96][96] == entry['terrainHeight'] == 320 and entry['verticalMargin'] == position['z']-320 == 256, 'Entry decoded height/margin')
    require(entry['automaticTeleport'] is False and entry['networkEffects'] == 0, 'Terrain introduces action/network')
    return {'cellCount':len(cells), 'sharedVertexChecks':repeated_vertices, 'globalVertexCount':257**2,
            'flatPadVertexCount':flat_count, 'textures':ltex,
            'decodedHeightRange':[min(map(min,global_grid)),max(map(max,global_grid))],
            'paletteValues':sorted({v for land in lands.values() for line in land['palette'] for v in line})}

def check_base(config, build):
    require(digest(config) == build['baseConfigSha256'], 'Source profile changed')
    directories = []
    names = []
    for raw in config.read_text(encoding='utf-8-sig').splitlines():
        raw = raw.strip()
        if not raw or raw.startswith('#') or '=' not in raw:
            continue
        key, value = raw.split('=', 1)
        value = value.strip().strip('"')
        if key == 'data':
            directories.append(Path(value))
        elif key == 'content' and value.lower().endswith(('.esp','.esm')):
            names.append(value)
        elif key in ('config','replace'):
            raise ValueError('Independent base adapter accepts this single bound config only')
    names = list(dict.fromkeys(names))
    require(names == [r['content'] for r in build['contentBinding']], 'Effective content order changed')
    for name, row in zip(names, build['contentBinding']):
        path = next((d/name for d in reversed(directories) if (d/name).is_file()), None)
        require(path is not None and digest(path) == row['sha256'], 'Bound base content changed: '+name)
        for kind, _, _, body in parse_records(path.read_bytes()):
            if kind not in (b'CELL',b'LAND',b'REGN',b'LTEX'):
                continue
            # Existing CELLs may have many repeated reference subrecords.
            cursor = 0
            while cursor < len(body):
                key, size = struct.unpack_from('<4sI', body, cursor)
                value = body[cursor+8:cursor+8+size]
                cursor += 8+size
                if key == b'NAME' and kind in (b'CELL',b'REGN',b'LTEX'):
                    require(value.rstrip(b'\0').decode('cp1252').casefold() not in OWN_IDS, 'Own record ID collides with base')
                    if kind != b'CELL':
                        break
                if key == b'DATA' and kind == b'CELL':
                    flags,x,y = struct.unpack('<Iii', value)
                    require(flags & 1 or (x,y) not in TARGET, 'Existing exterior CELL collision')
                    break
                if key == b'INTV' and kind == b'LAND':
                    require(struct.unpack('<ii', value) not in TARGET, 'Existing LAND collision')
                    break
        require(digest(path) == row['sha256'], 'Base changed during independent scan')
    require(digest(config) == build['baseConfigSha256'], 'Source profile changed during scan')
    return len(names)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-config', type=Path, required=True)
    args = parser.parse_args()
    mod = BASE/'mod'
    build = json.loads((BASE/'BUILD_RECEIPT.json').read_text())
    entry = json.loads((BASE/'ENTRY.json').read_text())
    plugin = mod/'LEVIATH-Frontier.esp'
    require(digest(BASE/'build-frontier.py') == build['generatorSha256'], 'Generator receipt stale')
    require(digest(BASE/'ENTRY.json') == build['entryManifestSha256'], 'Entry receipt stale')
    require(digest(plugin) == entry['pluginSha256'], 'Entry/plugin hash differs')
    for name, expected in build['generatedHashes'].items():
        require(digest(mod/name) == expected, 'Generated asset differs: '+name)
    observations = validate_plugin(plugin.read_bytes(), build, entry, mod)
    sources = check_base(args.base_config, build)
    negative = []
    for description, version, weather in (
            ('TES3_1.3_with_8_byte_WEAT', struct.pack('<f',1.3), bytes((60,30,10,0,0,0,0,0))),
            ('TES3_1.2_with_10_byte_WEAT', struct.pack('<f',1.2), bytes((60,30,10,0,0,0,0,0,0,0)))):
        try:
            weather_contract(version, weather)
        except ValueError:
            negative.append(description)
        else:
            raise ValueError('Invalid writer-contract regression accepted')
    # A known asymmetric ramp ensures the independent decoder does not merely
    # compare two copies of the same generated data.
    ramp = struct.pack('<f', 10.0)+struct.pack('<4225b', *([0]+[1]*64+([2]+[1]*64)*64))+b'\0'*3
    decoded,_ = decode_heights(ramp)
    require(decoded[0][64] == 592 and decoded[64][0] == 1104 and decoded[64][64] == 1616, 'Asymmetric height codec oracle')
    sentinel = struct.pack('<256H', *range(256))
    palette = decode_palette(sentinel)
    require(palette[0][4] == 16 and palette[4][0] == 64 and palette[15][15] == 255, 'VTEX permutation oracle')
    result = {'schema':'veyra.frontier-check.v1', 'version':'0.1.0',
              'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'checkerSha256':digest(Path(__file__)), 'pluginSha256':digest(plugin),
              'entryManifestSha256':digest(BASE/'ENTRY.json'), 'baseConfigSha256':build['baseConfigSha256'],
              'status':'SERIALIZED_CODEC_SEAMS_PALETTE_COLLISION_PASS_NATIVE_PENDING',
              'boundSourceFilesChecked':sources, 'coordinateCollisions':0, 'ownIdCollisions':0,
              'observations':observations, 'negativeWriterContractChecks':negative,
              'asymmetricHeightCodecOracle':'PASS', 'texturePermutationOracle':'PASS',
              'nativeEngineStarted':False, 'sourceProfilesMutated':0,
              'claimCeiling':'BOUND_SERIALIZED_TERRAIN_AND_ASSET_STRUCTURE_ONLY'}
    (BASE/'CHECK_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('FRONTIER_CHECK_PASS CELL16 LAND16 sharedVertices%d sources%d palette1..3 nativePENDING' %
          (observations['sharedVertexChecks'], sources))

if __name__ == '__main__':
    main()
