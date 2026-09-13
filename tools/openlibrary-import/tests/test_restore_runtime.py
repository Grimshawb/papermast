import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "restore_runtime.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("restore_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RestoreRuntimeTests(unittest.TestCase):
    def test_verifies_snapshot_size_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "catalog.snapshot"
            snapshot.write_bytes(b"runtime catalog")
            manifest = root / "deployment-manifest.json"
            manifest.write_text(json.dumps({
                "status": "complete",
                "snapshot": {
                    "file": snapshot.name,
                    "bytes": snapshot.stat().st_size,
                    "sha256": MODULE.file_sha256(snapshot),
                },
            }))

            _, verified_snapshot = MODULE.load_and_verify(manifest)

            self.assertEqual(snapshot, verified_snapshot)

    def test_rejects_modified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "catalog.snapshot"
            snapshot.write_bytes(b"changed")
            manifest = root / "deployment-manifest.json"
            manifest.write_text(json.dumps({
                "status": "complete",
                "snapshot": {
                    "file": snapshot.name,
                    "bytes": snapshot.stat().st_size,
                    "sha256": "0" * 64,
                },
            }))

            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                MODULE.load_and_verify(manifest)


if __name__ == "__main__":
    unittest.main()
