import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "openlibrary_import.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("openlibrary_import", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def dump_line(key, record):
    return f"/type/work\t{key}\t1\t2026-08-01T00:00:00.000000\t{json.dumps(record)}\n".encode()


class ParsingTests(unittest.TestCase):
    def test_recognizes_archive_download_url_shapes(self):
        direct = "https://archive.org/download/ol_dump_2026-07-31/file.txt.gz"
        mirror = "https://ia600708.us.archive.org/27/items/ol_dump_2026-07-31/file.txt.gz"
        self.assertEqual("ol_dump_2026-07-31", MODULE.archive_identifier(direct))
        self.assertEqual("ol_dump_2026-07-31", MODULE.archive_identifier(mirror))

    def test_parses_five_column_dump_line(self):
        parsed, error = MODULE.parse_dump_line(dump_line("/works/OL1W", {"title": "A Book"}))
        self.assertIsNone(error)
        self.assertEqual("/works/OL1W", parsed["key"])
        self.assertEqual("A Book", parsed["record"]["title"])

    def test_reports_malformed_tsv_and_json(self):
        self.assertEqual("malformed_tsv", MODULE.parse_dump_line(b"too\tfew\n")[1])
        self.assertEqual("invalid_json", MODULE.parse_dump_line(b"a\tb\tc\td\t{nope}\n")[1])

    def test_extracts_plain_and_object_text(self):
        self.assertEqual("plain", MODULE.open_library_text(" plain "))
        self.assertEqual("object", MODULE.open_library_text({"value": " object "}))
        self.assertEqual("", MODULE.open_library_text(None))

    def test_rejection_reasons(self):
        complete = {
            "title": "Complete",
            "authors": [{"author": {"key": "/authors/OL1A"}}],
            "subjects": ["One", "Two", "Three"],
            "covers": [123],
            "first_publish_date": "2001",
        }
        self.assertEqual([], MODULE.rejection_reasons(complete))
        reasons = MODULE.rejection_reasons({})
        self.assertEqual(
            ["missing_title", "missing_author", "insufficient_descriptive_metadata", "missing_cover", "missing_or_invalid_publication_year"],
            reasons,
        )


class BoundedStructuresTests(unittest.TestCase):
    def test_subject_counter_never_exceeds_capacity(self):
        counter = MODULE.BoundedCounter(10)
        for index in range(10_000):
            counter.add(f"subject-{index}")
        self.assertLessEqual(len(counter.counts), 10)
        self.assertLessEqual(len(counter.heap), 40)

    def test_subject_counter_retains_frequent_values(self):
        counter = MODULE.BoundedCounter(10)
        for index in range(1_000):
            counter.add("fantasy")
            counter.add(f"subject-{index}")
        self.assertEqual("fantasy", counter.top(1)[0]["subject"])

    def test_reservoir_is_deterministic(self):
        first = MODULE.ReservoirSampler(5, 42)
        second = MODULE.ReservoirSampler(5, 42)
        for index in range(100):
            first.add({"value": index})
            second.add({"value": index})
        self.assertEqual(first.items, second.items)


