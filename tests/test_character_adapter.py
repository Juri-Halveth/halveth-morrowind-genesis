"""Synthetic adapters: preserve quest/item semantics while changing appearance."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_character_adapter import build_adapter, read_records, PART_FIELDS
from scripts.build_head_adapter import recbytes


def body(name, model, clothing=False):
    return [(b'NAME', name.encode() + b'\0'), (b'MODL', model.encode() + b'\0'),
            (b'FNAM', b'fixture race\0'), (b'BYDT', bytes([3, 0, 0, int(clothing)]))]


def clothing(name, reference, value=17):
    return [(b'NAME', name.encode() + b'\0'), (b'MODL', b'c/world.nif\0'),
            (b'FNAM', b'Original localized name\0'), (b'CTDT', struct.pack('<IfHH', 2, 3.0, value, 20)),
            (b'ITEX', b'c/icon.dds\0'), (b'SCRI', b'quest_script\0'), (b'ENAM', b'enchantment\0'),
            (b'INDX', b'\x02'), (b'BNAM', reference.encode())]


def plugin(items):
    return recbytes(b'TES3', [(b'HEDR', struct.pack('<fI32s256sI', 1.3, 0, b'fixture', b'synthetic', len(items)))]) + b''.join(recbytes(k, v) for k, v in items)


class CharacterAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.master = self.root / 'Morrowind.esm'
        self.bodies, self.clothes = self.root / 'Bodies.esp', self.root / 'Clothes.esp'
        self.data = self.root / 'data'
        self.output = self.root / 'output'
        (self.data / 'Meshes').mkdir(parents=True)
        for name in ('smooth.nif', 'shirt.nif'):
            (self.data / 'Meshes' / name).write_bytes(b'fixture; native NIF parsing is a separate check')
        self.original = clothing('quest_shirt', 'skin')
        self.master.write_bytes(plugin([(b'BODY', body('skin', 'old.nif')), (b'CLOT', self.original)]))
        self.body_parts = body('skin', 'smooth.nif')
        self.bodies.write_bytes(plugin([(b'BODY', self.body_parts)]))
        self.donor_shirt = clothing('quest_shirt', 'new_shirt', value=999)
        self.clothing_body = body('new_shirt', 'shirt.nif', True)
        self.clothes.write_bytes(plugin([(b'CLOT', self.donor_shirt), (b'BODY', self.clothing_body)]))

    def build(self):
        return build_adapter([self.master], self.bodies, self.clothes, [self.data], self.output)

    def test_item_properties_and_source_bytes_survive_visual_change(self):
        before = {p: p.read_bytes() for p in (self.master, self.bodies, self.clothes)}
        result = self.build()
        records = read_records(self.output / result['file'])
        actual = records[(b'CLOT', b'quest_shirt')][2]
        self.assertEqual([(k, v) for k, v in actual if k not in PART_FIELDS],
                         [(k, v) for k, v in self.original if k not in PART_FIELDS])
        self.assertIn((b'BNAM', b'new_shirt'), actual)
        self.assertEqual(result['recordCounts'], {'TES3': 1, 'BODY': 2, 'CLOT': 1})
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertFalse(result['installed'])

    def test_missing_dependency_is_rejected_before_output(self):
        self.clothes.write_bytes(plugin([(b'CLOT', clothing('quest_shirt', 'missing'))]))
        with self.assertRaisesRegex(ValueError, 'unavailable BODY'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_donor_gameplay_records_are_not_imported(self):
        self.clothes.write_bytes(self.clothes.read_bytes() + recbytes(b'SCPT', []))
        with self.assertRaisesRegex(ValueError, 'Unexpected donor record'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_body_race_change_is_rejected(self):
        modified = [(k, b'another race\0' if k == b'FNAM' else v) for k, v in self.body_parts]
        self.bodies.write_bytes(plugin([(b'BODY', modified)]))
        with self.assertRaisesRegex(ValueError, 'non-model fields'):
            self.build()

    def test_new_items_and_unused_body_definitions_are_explicitly_excluded(self):
        self.clothes.write_bytes(plugin([(b'CLOT', self.donor_shirt), (b'BODY', self.clothing_body),
            (b'CLOT', clothing('new_item', 'unused')), (b'BODY', body('unused', 'absent.nif', True))]))
        result = self.build()
        self.assertEqual({r['id'] for r in result['excludedRecords']}, {'new_item', 'unused'})
        self.assertEqual(result['recordCounts']['CLOT'], 1)

    def test_duplicate_slot_rejected(self):
        broken = self.donor_shirt + [(b'INDX', b'\x02'), (b'BNAM', b'new_shirt')]
        self.clothes.write_bytes(plugin([(b'CLOT', broken), (b'BODY', self.clothing_body)]))
        with self.assertRaisesRegex(ValueError, 'repeated clothing body-part slot'):
            self.build()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
