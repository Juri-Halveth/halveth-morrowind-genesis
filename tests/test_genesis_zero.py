from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "genesis-zero"


class GenesisZeroBoundaryTests(unittest.TestCase):
    def test_runtime_references_are_local_and_complete(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        scene = (ROOT / "scene.js").read_text(encoding="utf-8")
        self.assertIn('href="./style.css"', html)
        self.assertIn('src="./scene.js"', html)
        self.assertNotRegex(html, r"(?:src|href)=['\"]https?://")
        self.assertNotIn("@import", css)
        self.assertNotRegex(css, r"url\(['\"]?https?://")
        for network_api in ("fetch(", "XMLHttpRequest", "WebSocket(", "EventSource(", "navigator.sendBeacon"):
            self.assertNotIn(network_api, scene)
        self.assertNotIn("import(", scene)

    def test_scene_has_authored_phase_field_and_user_controls(self):
        scene = (ROOT / "scene.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("field4(p-center", scene)
        self.assertIn("u_phase", scene)
        self.assertIn("KeyQ", scene)
        self.assertIn("KeyE", scene)
        self.assertIn("KeyW", scene)
        self.assertIn("PULS GEBEN", html)

    def test_new_runtime_contains_no_imported_game_or_asset_paths(self):
        for path in ROOT.iterdir():
            if path.suffix in {".html", ".css", ".js"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("Morrowind.esm", text)
                self.assertNotIn("Data Files", text)
                self.assertNotIn("openmw.cfg", text)


if __name__ == "__main__":
    unittest.main()
