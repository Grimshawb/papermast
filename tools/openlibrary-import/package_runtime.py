#!/usr/bin/env python3
"""Download and checksum the versioned Qdrant runtime snapshot for deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict

from embedding_contract import FASTEMBED_MODEL_REVISION, utc_now


SCHEMA_VERSION = 1
QDRANT_IMAGE = "qdrant/qdrant:v1.15.5"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def download_snapshot(url: str, api_key: str | None, destination: Path) -> str:
    request = urllib.request.Request(url)
    if api_key:
        request.add_header("api-key", api_key)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".part", dir=destination.parent
    )
    temporary = Path(temporary_name)
    digest = hashlib.sha256()
    try:
        with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(request, timeout=120) as response:
            while block := response.read(8 * 1024 * 1024):
                output.write(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return digest.hexdigest()


def package(args: argparse.Namespace) -> int:
    source_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    qdrant = source_manifest["qdrant"]
    snapshot = qdrant["snapshot"]
    if qdrant["collection"] != args.collection:
        raise RuntimeError(
            f"manifest collection is {qdrant['collection']}, expected {args.collection}"
        )
    if qdrant["points_count"] != source_manifest["row_count"]:
        raise RuntimeError("manifest Qdrant and catalog counts do not match")

    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / snapshot["name"]
    expected_bytes = int(snapshot["bytes"])
    source_manifest_sha256 = sha256(args.manifest)
    deployment_path = args.output / "deployment-manifest.json"
    snapshot_url = (
        f"{args.qdrant_url.rstrip('/')}/collections/"
        f"{urllib.parse.quote(args.collection, safe='')}/snapshots/"
        f"{urllib.parse.quote(snapshot['name'], safe='')}"
    )
    snapshot_sha256 = ""
    if destination.is_file() and destination.stat().st_size == expected_bytes and deployment_path.is_file():
        previous = json.loads(deployment_path.read_text(encoding="utf-8"))
        previous_snapshot = previous.get("snapshot", {})
        if (
            previous.get("source_manifest_sha256") == source_manifest_sha256
            and previous_snapshot.get("file") == destination.name
            and previous_snapshot.get("bytes") == expected_bytes
        ):
            candidate_sha256 = sha256(destination)
            if candidate_sha256 == previous_snapshot.get("sha256"):
                snapshot_sha256 = candidate_sha256
    if not snapshot_sha256:
        snapshot_sha256 = download_snapshot(
            snapshot_url, os.getenv("QDRANT_API_KEY") or None, destination
        )
    if destination.stat().st_size != expected_bytes:
        destination.unlink(missing_ok=True)
        raise RuntimeError("downloaded snapshot size does not match the source manifest")

    deployment = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete",
        "generated_at_utc": utc_now(),
        "catalog_version": source_manifest["catalog_version"],
        "collection": args.collection,
        "expected_points": qdrant["points_count"],
        "qdrant_image": QDRANT_IMAGE,
        "embedding": source_manifest["embedding"],
        "fastembed_model_revision": FASTEMBED_MODEL_REVISION,
        "snapshot": {
            "file": destination.name,
            "bytes": expected_bytes,
            "sha256": snapshot_sha256,
        },
        "source_manifest_sha256": source_manifest_sha256,
    }
    atomic_json(deployment_path, deployment)
    print(json.dumps({
        "collection": args.collection,
        "points": qdrant["points_count"],
        "snapshot": str(destination.resolve()),
        "bytes": expected_bytes,
        "sha256": snapshot_sha256,
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".data/openlibrary/production/catalog-v1/manifest.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".data/openlibrary/deployment/catalog-v1"),
    )
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    parser.add_argument("--collection", default="papermast_fiction_bge_runtime_v1")
    args = parser.parse_args()
    if not args.manifest.is_file():
        parser.error(f"manifest does not exist: {args.manifest}")
    return package(args)


if __name__ == "__main__":
    raise SystemExit(main())
