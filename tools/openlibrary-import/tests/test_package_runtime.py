import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "package_runtime.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("package_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PackageRuntimeTests(unittest.TestCase):
    def test_rejects_evaluation_collection_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "row_count": 1,
                "qdrant": {
                    "collection": "evaluation_collection",
                    "points_count": 1,
                    "snapshot": {"name": "test.snapshot", "bytes": 1},
                },
            }))
            args = SimpleNamespace(
                manifest=manifest,
                output=root / "output",
                qdrant_url="http://127.0.0.1:6333",
                collection="runtime_collection",
            )

            with self.assertRaisesRegex(RuntimeError, "manifest collection"):
                MODULE.package(args)

    def test_existing_snapshot_is_checksummed_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()
            snapshot = output / "runtime.snapshot"
            snapshot.write_bytes(b"snapshot")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "catalog_version": 1,
                "row_count": 1,
                "embedding": {"model_id": "model"},
                "qdrant": {
                    "collection": "runtime_collection",
                    "points_count": 1,
                    "snapshot": {"name": snapshot.name, "bytes": snapshot.stat().st_size},
                },
            }))
            (output / "deployment-manifest.json").write_text(json.dumps({
                "source_manifest_sha256": MODULE.sha256(manifest),
                "snapshot": {
                    "file": snapshot.name,
                    "bytes": snapshot.stat().st_size,
                    "sha256": MODULE.sha256(snapshot),
                },
            }))
            args = SimpleNamespace(
                manifest=manifest,
                output=output,
                qdrant_url="http://127.0.0.1:6333",
                collection="runtime_collection",
            )

            with patch.object(MODULE, "download_snapshot") as download:
                self.assertEqual(0, MODULE.package(args))

            download.assert_not_called()
            deployment = json.loads((output / "deployment-manifest.json").read_text())
            self.assertEqual(MODULE.sha256(snapshot), deployment["snapshot"]["sha256"])

    def test_same_size_snapshot_without_matching_manifest_is_downloaded_again(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.mkdir()
            snapshot = output / "runtime.snapshot"
            snapshot.write_bytes(b"bad-data")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "catalog_version": 1,
                "row_count": 1,
                "embedding": {"model_id": "model"},
                "qdrant": {
                    "collection": "runtime_collection",
                    "points_count": 1,
                    "snapshot": {"name": snapshot.name, "bytes": 8},
                },
            }))
            args = SimpleNamespace(
                manifest=manifest,
                output=output,
                qdrant_url="http://127.0.0.1:6333",
                collection="runtime_collection",
            )

            def replace_snapshot(_url, _api_key, destination):
                destination.write_bytes(b"new-data")
                return MODULE.sha256(destination)

            with patch.object(MODULE, "download_snapshot", side_effect=replace_snapshot) as download:
                self.assertEqual(0, MODULE.package(args))

            download.assert_called_once()
            self.assertEqual(b"new-data", snapshot.read_bytes())


if __name__ == "__main__":
    unittest.main()
