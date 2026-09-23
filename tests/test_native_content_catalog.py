import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_native_content import SOURCE, TARGET, render, validate


class NativeContentCatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_generated_lua_matches_current_authoritative_content(self):
        self.assertEqual(TARGET.read_text(encoding="utf-8"), render(self.data))

    def test_all_fifteen_original_passages_remain_available(self):
        self.assertEqual([len(book["pages"]) for book in self.data["books"]], [3, 3, 3, 2, 2, 2])
        texts = [page["text"] for book in self.data["books"] for page in book["pages"]]
        self.assertEqual(len(set(texts)), 15)
        self.assertTrue(all(len(text) > 150 for text in texts))

    def test_duplicate_logical_identity_is_rejected(self):
        candidate = copy.deepcopy(self.data)
        candidate["books"][1]["key"] = candidate["books"][0]["key"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate(candidate)

    def test_invalid_recall_answer_is_rejected(self):
        candidate = copy.deepcopy(self.data)
        candidate["books"][0]["pages"][0]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "recall"):
            validate(candidate)

    def test_invented_engine_effect_is_rejected(self):
        candidate = copy.deepcopy(self.data)
        candidate["spells"][0]["effects"][0]["id"] = "imaginary-effect"
        with self.assertRaisesRegex(ValueError, "effect"):
            validate(candidate)


if __name__ == "__main__":
    unittest.main()
