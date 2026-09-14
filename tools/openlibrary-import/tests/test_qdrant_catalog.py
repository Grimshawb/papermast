import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "qdrant_catalog.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("qdrant_catalog", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class QdrantCatalogTests(unittest.TestCase):
    def test_point_id_is_stable_and_work_specific(self):
        self.assertEqual(MODULE.point_id("/works/OL1W"), MODULE.point_id("/works/OL1W"))
        self.assertNotEqual(MODULE.point_id("/works/OL1W"), MODULE.point_id("/works/OL2W"))

    def test_decodes_payload_json_arrays(self):
        payload = MODULE.decoded_payload({
            "embedding_index": 7,
            "work_key": "/works/OL1W",
            "document_hash": "abc",
            "document_version": 1,
            "title": "Example",
            "author_names": ["A. Writer"],
            "genres": ["fantasy"],
            "retrieval_quality": "rich",
            "metadata_quality_score": 90,
            "representative_edition_key": "/books/OL1M",
            "representative_covers_json": "[123]",
            "representative_isbn_10_json": "[]",
            "representative_isbn_13_json": '["9780000000000"]',
        })
        self.assertEqual([123], payload["covers"])
        self.assertEqual(["9780000000000"], payload["isbn_13"])
        self.assertEqual(["A. Writer"], payload["authors"])

    def test_rejects_incomplete_embedding_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps({"status": "running"}))
            with self.assertRaisesRegex(RuntimeError, "not complete"):
                MODULE.read_manifest(path)


if __name__ == "__main__":
    unittest.main()
