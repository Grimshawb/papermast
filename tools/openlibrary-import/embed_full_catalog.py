#!/usr/bin/env python3
"""Generate resumable, sharded local BGE embeddings for the fiction catalog."""

from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import duckdb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from embedding_pilot import MODEL_ID, MODEL_REVISION, atomic_write, file_sha256, utc_now


SCHEMA_VERSION = 1
DIMENSIONS = 384


def atomic_save_npy(path: Path, vectors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        np.save(handle, vectors, allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def build_corpus(connection: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    if not connection.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name='retrieval_documents'").fetchone()[0]:
        raise RuntimeError("retrieval_documents does not exist; run prepare-documents first")
    connection.execute("DROP TABLE IF EXISTS embedding_corpus_staging")
    connection.execute("""
        CREATE TABLE embedding_corpus_staging AS
        SELECT
            row_number() OVER (ORDER BY work_key) - 1 AS embedding_index,
            work_key, document_hash, document_version, embedding_text,
            title, author_names, genres, retrieval_quality,
            metadata_quality_score, representative_edition_key,
            representative_covers_json, representative_isbn_10_json,
            representative_isbn_13_json
        FROM retrieval_documents
    """)
    connection.execute("DROP TABLE IF EXISTS embedding_corpus")
    connection.execute("ALTER TABLE embedding_corpus_staging RENAME TO embedding_corpus")
    result = connection.execute("""
        SELECT count(*) AS count,
               min(work_key) AS first_work_key,
               max(work_key) AS last_work_key,
               bit_xor(hash(work_key || ':' || document_hash)) AS identity_xor,
               min(document_version) AS min_document_version,
               max(document_version) AS max_document_version
        FROM embedding_corpus
    """)
    return dict(zip([item[0] for item in result.description], result.fetchone()))


def read_rows(connection: duckdb.DuckDBPyConnection, start: int, stop: int) -> List[Dict[str, Any]]:
    result = connection.execute("""
        SELECT * FROM embedding_corpus
        WHERE embedding_index >= ? AND embedding_index < ?
        ORDER BY embedding_index
    """, [start, stop])
    columns = [item[0] for item in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def manifest_identity(corpus: Dict[str, Any], target_count: int, shard_size: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": DIMENSIONS,
        "normalized": True,
        "distance": "cosine",
        "document_version": corpus["min_document_version"],
        "source_count": corpus["count"],
        "target_count": target_count,
        "source_identity_xor": str(corpus["identity_xor"]),
        "first_work_key": corpus["first_work_key"],
        "last_work_key": corpus["last_work_key"],
        "shard_size": shard_size,
    }


def validate_completed_shards(output: Path, manifest: Dict[str, Any]) -> None:
    for shard in manifest.get("shards", []):
        vector_path = output / shard["vectors_file"]
        metadata_path = output / shard["metadata_file"]
        if not vector_path.is_file() or not metadata_path.is_file():
            raise RuntimeError(f"completed shard {shard['shard']} is missing an artifact")
        if file_sha256(vector_path) != shard["vectors_sha256"]:
            raise RuntimeError(f"completed shard {shard['shard']} vector checksum does not match")
        if file_sha256(metadata_path) != shard["metadata_sha256"]:
            raise RuntimeError(f"completed shard {shard['shard']} metadata checksum does not match")
        vectors = np.load(vector_path, mmap_mode="r", allow_pickle=False)
        if vectors.shape != (shard["count"], DIMENSIONS) or vectors.dtype != np.float32:
            raise RuntimeError(f"completed shard {shard['shard']} has invalid vector shape or type")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=10_000)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=0.0,
        help="pause after each completed shard to reduce sustained thermal load",
    )
    parser.add_argument("--limit", type=int, help="embed only the first N rows for validation")
    args = parser.parse_args()
    if (
        args.shard_size < 1
        or args.batch_size < 1
        or args.cooldown_seconds < 0
        or (args.limit is not None and args.limit < 1)
    ):
        parser.error("shard size and batch size must be positive; cooldown must be nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(args.database))
    print("Materializing stable embedding order...", flush=True)
    corpus = build_corpus(connection)
    if corpus["min_document_version"] != corpus["max_document_version"]:
        raise RuntimeError("retrieval documents contain multiple document versions")
    target_count = min(corpus["count"], args.limit or corpus["count"])
    identity = manifest_identity(corpus, target_count, args.shard_size)
    manifest_path = args.output / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_identity = {key: manifest.get(key) for key in identity}
        if existing_identity != identity:
            raise RuntimeError(
                "existing manifest does not match this corpus/configuration; use a new output directory"
            )
        validate_completed_shards(args.output, manifest)
    else:
        manifest = {
            **identity,
            "status": "running",
            "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(),
            "shards": [],
            "total_embedding_seconds": 0.0,
        }
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())

    completed = sum(shard["count"] for shard in manifest["shards"])
    expected_completed = min(len(manifest["shards"]) * args.shard_size, target_count)
    if completed != expected_completed:
        raise RuntimeError("manifest shard sequence is incomplete or non-contiguous")
    if completed == target_count:
        print(json.dumps({"status": "complete", "count": target_count, "shards": len(manifest["shards"])}, indent=2))
        connection.close()
        return 0

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = SentenceTransformer(
        MODEL_ID,
        revision=MODEL_REVISION,
        cache_folder=str((args.output.parent / "models").resolve()),
        device=device,
    )
    total_shards = math.ceil(target_count / args.shard_size)
    while completed < target_count:
        shard_number = len(manifest["shards"])
        stop = min(completed + args.shard_size, target_count)
        rows = read_rows(connection, completed, stop)
        if len(rows) != stop - completed:
            raise RuntimeError(f"database returned {len(rows)} rows for range {completed}:{stop}")
        # PyTorch's MPS allocator otherwise retains buffers across successive
        # encode calls. On long catalogs that can force macOS into compression
        # and swap, making later shards dramatically slower than earlier ones.
        if device == "mps":
            torch.mps.empty_cache()
        print(f"Embedding shard {shard_number + 1}/{total_shards} ({completed:,}:{stop:,})...", flush=True)
        started = time.monotonic()
        vectors = model.encode(
            [row["embedding_text"] for row in rows],
            batch_size=args.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32, copy=False)
        elapsed = time.monotonic() - started
        if vectors.shape != (len(rows), DIMENSIONS) or not np.isfinite(vectors).all():
            raise RuntimeError(f"shard {shard_number} produced invalid vectors")
        norms = np.linalg.norm(vectors, axis=1)
        if float(norms.min()) < 0.999 or float(norms.max()) > 1.001:
            raise RuntimeError(f"shard {shard_number} vectors are not normalized")

        base = f"shard-{shard_number:05d}"
        vector_path = args.output / f"{base}.npy"
        metadata_path = args.output / f"{base}.jsonl"
        atomic_save_npy(vector_path, vectors)
        metadata = b"".join(
            (json.dumps({key: value for key, value in row.items() if key != "embedding_text"}, ensure_ascii=False, default=str) + "\n").encode("utf-8")
            for row in rows
        )
        atomic_write(metadata_path, metadata)
        shard = {
            "shard": shard_number,
            "start_index": completed,
            "stop_index": stop,
            "count": len(rows),
            "first_work_key": rows[0]["work_key"],
            "last_work_key": rows[-1]["work_key"],
            "vectors_file": vector_path.name,
            "vectors_sha256": file_sha256(vector_path),
            "metadata_file": metadata_path.name,
            "metadata_sha256": file_sha256(metadata_path),
            "embedding_seconds": elapsed,
            "documents_per_second": len(rows) / elapsed,
        }
        manifest["shards"].append(shard)
        manifest["total_embedding_seconds"] += elapsed
        manifest["updated_at_utc"] = utc_now()
        completed = stop
        if completed == target_count:
            manifest["status"] = "complete"
            manifest["completed_at_utc"] = utc_now()
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())
        print(f"Completed shard {shard_number + 1}: {len(rows):,} documents at {shard['documents_per_second']:.1f}/s", flush=True)
        if completed < target_count and args.cooldown_seconds:
            print(f"Cooling down for {args.cooldown_seconds:g} seconds...", flush=True)
            time.sleep(args.cooldown_seconds)

    connection.close()
    print(json.dumps({
        "status": manifest["status"],
        "count": target_count,
        "shards": len(manifest["shards"]),
        "embedding_seconds": manifest["total_embedding_seconds"],
        "average_documents_per_second": target_count / manifest["total_embedding_seconds"],
        "output": str(args.output.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
