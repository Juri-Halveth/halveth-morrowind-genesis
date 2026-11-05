"""MIT. Bind own entry/plaza inputs and primary API bytes; never launch a game."""
import argparse
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, limit=4 * 1024 * 1024):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('Input is not a bounded regular file')
    return path.read_bytes()


def lua(value):
    if isinstance(value, dict):
        return '{' + ','.join('[' + json.dumps(key) + ']=' + lua(item) for key, item in sorted(value.items())) + '}'
    if isinstance(value, list):
        return '{' + ','.join(lua(item) for item in value) + '}'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, (int, float)) and math.isfinite(value):
        return repr(value)
    raise ValueError('Unsupported configuration type')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entry', type=Path, required=True)
    p.add_argument('--frontier-plugin', type=Path, required=True)
    p.add_argument('--placements', type=Path, required=True)
    p.add_argument('--plaza-plugin', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    a = p.parse_args()
    raw_entry, raw_plaza = read(a.entry), read(a.placements)
    entry, plaza = json.loads(raw_entry), json.loads(raw_plaza)
    if entry['schema'] != 'veyra.frontier-entry.v1' or plaza['schema'] != 'veyra.plaza-placement.v1':
        raise ValueError('Unexpected own input schema')
    if sha(read(a.frontier_plugin)) != entry['pluginSha256'] or sha(raw_entry) != plaza['frontierEntrySha256']:
        raise ValueError('Entry/plugin/placement source binding differs')
    if sha(read(a.plaza_plugin)) != plaza['pluginSha256'] or plaza['frontierPluginSha256'] != entry['pluginSha256']:
        raise ValueError('Plaza/plugin/terrain source binding differs')
    if entry['automaticTeleport'] or plaza['automaticTeleport'] or entry['networkEffects'] or plaza['networkEffects']:
        raise ValueError('Unexpected action scope in own input')
    api = {}
    for name in ('core', 'world', 'types', 'nearby', 'self', 'ui', 'util'):
        relative = 'resources/lua_api/openmw/' + name + '.lua'
        api[relative] = sha(read(a.runtime / relative))
    ai_relative = 'resources/vfs/scripts/omw/ai.lua'
    ai = read(a.runtime / ai_relative)
    if b"elseif args.type == 'Travel' then" not in ai or b'_startAiTravel(args.destPosition' not in ai:
        raise ValueError('Bound runtime lacks expected Travel destination contract')
    api[ai_relative] = sha(ai)
    ui_relative = 'resources/vfs/scripts/omw/ui.lua'
    ui = read(a.runtime / ui_relative)
    if b"getMode = function()" not in ui or b"I.UI.setMode('Interface')" not in ui:
        raise ValueError('Bound runtime lacks expected native UI mode contract')
    api[ui_relative] = sha(ui)
    x, y = entry['position']['x'], entry['position']['y']
    z = plaza['worldFloorZ']
    offsets = {'home_garden': [100, 100], 'home_trade': [340, 100], 'home_watch': [100, 360],
               'water': [250, 650], 'field': [1500, 1500], 'market': [900, 500],
               'approach': [1400, 1400], 'lookout': [500, 1700], 'arrival_gate': [550, 250]}
    locations = {key: {'x': x + dx, 'y': y + dy, 'z': z} for key, (dx, dy) in offsets.items()}
    centre = entry['centralPad']['centre']
    for point in locations.values():
        if math.hypot(point['x'] - centre['x'], point['y'] - centre['y']) > entry['centralPad']['flatRadius'] - 160:
            raise ValueError('A source destination is outside the bounded flat-pad interior')
    def schedule(home, early, day, afternoon):
        return [{'at': hour, 'place': place} for hour, place in
                ((0, home), (6, early), (8, day), (12, afternoon), (18, home))]
    roles = [
        {'id': 'garden', 'name': 'Kera - Garden Visitor', 'template': 'eldafire', 'home': 'home_garden',
         'schedule': schedule('home_garden', 'water', 'field', 'market')},
        {'id': 'trade', 'name': 'Lio - Trade Visitor', 'template': 'fargoth', 'home': 'home_trade',
         'schedule': schedule('home_trade', 'water', 'market', 'approach')},
        {'id': 'watch', 'name': 'Senn - Watch Visitor', 'template': 'arrille', 'home': 'home_watch',
         'schedule': schedule('home_watch', 'approach', 'lookout', 'arrival_gate')},
    ]
    config = {'version': '0.1.0', 'saveSchema': 1, 'luaApi': 129,
              'entry': {'name': entry['cellName'], 'x': x, 'y': y, 'radius': 2200},
              'locations': locations, 'roles': roles,
              'arrivalTolerance': 90, 'minimumObservedMovement': 64,
              'maximumSampleJump': 800, 'sampleSeconds': 0.5, 'stallSeconds': 12,
              'maximumReplans': 2, 'activationRetrySeconds': 1,
              'boundEntrySha256': sha(raw_entry), 'boundPlazaSha256': sha(raw_plaza),
              'frontierPluginSha256': entry['pluginSha256'], 'plazaPluginSha256': plaza['pluginSha256']}
    output = BASE / 'mod/scripts/veyra_townlife/config.lua'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('-- SPDX-License-Identifier: MIT\n-- Own input-bound constants; native Townlife NOT_RUN.\nreturn ' + lua(config) + '\n', encoding='utf8', newline='\n')
    receipt = {'schema': 'veyra.townlife.source-binding.v1', 'dataClass': 'PUBLIC',
               'sourceStatus': 'OWN_SOURCE_INPUTS_BOUND_NATIVE_NOT_RUN', 'engine': 'OpenMW 0.51.0', 'luaApi': 129,
               'ownInputHashes': {'ENTRY.json': sha(raw_entry), 'PLACEMENTS.json': sha(raw_plaza),
                                  entry['plugin']: entry['pluginSha256'], plaza['plugin']: plaza['pluginSha256']},
               'primaryApiSourceHashes': api, 'generatedConfigSha256': sha(output.read_bytes()),
               'config': config, 'engineExecution': 'NOT_REQUESTED', 'networkEffects': 0,
               'sourceWrites': 'ONLY_OWN_CONFIG_AND_BINDING_RECEIPT'}
    (BASE / 'SOURCE_BINDING.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8', newline='\n')
    print('TOWNLIFE_SOURCE_BINDING_PASS roles=3 locations=9 native=NOT_RUN')


if __name__ == '__main__':
    main()
