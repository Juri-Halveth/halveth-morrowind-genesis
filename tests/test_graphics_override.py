"""Synthetic checks for optional local graphics overlays and visual plugins.

These fixtures contain no Morrowind assets. They bind configuration order and
the limited TES3 record types accepted by the public graphics helper.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import graphics_profile, prepare_profile


def record(kind: bytes, payload: bytes) -> bytes:
    return struct.pack("<4sIII", kind, len(payload), 0, 0) + payload


def subrecord(kind: bytes, payload: bytes) -> bytes:
    return struct.pack("<4sI", kind, len(payload)) + payload


def visual_plugin(kind: bytes = b"STAT") -> bytes:
    header = bytearray(300)
    struct.pack_into("<I", header, 296, 1)
    visual = subrecord(b"NAME", b"test_static\0") + subrecord(b"MODL", b"Meshes\\test.nif\0")
    return record(b"TES3", subrecord(b"HEDR", bytes(header))) + record(kind, visual)


class GraphicsOverlayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "app"
        self.state = self.root / "state"
        self.ordinary = self.root / "ordinary"
        self.override = self.root / "override"
        self.ordinary.mkdir()
        self.override.mkdir()
        self.manifest = self.state / "graphics" / "install.json"
        self.manifest.parent.mkdir(parents=True)

    def write_manifest(self, **updates):
        data = {"schemaVersion": 1, "dataDirectories": [str(self.ordinary), str(self.override)],
                "shaders": []}
        data.update(updates)
        self.manifest.write_text(json.dumps(data), encoding="utf-8")

    def test_registered_override_is_resolved_and_legacy_manifest_keeps_original_order(self):
        self.write_manifest(overrideDataDirectories=[str(self.override)])
        resolved = graphics_profile.load_graphics_manifest(self.project, self.state)
        self.assertEqual(resolved["directories"], [self.ordinary.resolve(), self.override.resolve()])
        self.assertEqual(resolved["override_directories"], [self.override.resolve()])
        self.write_manifest()
        self.assertEqual(graphics_profile.load_graphics_manifest(self.project, self.state)["override_directories"], [])

    def test_override_requires_registered_unique_directory(self):
        self.write_manifest(overrideDataDirectories=[str(self.root / "unregistered")])
        with self.assertRaisesRegex(ValueError, "must occur once"):
            graphics_profile.load_graphics_manifest(self.project, self.state)
        self.write_manifest(overrideDataDirectories=[str(self.override), str(self.override)])
        with self.assertRaisesRegex(ValueError, "must occur once"):
            graphics_profile.load_graphics_manifest(self.project, self.state)

    def test_stat_plugin_accepts_only_name_and_relative_model(self):
        plugin = self.override / "Visuals.esp"
        plugin.write_bytes(visual_plugin())
        digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
        receipt = graphics_profile.validate_visual_plugin(plugin, digest)
        self.assertEqual(receipt["recordCounts"], {"TES3": 1, "BODY": 0, "STAT": 1})
        plugin.write_bytes(visual_plugin(b"NPC_"))
        with self.assertRaisesRegex(ValueError, "non-visual record"):
            graphics_profile.validate_visual_plugin(plugin, hashlib.sha256(plugin.read_bytes()).hexdigest())
        unsafe = record(b"TES3", subrecord(b"HEDR", bytes(bytearray(296) + struct.pack("<I", 1))))
        unsafe += record(b"STAT", subrecord(b"NAME", b"test_static\0") +
                         subrecord(b"MODL", b"..\\outside.nif\0"))
        plugin.write_bytes(unsafe)
        with self.assertRaisesRegex(ValueError, "relative VFS path"):
            graphics_profile.validate_visual_plugin(plugin, hashlib.sha256(unsafe).hexdigest())

    def test_profile_places_override_after_app_mod_and_resolves_its_shader(self):
        install = self.root / "install"
        source = install / "profiles" / "max"
        engine = install / "engine"
        (engine / "resources" / "vfs").mkdir(parents=True)
        source.mkdir(parents=True)
        base_data = self.root / "base-data"
        base_data.mkdir()
        (engine / ("openmw.exe" if os.name == "nt" else "openmw")).write_bytes(b"test engine")
        (source / "openmw.cfg").write_text(f'data="{base_data}"\ncontent=Morrowind.esm\n', encoding="utf-8")
        (source / "settings.cfg").write_text("[Video]\nresolution x=1280\n", encoding="utf-8")
        mod = self.project / "mod"
        mod.mkdir(parents=True)
        (mod / "halveth.omwscripts").write_text("", encoding="utf-8")
        for directory in (self.ordinary, mod, self.override):
            shader_dir = directory / "Shaders"
            shader_dir.mkdir()
            (shader_dir / "fixture.omwfx").write_text(str(directory), encoding="utf-8")
        plugin = self.override / "Visuals.esp"
        plugin.write_bytes(visual_plugin())
        self.write_manifest(overrideDataDirectories=[str(self.override)], shaders=["fixture"],
                            visualPlugins=[{"file": plugin.name,
                                            "sha256": hashlib.sha256(plugin.read_bytes()).hexdigest()}])
        args = argparse.Namespace(install_root=install, state_dir=self.state, source_profile="max",
                                  profile="beauty", smoke=False, copy_saves=False,
                                  reset_settings=False, graphics_manifest=None)
        with patch.object(prepare_profile, "PROJECT", self.project):
            receipt = prepare_profile.prepare(args)
        lines = (self.state / "profiles" / "beauty" / "openmw.cfg").read_text(encoding="utf-8").splitlines()
        ordinary = "data=" + prepare_profile.quoted(self.ordinary)
        app_mod = "data=" + prepare_profile.quoted(mod)
        override = "data=" + prepare_profile.quoted(self.override)
        self.assertLess(lines.index(ordinary), lines.index(app_mod))
        self.assertLess(lines.index(app_mod), lines.index(override))
        self.assertLess(lines.index("content=Visuals.esp"), lines.index("content=halveth.omwscripts"))
        # Windows runners may spell the same temp directory as RUNNER~1 or
        # runneradmin; compare the selected file, not its path spelling.
        self.assertTrue(Path(receipt["graphics"]["shader_files"]["fixture"]).samefile(
            self.override / "Shaders" / "fixture.omwfx"))
        self.assertEqual(receipt["graphics"]["visual_plugins"][0]["recordCounts"]["STAT"], 1)


if __name__ == "__main__":
    unittest.main()
