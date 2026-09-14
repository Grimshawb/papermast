import importlib.util
import os
import sys
import threading
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "librarian_service.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("librarian_service", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeEmbedder:
    def embed(self, texts):
        assert texts == [MODULE.QUERY_PREFIX + "quiet fantasy"]
        vector = np.zeros(384, dtype=np.float32)
        vector[0] = 2.0
        yield vector


class FakeQdrant:
    def __init__(self, catalog_authors=()):
        self.query_filter = None
        self.catalog_authors = tuple(catalog_authors)

    def scroll(self, **kwargs):
        requested = {
            condition.match.value
            for condition in kwargs["scroll_filter"].should
        }
        matched = [author for author in self.catalog_authors if author in requested]
        records = [
            type("Point", (), {"payload": {"authors_normalized": [author]}})()
            for author in matched
        ]
        return records, None

    def query_points(self, **kwargs):
        self.query_filter = kwargs["query_filter"]
        return type("Result", (), {"points": []})()


class LibrarianServiceTests(unittest.TestCase):
    def test_query_vector_is_normalized_and_prefixed(self):
        engine = object.__new__(MODULE.LibrarianEngine)
        engine.embedder = FakeEmbedder()
        vector = engine.query_vector("quiet fantasy")
        self.assertEqual((384,), vector.shape)
        self.assertAlmostEqual(1.0, float(np.linalg.norm(vector)))
        self.assertEqual(1.0, float(vector[0]))

    def test_request_contract_bounds_query_and_result_count(self):
        request = MODULE.RecommendRequest(query="funny fiction", result_count=3)
        self.assertEqual(3, request.result_count)
        with self.assertRaises(Exception):
            MODULE.RecommendRequest(query="x", result_count=5)
        with self.assertRaises(Exception):
            MODULE.RecommendRequest(query="funny fiction", result_count=6)

    def test_settings_accept_gemini_key_from_environment(self):
        previous = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-only-key"
        try:
            settings = MODULE.Settings()
            self.assertEqual("test-only-key", settings.gemini_api_key)
            self.assertFalse(settings.model_local_only)
        finally:
            if previous is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = previous

    def test_author_request_filters_only_after_catalog_validation(self):
        engine = object.__new__(MODULE.LibrarianEngine)
        engine.settings = type("Settings", (), {"collection": "catalog"})()
        engine.qdrant = FakeQdrant(("morgan vale",))
        engine.query_vector = lambda _: np.zeros(384, dtype=np.float32)
        engine.author_reference_vector = lambda _: None

        with self.assertRaisesRegex(RuntimeError, "only 0 eligible candidates"):
            engine.candidates("Which book by Morgan Vale should I read?")

        self.assertIsNotNone(engine.qdrant.query_filter)
        condition = engine.qdrant.query_filter.should[0]
        self.assertEqual("authors_normalized", condition.key)
        self.assertEqual("morgan vale", condition.match.value)

    def test_non_author_possessive_does_not_create_a_hard_filter(self):
        engine = object.__new__(MODULE.LibrarianEngine)
        engine.settings = type("Settings", (), {"collection": "catalog"})()
        engine.qdrant = FakeQdrant()
        engine.query_vector = lambda _: np.zeros(384, dtype=np.float32)
        engine.author_reference_vector = lambda _: None

        with self.assertRaisesRegex(RuntimeError, "only 0 eligible candidates"):
            engine.candidates("A reader's guide to quiet fantasy")

        self.assertIsNone(engine.qdrant.query_filter)

    def test_gemini_failure_returns_local_recommendations(self):
        engine = object.__new__(MODULE.LibrarianEngine)
        engine.settings = type("Settings", (), {"gemini_model": "test-model"})()
        engine.gemini = object()
        engine.slots = threading.BoundedSemaphore(1)
        candidates = [
            {
                "work_key": f"/works/OL{index}W",
                "title": f"Book {index}",
                "authors": [f"Author {index}"],
                "genres": ["fantasy"],
                "description": "A quiet story about friendship.",
                "representative_edition_key": None,
                "cover_ids": [],
                "isbn_10": [],
                "isbn_13": [],
                "publication_date": None,
                "page_count": None,
            }
            for index in range(5)
        ]
        engine.candidates = lambda _: candidates
        original_rerank = MODULE.rerank
        MODULE.rerank = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("provider returned no text")
        )
        try:
            response = engine.recommend(
                MODULE.RecommendRequest(query="quiet fantasy", result_count=5)
            )
        finally:
            MODULE.rerank = original_rerank

        self.assertEqual(5, len(response.recommendations))
        self.assertEqual("/works/OL0W", response.recommendations[0].work_key)
        self.assertIn("fantasy", response.recommendations[0].reason)


if __name__ == "__main__":
    unittest.main()
