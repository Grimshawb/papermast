import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb


MODULE_PATH = Path(__file__).parents[1] / "finalize_catalog.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("finalize_catalog", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FinalizeCatalogTests(unittest.TestCase):
    def test_embedding_manifest_requires_completed_shards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({
                "status": "complete",
                "model_id": MODULE.MODEL_ID,
                "model_revision": MODULE.MODEL_REVISION,
                "dimensions": 384,
                "normalized": True,
                "target_count": 2,
                "shards": [{"count": 1}],
            }))
            with self.assertRaisesRegex(RuntimeError, "counts do not match"):
                MODULE.load_embedding_identity(path)

    def test_exports_valid_compact_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "catalog.duckdb"
            connection = duckdb.connect(str(database))
            connection.execute("""
                CREATE TABLE retrieval_documents AS SELECT
                    '/works/OL1W'::VARCHAR AS work_key,
                    'A Book'::VARCHAR AS title,
                    ['A Writer']::VARCHAR[] AS author_names,
                    ['mystery']::VARCHAR[] AS genres,
                    ['small towns']::VARCHAR[] AS cleaned_subjects,
                    'A description.'::VARCHAR AS cleaned_description,
                    '/books/OL1M'::VARCHAR AS representative_edition_key,
                    '[123]'::VARCHAR AS representative_covers_json,
                    '["0123456789"]'::VARCHAR AS representative_isbn_10_json,
                    '["9780123456786"]'::VARCHAR AS representative_isbn_13_json,
                    'rich'::VARCHAR AS retrieval_quality,
                    8::INTEGER AS metadata_quality_score,
                    1::INTEGER AS document_version,
                    'abc'::VARCHAR AS document_hash
            """)
            connection.execute("""
                CREATE TABLE fiction_catalog AS SELECT
                    '/works/OL1W'::VARCHAR AS work_key,
                    '2001'::VARCHAR AS representative_publish_date,
                    NULL::VARCHAR AS first_publish_date,
                    320::INTEGER AS representative_number_of_pages,
                    3::BIGINT AS edition_count,
                    2::BIGINT AS english_edition_count
            """)
            connection.close()
            output = root / "fiction-catalog.parquet"
            result = MODULE.export_catalog(database, output)
            self.assertEqual(1, result["source"]["count"])
            row = duckdb.connect().execute(
                "SELECT work_key, cover_ids, isbn_13 FROM read_parquet(?)", [str(output)]
            ).fetchone()
            self.assertEqual(("/works/OL1W", [123], ["9780123456786"]), row)


if __name__ == "__main__":
    unittest.main()
