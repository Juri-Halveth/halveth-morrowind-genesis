"""MIT. Tests use only authored synthetic records, never redistributed masters."""
from pathlib import Path
import contextlib, gzip, io, json, struct, tempfile, unittest, subprocess, hashlib, os
import registry as r


def sub(tag, value):
    return struct.pack('<4sI', tag, len(value)) + value


def record(tag, *fields):
    body = b''.join(sub(k, v) for k, v in fields)
    return struct.pack('<4sIII', tag, len(body), 0, 0) + body


def cell(name, number, rid, x):
    return record(b'CELL', (b'NAME', name.encode() + b'\0'),
        (b'DATA', struct.pack('<Iii', 1, 0, 0)),
        (b'FRMR', struct.pack('<I', number)), (b'NAME', rid.encode() + b'\0'),
        (b'DATA', struct.pack('<6f', x, 0, 0, 0, 0, 0)))


class RegistryContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'; self.data.mkdir()
        self.cfgdir = self.root / 'cfg'; self.cfgdir.mkdir()
        self.config = self.cfgdir / 'openmw.cfg'
        self.config.write_text('replace=config\nreplace=data\nreplace=content\n'
            f'data="{self.data.as_posix()}"\ncontent=Base.esm\n', encoding='utf8')
        self.base = self.data / 'Base.esm'
        self.base.write_bytes(record(b'TES3') + record(b'MISC', (b'NAME', b'cup\0'))
            + record(b'NPC_', (b'NAME', b'actor\0'), (b'BNAM', b'head1\0'))
            + cell('room', 1, 'cup', 0) + cell('room', 2, 'cup', 10)
            + cell('room', 3, 'actor', 20))

    def tearDown(self):
        self.temp.cleanup()

    def build(self, suffix):
        out = self.root / suffix
        with contextlib.redirect_stdout(io.StringIO()):
            receipt = r.catalogue(self.config, out)
        with gzip.open(out / 'registry.jsonl.gz', 'rt', encoding='ascii') as stream:
            entries = [json.loads(row) for row in stream]
        return entries, receipt

    def test_two_copies_have_two_ids_and_one_template(self):
        entries, receipt = self.build('a')
        cups = [v for v in entries if v.get('recordId') == 'cup']
        self.assertEqual(len(cups), 2)
        self.assertNotEqual(cups[0]['id'], cups[1]['id'])
        self.assertEqual(cups[0]['templateIds'], cups[1]['templateIds'])
        self.assertTrue(receipt['sourceBytesUnchanged'])

    def test_position_and_cell_change_preserve_reference_identity(self):
        a, _ = self.build('a')
        self.base.write_bytes(record(b'TES3') + record(b'MISC', (b'NAME', b'cup\0'))
                             + cell('another-room', 1, 'cup', 123))
        b, _ = self.build('b')
        old = next(v for v in a if v['kind'] == 'INSTANCE' and v['anchor'] == 'base.esm:1')
        new = next(v for v in b if v['kind'] == 'INSTANCE')
        self.assertEqual(old['id'], new['id'])
        self.assertNotEqual(old['stateSha256'], new['stateSha256'])

    def test_appearance_edit_preserves_record_identity(self):
        a, _ = self.build('a')
        self.base.write_bytes(record(b'TES3') + record(b'NPC_', (b'NAME', b'actor\0'), (b'BNAM', b'head2\0')))
        b, _ = self.build('b')
        old = next(v for v in a if v['kind'] == 'RECORD/NPC_')
        new = next(v for v in b if v['kind'] == 'RECORD/NPC_')
        self.assertEqual(old['id'], new['id'])
        self.assertNotEqual(old['stateSha256'], new['stateSha256'])

    def test_master_override_keeps_reference_owner(self):
        a, _ = self.build('a')
        (self.data / 'Overlay.esp').write_bytes(record(b'TES3', (b'MAST', b'Base.esm\0'))
            + cell('room', 0x01000001, 'cup', 77))
        self.config.write_text(self.config.read_text(encoding='utf8') + 'content=Overlay.esp\n', encoding='utf8')
        b, _ = self.build('b')
        old = next(v for v in a if v['kind'] == 'INSTANCE' and v['anchor'] == 'base.esm:1')
        new = next(v for v in b if v['kind'] == 'INSTANCE' and v['anchor'] == 'base.esm:1')
        self.assertEqual(old['id'], new['id'])
        self.assertEqual(new['sourceFile'], 'Overlay.esp')
        self.assertNotEqual(old['stateSha256'], new['stateSha256'])

    def test_invalid_source_never_creates_catalogue(self):
        self.base.write_bytes(b'not-a-complete-record')
        with self.assertRaises(ValueError):
            self.build('bad')
        self.assertFalse((self.root / 'bad').exists())

    def test_unknown_reference_owner_remains_explicit(self):
        self.base.write_bytes(record(b'TES3') + cell('room', 0x02000001, 'cup', 0))
        entries, receipt = self.build('a')
        self.assertEqual(receipt['snapshotAddressCount'], 1)
        self.assertEqual(receipt['observationGaps'][0]['kind'], 'UNRESOLVED_REFERENCE_OWNER')

    def test_bash_story_history_is_chained_and_visual_policy_has_no_story_effect(self):
        script = Path(__file__).parent / 'ENTITY_LIFE.sh'
        bash = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else 'bash'
        env = {**os.environ, 'ENTITY_REGISTRY_DIR': str(self.root / 'no-source-binding'), 'TMPDIR': str(self.root)}
        for policy, event_count, ending in [('connected', 12, 'story-endpoint=reassess'),
                                            ('visual-only', 3, 'story-endpoint=unaware')]:
            result = subprocess.run([bash, str(script), 'demo', policy, 'bright'],
                                    capture_output=True, text=True, env=env, check=True)
            self.assertIn(ending, result.stdout)
            history = next(line[9:] for line in result.stdout.splitlines() if line.startswith('HISTORY: '))
            if os.name == 'nt' and history.startswith('/'):
                history = subprocess.run([bash, '-c', 'cygpath -m -- "$1"', '_', history],
                    capture_output=True, text=True, check=True).stdout.strip()
            rows = Path(history).read_text(encoding='utf8').splitlines()[1:]
            self.assertEqual(len(rows), event_count)
            previous = 'GENESIS'
            for row in rows:
                values = row.split('\t')
                self.assertEqual(values[-2], previous)
                self.assertEqual(values[-1], hashlib.sha256('\t'.join(values[:-1]).encode('utf8')).hexdigest())
                previous = values[-1]


if __name__ == '__main__':
    unittest.main()