class ProfileIntegrationTests(unittest.TestCase):
    def test_download_metadata_records_dump_identity_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            dump = Path(directory) / "ol_dump_works_2026-07-31.txt.gz"
            dump.write_bytes(b"fixture")
            hashes = MODULE.file_hashes(dump, ["sha256", "md5"])
            MODULE.write_download_metadata(
                dump,
                "https://openlibrary.org/data/ol_dump_works_latest.txt.gz",
                "https://archive.org/download/item/ol_dump_works_2026-07-31.txt.gz",
                hashes,
                hashes["md5"],
                "2026-08-26T00:00:00Z",
            )
            metadata = json.loads(Path(f"{dump}.metadata.json").read_text())
            self.assertEqual("2026-07-31", metadata["dump_date"])
            self.assertEqual(7, metadata["size_bytes"])
            self.assertTrue(metadata["archive_md5_verified"])

    def test_profiles_fixture_and_writes_matching_reports(self):
        records = [
            dump_line("/works/OL1W", {
                "title": "Complete", "subtitle": "A Novel",
                "authors": [{"author": {"key": "/authors/OL1A"}}],
                "description": {"value": "A sufficiently useful description."},
                "subjects": ["Fantasy", "Adventure", "Friendship"], "covers": [1],
                "first_publish_date": "2001", "original_languages": [{"key": "/languages/eng"}],
            }),
            dump_line("/works/OL2W", {"title": "Sparse"}),
            b"bad\trow\n",
            b"/type/work\t/works/OL3W\t1\tdate\t{bad json}\n",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture.txt.gz"
            with gzip.open(fixture, "wb") as handle:
                for record in records:
                    handle.write(record)
            json_path, markdown_path = MODULE.profile_dump(fixture, root / "reports", 7, 5, 20)
            report = json.loads(json_path.read_text())
            markdown = markdown_path.read_text()
            self.assertEqual(4, report["totals"]["total_rows"])
            self.assertEqual(2, report["totals"]["valid_records"])
            self.assertEqual(1, report["totals"]["malformed_tsv"])
            self.assertEqual(1, report["totals"]["invalid_json"])
            self.assertEqual(1, report["qualification_funnel"]["plus_publication_year"]["count"])
            self.assertIn("| total_rows | 4 |", markdown)
            self.assertIn("| valid_records | 2 |", markdown)
            self.assertEqual([], report["samples"]["qualifying"][0]["rejection_reasons"])

    def test_ingests_and_merges_all_dump_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            works = root / "ol_dump_works_2026-07-31.txt.gz"
            authors = root / "ol_dump_authors_2026-07-31.txt.gz"
            editions = root / "ol_dump_editions_2026-07-31.txt.gz"
            with gzip.open(works, "wb") as handle:
                handle.write(dump_line("/works/OL1W", {
                    "title": "The Test Book",
                    "authors": [{"author": {"key": "/authors/OL1A"}}],
                    "subjects": ["Fiction", "Adventure", "Friendship"],
                }))
            with gzip.open(authors, "wb") as handle:
                handle.write(dump_line("/authors/OL1A", {"name": "Test Author"}).replace(b"/type/work", b"/type/author", 1))
            with gzip.open(editions, "wb") as handle:
                handle.write(dump_line("/books/OL1M", {
                    "title": "The Test Book", "works": [{"key": "/works/OL1W"}],
                    "languages": [{"key": "/languages/eng"}], "isbn_13": ["9780000000002"],
                    "covers": [123], "number_of_pages": 250, "publish_date": "2020",
                }).replace(b"/type/work", b"/type/edition", 1))

            database = root / "catalog.duckdb"
            temporary = root / "tmp"
            for dataset, path in (("works", works), ("authors", authors), ("editions", editions)):
                result = MODULE.ingest_dataset(database, dataset, path, temporary, "512MB", 1)
                self.assertEqual("imported", result["status"])
                self.assertEqual(1, result["row_count"])
                repeated = MODULE.ingest_dataset(database, dataset, path, temporary, "512MB", 1)
                self.assertEqual("unchanged", repeated["status"])
            merged = MODULE.rebuild_catalog(database, temporary, "512MB", 1)
            self.assertEqual(1, merged["catalog_candidates"])
            self.assertEqual(1, merged["metadata_capable_english"])
            audit = MODULE.classify_fiction(database, temporary, "512MB", 1, 17, 2)
            self.assertEqual(1, audit["totals"]["total"])
            self.assertEqual(1, audit["totals"]["high"])
            self.assertEqual(1, audit["totals"]["accepted"])
            self.assertEqual(0, audit["totals"]["review_candidates"])
            self.assertEqual(1, audit["totals"]["without_description"])
            self.assertEqual("explicit_subject", audit["samples"]["high_explicit"][0]["primary_evidence"])
            repeated_audit = MODULE.classify_fiction(database, temporary, "512MB", 1, 17, 2)
            self.assertEqual(audit["samples"], repeated_audit["samples"])
            documents = MODULE.prepare_retrieval_documents(database, temporary, "512MB", 1, 17, 2)
            self.assertEqual(1, documents["totals"]["total"])
            self.assertEqual(1, documents["totals"]["subject_only"])
            prepared = documents["samples"]["subject_only"][0]
            self.assertIn("Title: The Test Book", prepared["embedding_text"])
            self.assertIn("Subjects: friendship; adventure", prepared["embedding_text"])
            self.assertNotIn("Subjects: fiction", prepared["embedding_text"])
            status = MODULE.catalog_status(database)
            self.assertEqual(3, len(status["imports"]))


if __name__ == "__main__":
    unittest.main()
