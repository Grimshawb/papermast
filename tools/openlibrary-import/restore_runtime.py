#!/usr/bin/env python3
"""Verify and restore a packaged runtime collection from inside production Compose."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_and_verify(manifest_path: Path) -> tuple[Dict[str, Any], Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError("deployment manifest is not complete")
    snapshot_info = manifest["snapshot"]
    snapshot_path = manifest_path.parent / snapshot_info["file"]
    if not snapshot_path.is_file():
        raise RuntimeError(f"snapshot does not exist: {snapshot_path}")
    if snapshot_path.stat().st_size != snapshot_info["bytes"]:
        raise RuntimeError("snapshot size does not match deployment manifest")
    if file_sha256(snapshot_path) != snapshot_info["sha256"]:
        raise RuntimeError("snapshot SHA-256 does not match deployment manifest")
    return manifest, snapshot_path


def qdrant_request(
    base_url: str,
    path: str,
    api_key: str,
    method: str = "GET",
    body: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"api-key": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def collection_status(base_url: str, collection: str, api_key: str) -> Dict[str, Any] | None:
    path = f"/collections/{urllib.parse.quote(collection, safe='')}"
    try:
        return qdrant_request(base_url, path, api_key)["result"]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "restore", "status"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--qdrant-url", default=os.getenv("LIBRARIAN_QDRANT_URL", "http://qdrant:6333"))
    args = parser.parse_args()
    manifest, snapshot_path = load_and_verify(args.manifest)
    collection = manifest["collection"]
    expected = int(manifest["expected_points"])
    print(json.dumps({
        "verified": True,
        "collection": collection,
        "snapshot": str(snapshot_path),
        "bytes": snapshot_path.stat().st_size,
    }))
    if args.command == "verify":
        return 0

    api_key = os.getenv("QDRANT_API_KEY", "")
    if not api_key:
        raise RuntimeError("QDRANT_API_KEY is missing")
    current = collection_status(args.qdrant_url, collection, api_key)
    if args.command == "restore":
        if current is not None:
            raise RuntimeError(
                f"collection already exists: {collection}; restore into a new versioned collection"
            )
        quoted = urllib.parse.quote(collection, safe="")
        result = qdrant_request(
            args.qdrant_url,
            f"/collections/{quoted}/snapshots/recover?wait=true&checksum={manifest['snapshot']['sha256']}",
            api_key,
            method="PUT",
            body={"location": f"file://{snapshot_path}", "priority": "snapshot"},
        )
        print(json.dumps(result))
        current = collection_status(args.qdrant_url, collection, api_key)
    if current is None:
        raise RuntimeError(f"collection does not exist: {collection}")
    result = {
        "collection": collection,
        "status": current["status"],
        "points_count": current["points_count"],
        "indexed_vectors_count": current["indexed_vectors_count"],
    }
    print(json.dumps(result, indent=2))
    if (
        result["status"] != "green"
        or result["points_count"] != expected
        or result["indexed_vectors_count"] != expected
    ):
        raise RuntimeError("restored collection is not ready or has unexpected counts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
