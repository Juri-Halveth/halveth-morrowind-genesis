import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.install_scarlet_banner import apply, restore, PACK_ID, TGA_PATH, DDS_PATH, PNG_PATH


class ScarletBannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.manifest = self.state / "graphics/install.json"
        self.manifest.parent.mkdir(parents=True)
        self.original = {"schemaVersion": 1, "dataDirectories": ["base-mod"], "shaders": ["clouds", "ssao"],
            "packages": [{"name": "Existing package", "status": "installed"}],
            "visualPlugins": [{"file": "Heads.esp", "sha256": "a" * 64}], "customSetting": "preserve"}
        self.original_bytes = json.dumps(self.original, ensure_ascii=False).encode()
        self.manifest.write_bytes(self.original_bytes)
        self.png = self.root / "input.png"
        self.tga = self.root / "input.tga"
        self.dds = self.root / "input.dds"
        # Header fixtures test format contracts, not rendering or image decoding.
        self.png.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
            + struct.pack(">II", 128, 256) + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)
        header = bytearray(18)
        header[2] = 2
        struct.pack_into("<HH", header, 12, 128, 256)
        header[16] = 24
        self.tga.write_bytes(header + bytes(128 * 256 * 3))
        dds_header = bytearray(128)
        dds_header[:4] = b"DDS "
        struct.pack_into("<I", dds_header, 4, 124)
        struct.pack_into("<II", dds_header, 12, 256, 128)
        struct.pack_into("<II", dds_header, 76, 32, 0x41)
        struct.pack_into("<I", dds_header, 88, 32)
        self.dds.write_bytes(dds_header + bytes(128 * 256 * 4))

    def install(self):
        return apply(self.png, self.tga, self.state, self.root, dds=self.dds)

    def test_apply_preserves_sources_and_existing_manifest_contract(self):
        png_before, tga_before = self.png.read_bytes(), self.tga.read_bytes()
        receipt = self.install()
        after = json.loads(self.manifest.read_text())
        for key in ("shaders", "visualPlugins", "customSetting"):
            self.assertEqual(after[key], self.original[key])
        self.assertEqual(after["dataDirectories"][0], "base-mod")
        self.assertEqual(Path(receipt["manifestBackup"]).read_bytes(), self.original_bytes)
        self.assertEqual(receipt["manifestBeforeSha256"], hashlib.sha256(self.original_bytes).hexdigest())
        pack = self.state / "graphics/ScarletLoveBanner"
        self.assertEqual((pack / TGA_PATH).read_bytes(), tga_before)
        self.assertEqual((pack / PNG_PATH).read_bytes(), png_before)
        self.assertEqual((pack / DDS_PATH).read_bytes(), self.dds.read_bytes())
        self.assertEqual(self.png.read_bytes(), png_before)
        self.assertEqual(self.tga.read_bytes(), tga_before)
        self.assertEqual(receipt["assetHeaderDimensions"], [128, 256])

    def test_restore_only_removes_owned_pack_and_preserves_later_changes(self):
        self.install()
        current = json.loads(self.manifest.read_text())
        current["dataDirectories"].append("later-mod")
        current["packages"].append({"name": "Later package"})
        current["shaders"].append("new-shader")
        self.manifest.write_text(json.dumps(current))
        result = restore(self.state, self.root)
        after = json.loads(self.manifest.read_text())
        self.assertFalse(result["active"])
        self.assertEqual(after["dataDirectories"], ["base-mod", "later-mod"])
        self.assertEqual(after["packages"], self.original["packages"] + [{"name": "Later package"}])
        self.assertEqual(after["shaders"], self.original["shaders"] + ["new-shader"])
        self.assertTrue((self.state / "graphics/ScarletLoveBanner" / TGA_PATH).is_file())
        raw = self.manifest.read_bytes()
        self.assertFalse(restore(self.state, self.root)["changed"])
        self.assertEqual(self.manifest.read_bytes(), raw)

    def test_reapplying_creates_no_duplicate_data_path_or_package(self):
        self.install()
        self.install()
        current = json.loads(self.manifest.read_text())
        self.assertEqual(len(current["dataDirectories"]), 2)
        self.assertEqual(sum(item.get("id") == PACK_ID for item in current["packages"]), 1)

    def test_rejects_mismatched_image_dimensions_without_manifest_change(self):
        raw = bytearray(self.png.read_bytes())
        struct.pack_into(">II", raw, 16, 256, 512)
        self.png.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "dimensions must match"):
            self.install()
        self.assertEqual(self.manifest.read_bytes(), self.original_bytes)
        self.assertFalse((self.state / "graphics/ScarletLoveBanner").exists())

    def test_rejects_truncated_tga_without_changing_manifest(self):
        self.tga.write_bytes(self.tga.read_bytes()[:18])
        with self.assertRaisesRegex(ValueError, "Truncated"):
            self.install()
        self.assertEqual(self.manifest.read_bytes(), self.original_bytes)

    def test_unowned_manifest_entry_is_not_removed_or_replaced(self):
        current = dict(self.original)
        current["dataDirectories"] = [str(self.state / "graphics/ScarletLoveBanner")]
        raw = json.dumps(current).encode()
        self.manifest.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "unowned"):
            self.install()
        with self.assertRaisesRegex(ValueError, "No owned"):
            restore(self.state, self.root)
        self.assertEqual(self.manifest.read_bytes(), raw)

    def test_rejects_missing_dds_alternative_without_manifest_change(self):
        self.dds.unlink()
        with self.assertRaisesRegex(ValueError, "DDS input"):
            self.install()
        self.assertEqual(self.manifest.read_bytes(), self.original_bytes)

    def test_rejects_truncated_dds_without_manifest_change(self):
        self.dds.write_bytes(self.dds.read_bytes()[:128])
        with self.assertRaisesRegex(ValueError, "Truncated uncompressed DDS"):
            self.install()
        self.assertEqual(self.manifest.read_bytes(), self.original_bytes)


if __name__ == "__main__":
    unittest.main()
