import importlib.util
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).parents[1] / "gemini_librarian.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("gemini_librarian", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GeminiLibrarianTests(unittest.TestCase):
    @staticmethod
    def candidate(index, *, author=None, genres=None, quality="rich", score=None, title=None):
        return {
            "work_key": f"/works/OL{index}W",
            "title": title or f"Book {index}",
            "authors": [author or f"Author {index}"],
            "genres": genres or [],
            "description": "A detailed novel description.",
            "retrieval_quality": quality,
            "metadata_quality_score": 5,
            "representative_edition_key": f"/books/OL{index}M",
            "retrieval_rank": index + 1,
            "similarity_score": score if score is not None else 1 - index / 1000,
        }

    def test_load_api_key_requires_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gemini.env"
            path.write_text("GEMINI_API_KEY=secret\n")
            os.chmod(path, 0o644)
            with self.assertRaisesRegex(RuntimeError, "permissions must be 600"):
                MODULE.load_api_key(path)
            os.chmod(path, 0o600)
            self.assertEqual("secret", MODULE.load_api_key(path))

    def test_normalized_identity_ignores_case_and_spacing(self):
        first = {"title": " The Book ", "authors": ["A  Writer"]}
        second = {"title": "the book", "authors": ["a writer"]}
        self.assertEqual(MODULE.normalized_identity(first), MODULE.normalized_identity(second))

    def test_placeholder_titles_are_rejected(self):
        self.assertFalse(MODULE.acceptable_title(" Untitled "))
        self.assertFalse(MODULE.acceptable_title("[UNKNOWN]"))
        self.assertTrue(MODULE.acceptable_title("The Unknown"))

    def test_candidate_prompt_omits_embedding_derived_rank_and_score(self):
        candidate = {
            "work_key": "/works/OL1W", "title": "Book", "authors": ["Author"],
            "genres": ["mystery"], "description": "Description",
            "retrieval_rank": 1, "similarity_score": 0.9,
        }
        prompt = MODULE.candidate_prompt("A mystery", [candidate], 5)
        self.assertNotIn("retrieval_rank", prompt)
        self.assertNotIn("similarity_score", prompt)
        self.assertIn("untrusted book metadata", MODULE.SYSTEM_INSTRUCTION)

    def test_empty_gemini_response_reports_finish_reason(self):
        response = SimpleNamespace(
            parsed=None,
            text=None,
            candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")],
        )
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: response))
        with self.assertRaisesRegex(RuntimeError, "MAX_TOKENS"):
            MODULE.rerank(client, "quiet fantasy", [self.candidate(i) for i in range(5)], 5, "model")

    def test_local_fallback_returns_diversified_candidates(self):
        candidates = [self.candidate(i, genres=["fantasy"]) for i in range(6)]
        result = MODULE.local_fallback_rerank(candidates, 5)
        self.assertEqual("local-fallback", result["reranker"])
        self.assertEqual(5, len(result["recommendations"]))
        self.assertEqual([item["work_key"] for item in candidates[:5]], [
            item["work_key"] for item in result["recommendations"]
        ])
        self.assertTrue(all(item["reason"] for item in result["recommendations"]))

    def test_extracts_genre_exclusion_and_cleans_retrieval_query(self):
        constraints = MODULE.extract_constraints(
            "Something creepy and historical, but not outright horror"
        )
        self.assertEqual(("horror",), constraints.excluded_genres)
        self.assertEqual((), constraints.excluded_authors)
        self.assertEqual(("historical-fiction",), constraints.preferred_genres)
        self.assertNotIn("horror", constraints.retrieval_query.casefold())
        self.assertIn("historical", constraints.retrieval_query.casefold())

    def test_extracts_capitalized_author_without_misreading_prose(self):
        author = MODULE.extract_constraints("Something like Stephen King without Stephen King")
        self.assertEqual(("stephen king",), author.excluded_authors)
        science = MODULE.extract_constraints("Science fiction without a lot of complicated science")
        self.assertEqual((), science.excluded_authors)
        self.assertEqual((), science.excluded_genres)
        self.assertEqual("Science fiction", science.retrieval_query)
        self.assertEqual(("science-fiction",), science.preferred_genres)

    def test_extracts_possessive_and_by_author_requests(self):
        possessive = MODULE.extract_constraints("Morgan Vale's best book")
        by_author = MODULE.extract_constraints("Which books by Morgan Vale should I read?")
        lowercase_author = MODULE.extract_constraints("I'd like a book by ada quill")

        self.assertIn("morgan vale", possessive.requested_author_candidates)
        self.assertIn("morgan vale", by_author.requested_author_candidates)
        self.assertIn("ada quill", lowercase_author.requested_author_candidates)

    def test_diversification_enforces_hard_exclusions(self):
        candidates = [
            self.candidate(0, author="Stephen King", genres=["horror"]),
            self.candidate(1, author="Other Writer", genres=["horror"]),
        ] + [self.candidate(i) for i in range(2, 12)]
        constraints = MODULE.QueryConstraints(
            retrieval_query="dark suspense",
            excluded_genres=("horror",),
            excluded_authors=("stephen king",),
        )
        selected = MODULE.diversify_candidates(candidates, constraints, 5)
        self.assertEqual(5, len(selected))
        self.assertTrue(all("horror" not in item["genres"] for item in selected))
        self.assertTrue(all("Stephen King" not in item["authors"] for item in selected))

    def test_excluded_author_surname_is_removed_from_titles(self):
        candidates = [
            self.candidate(0, title="The Vampire King"),
            *[self.candidate(i) for i in range(1, 8)],
        ]
        constraints = MODULE.QueryConstraints(
            retrieval_query="Something like Stephen King",
            excluded_authors=("stephen king",),
        )
        selected = MODULE.diversify_candidates(candidates, constraints, 5)
        self.assertNotIn("The Vampire King", [item["title"] for item in selected])

    def test_diversification_limits_repeated_authors_and_subject_only_rows(self):
        repeated = [self.candidate(i, author="Same Author") for i in range(10)]
        subject_only = [self.candidate(i, quality="subject_only") for i in range(10, 30)]
        rich = [self.candidate(i) for i in range(30, 60)]
        selected = MODULE.diversify_candidates(
            repeated + subject_only + rich, MODULE.QueryConstraints("query"), 20
        )
        self.assertLessEqual(sum("Same Author" in item["authors"] for item in selected), 2)
        self.assertLessEqual(sum(item["retrieval_quality"] == "subject_only" for item in selected), 8)

    def test_response_must_use_distinct_candidate_ids(self):
        candidates = [{"work_key": f"/works/OL{i}W"} for i in range(5)]
        valid = MODULE.LibrarianResponse(recommendations=[
            MODULE.Recommendation(work_key=f"/works/OL{i}W", reason="Suitable") for i in range(5)
        ])
        MODULE.validate_response(valid, candidates, 5)
        invalid = MODULE.LibrarianResponse(recommendations=[
            MODULE.Recommendation(work_key="/works/OL0W", reason="Suitable") for _ in range(5)
        ])
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            MODULE.validate_response(invalid, candidates, 5)

    def test_cost_estimate_uses_input_and_output_rates(self):
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "thinking_tokens": 0}
        self.assertAlmostEqual(2.80, MODULE.estimated_cost(usage))


if __name__ == "__main__":
    unittest.main()
