import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_material_overlay import build, texture_path


class MaterialPathTests(unittest.TestCase):
    def test_texture_target_stays_in_texture_directory(self):
        self.assertEqual(str(texture_path('textures/BC/shirt.dds')), 'textures/BC/shirt.dds')
        for name in ('../shirt.dds', 'textures/../shirt.dds', 'textures//shirt.dds',
                     'textures/./shirt.dds', 'C:/textures/shirt.dds', 'textures/shirt.png'):
            with self.assertRaises(ValueError):
                texture_path(name)


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Optional authoring dependency Pillow')
class MaterialConversionTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.original, self.source = self.root / 'original.dds', self.root / 'source.png'
        Image.new('RGBA', (32, 64), (41, 130, 83, 200)).save(self.original)
        Image.new('RGBA', (64, 128), (40, 120, 80, 210)).save(self.source)
        self.item = {'target': 'textures/cloth.dds', 'source': str(self.source), 'original': str(self.original),
                     'sourceSha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                     'originalSha256': hashlib.sha256(self.original.read_bytes()).hexdigest()}

    def plan(self, maps):
        path = self.root / 'plan.json'
        path.write_text(json.dumps({'schemaVersion': 1, 'maps': maps}), encoding='utf-8')
        return path

    def test_conversion_preserves_exact_pixels_and_sources(self):
        from PIL import Image
        original = self.original.read_bytes()
        receipt = build(self.plan([self.item]), self.root / 'result')
        with Image.open(self.root / 'result/textures/cloth.dds') as converted, Image.open(self.source) as source:
            self.assertEqual(converted.convert('RGBA').tobytes(), source.tobytes())
        self.assertEqual(self.original.read_bytes(), original)
        self.assertEqual(receipt['state'], 'BUILT_NOT_ACTIVATED')

    def test_changed_input_or_later_duplicate_leaves_no_output(self):
        bad_hash = dict(self.item, sourceSha256='0' * 64)
        duplicate = dict(self.item, target='textures/CLOTH.dds')
        for maps in ([bad_hash], [self.item, duplicate]):
            with self.assertRaises(ValueError):
                build(self.plan(maps), self.root / 'rejected')
            self.assertFalse((self.root / 'rejected').exists())

    def test_changed_aspect_ratio_is_rejected(self):
        from PIL import Image
        Image.new('RGB', (64, 64)).save(self.source)
        self.item['sourceSha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'aspect ratio'):
            build(self.plan([self.item]), self.root / 'rejected')
        self.assertFalse((self.root / 'rejected').exists())


if __name__ == '__main__':
    unittest.main()
