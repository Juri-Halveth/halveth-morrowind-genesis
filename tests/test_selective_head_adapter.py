"""Synthetic TES3 records only; no original game or downloaded art fixtures."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_head_adapter import records, recbytes
from scripts.build_selective_head_adapter import build_adapter


def head(name, model, kind=0):
    return [(b'NAME', name.encode() + b'\0'), (b'MODL', model.encode() + b'\0'),
            (b'FNAM', b'fixture race\0'), (b'BYDT', bytes([kind, 0, 0, 0]))]


def plugin(bodies, masters=()):
    hedr = struct.pack('<fI32s256sI', 1.3, 0, b'fixture', b'no game assets', len(bodies))
    header = [(b'HEDR', hedr)]
    for name, size in masters:
        header.extend([(b'MAST', name.encode() + b'\0'), (b'DATA', struct.pack('<Q', size))])
    return recbytes(b'TES3', header) + b''.join(recbytes(b'BODY', parts) for parts in bodies)


class SelectiveHeadAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.master = self.root / 'Morrowind.esm'
        self.existing = self.root / 'HALVETH-Beautiful-Heads.esp'
        self.pack = self.root / 'westly'
        self.output = self.root / 'new-private-adapter'
        (self.pack / 'Meshes' / 'B').mkdir(parents=True)
        (self.pack / 'Meshes/B/HEAD_A.NIF').write_bytes(b'synthetic nif placeholder')
        (self.pack / 'Meshes/unused.nif').write_bytes(b'other synthetic placeholder')
        self.base_a = head('head_a', r'b\head_a.nif')
        self.base_b = head('head_b', r'b\head_b.nif')
        self.old_a = head('head_a', r'better\head_a.nif')
        self.old_b = head('head_b', r'khajiit\head_b.nif')
        self.master.write_bytes(plugin([self.base_a, self.base_b]))
        self.master_links = [(self.master.name, self.master.stat().st_size)]
        self.existing.write_bytes(plugin([self.old_a, self.old_b], self.master_links))
        self.original_master = self.master.read_bytes()
        self.original_adapter = self.existing.read_bytes()

    def build(self):
        return build_adapter([self.master], self.existing, [self.pack], self.output)

    def test_selective_existing_paths_preserve_every_other_body_byte(self):
        result = self.build()
        self.assertEqual((result['bodyRecords'], result['changedRecords'], result['preservedRecords']), (2, 1, 1))
        self.assertEqual((result['availableNifCount'], result['selectedNifCount'], result['unselectedNifCount']), (2, 1, 1))
        self.assertEqual(result['npcRecords'], 0)
        self.assertFalse(result['installed'])
        output = {rid: (unknown, flags, parts) for rid, unknown, flags, parts in records(self.output / self.existing.name)}
        self.assertEqual(output[b'head_a'], (0, 0, self.base_a))
        self.assertEqual(output[b'head_b'], (0, 0, self.old_b))
        self.assertEqual(self.master.read_bytes(), self.original_master)
        self.assertEqual(self.existing.read_bytes(), self.original_adapter)
        receipt = json.loads((self.output / 'adapter-receipt.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['selectedNifs'][0]['relativePath'], 'Meshes/B/HEAD_A.NIF')
        self.assertEqual(receipt['unselectedNifs'][0]['relativePath'], 'Meshes/unused.nif')

    def test_existing_output_and_originals_are_preserved(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'
        marker.write_bytes(b'previous output')
        with self.assertRaisesRegex(FileExistsError, 'new output directory'):
            self.build()
        self.assertEqual(marker.read_bytes(), b'previous output')
        self.assertEqual(self.existing.read_bytes(), self.original_adapter)

    def test_non_model_changes_in_existing_adapter_are_rejected(self):
        modified = [(key, b'another race\0' if key == b'FNAM' else value) for key, value in self.old_a]
        self.existing.write_bytes(plugin([modified, self.old_b], self.master_links))
        with self.assertRaisesRegex(ValueError, 'beyond BODY.MODL'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_npc_record_cannot_enter_output(self):
        self.existing.write_bytes(self.original_adapter + recbytes(b'NPC_', [(b'NAME', b'fixture\0')]))
        with self.assertRaisesRegex(ValueError, 'non-visual record'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_wrong_master_size_binding_is_rejected(self):
        self.existing.write_bytes(plugin([self.old_a, self.old_b], [(self.master.name, 1)]))
        with self.assertRaisesRegex(ValueError, 'master names, sizes or order'):
            self.build()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
