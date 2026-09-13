#!/usr/bin/env python3
"""Build the production-shaped Qdrant collection from versioned local artifacts."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import duckdb
import numpy as np
from qdrant_client import QdrantClient, models

from embedding_contract import RUNTIME_COLLECTION, file_sha256, utc_now
from qdrant_catalog import atomic_json, decoded_payload, point_id, read_manifest


STATE_VERSION = 1


def create_collection(client: QdrantClient, name: str, dimensions: int) -> None:
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=dimensions, distance=models.Distance.COSINE, on_disk=True,
        ),
        on_disk_payload=True,
        hnsw_config=models.HnswConfigDiff(
            m=16, ef_construct=100, on_disk=True, max_indexing_threads=2,
        ),
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=0, max_optimization_threads=2,
        ),
    )
    for field, schema in (
        ("genres", models.PayloadSchemaType.KEYWORD),
        ("authors_normalized", models.PayloadSchemaType.KEYWORD),
        ("retrieval_quality", models.PayloadSchemaType.KEYWORD),
        ("metadata_quality_score", models.PayloadSchemaType.INTEGER),
    ):
        client.create_payload_index(name, field, schema, wait=True)


def catalog_rows(
    connection: duckdb.DuckDBPyConnection, catalog_path: Path, keys: List[str]
) -> Dict[str, Dict[str, Any]]:
    result = connection.execute("""
        SELECT work_key, subjects, description, publication_date, page_count,
               edition_count, english_edition_count
        FROM read_parquet(?)
        WHERE work_key IN (SELECT unnest(?))
    """, [str(catalog_path), keys])
    columns = [item[0] for item in result.description]
    return {row[0]: dict(zip(columns, row)) for row in result.fetchall()}


def points_for_shard(
    connection: duckdb.DuckDBPyConnection,
    catalog_path: Path,
    vector_path: Path,
    metadata_path: Path,
    expected_count: int,
) -> Iterable[models.PointStruct]:
    vectors = np.load(vector_path, mmap_mode="r", allow_pickle=False)
    records = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines()]
    if vectors.shape != (expected_count, 384) or len(records) != expected_count:
        raise RuntimeError(f"invalid embedding shard: {vector_path.name}")
    rows = catalog_rows(connection, catalog_path, [record["work_key"] for record in records])
    if len(rows) != expected_count:
        raise RuntimeError(f"catalog is missing records for {metadata_path.name}")
    for index, record in enumerate(records):
        catalog = rows[record["work_key"]]
        payload = decoded_payload(record)
        payload.update({
            "authors_normalized": [" ".join(item.casefold().split()) for item in payload["authors"]],
            "subjects": catalog["subjects"] or [],
            "description": (catalog["description"] or "")[:1200],
            "publication_date": catalog["publication_date"],
            "page_count": catalog["page_count"],
            "edition_count": catalog["edition_count"],
            "english_edition_count": catalog["english_edition_count"],
        })
        yield models.PointStruct(
            id=point_id(record["work_key"]),
            vector=vectors[index].tolist(),
            payload=payload,
        )


def build(args: argparse.Namespace) -> int:
    manifest = read_manifest(args.embeddings)
    catalog_manifest = json.loads(args.catalog_manifest.read_text(encoding="utf-8"))
    catalog_path = args.catalog_manifest.parent / catalog_manifest["artifact"]["file"]
    if file_sha256(catalog_path) != catalog_manifest["artifact"]["sha256"]:
        raise RuntimeError("catalog artifact checksum failed")
    if catalog_manifest["source_identity_xor"] != manifest["source_identity_xor"]:
        raise RuntimeError("catalog and embeddings do not describe the same work set")

    qdrant = QdrantClient(url=args.url, timeout=120)
    create_collection(qdrant, args.collection, manifest["dimensions"])
    state_path = args.embeddings / f"{args.collection}-import-state.json"
    identity = {
        "state_version": STATE_VERSION,
        "collection": args.collection,
        "source_identity_xor": manifest["source_identity_xor"],
        "source_count": manifest["target_count"],
        "catalog_sha256": catalog_manifest["artifact"]["sha256"],
    }
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if any(state.get(key) != value for key, value in identity.items()):
            raise RuntimeError("existing runtime import state has a different source identity")
    else:
        info = qdrant.get_collection(args.collection)
        if info.points_count:
            raise RuntimeError("runtime collection has points but no matching import state")
        state = {**identity, "status": "importing", "completed_shards": [], "completed_points": 0}
        atomic_json(state_path, state)

    connection = duckdb.connect()
    try:
        completed = len(state["completed_shards"])
        for index, shard in enumerate(manifest["shards"]):
            if index < completed:
                continue
            vector_path = args.embeddings / shard["vectors_file"]
            metadata_path = args.embeddings / shard["metadata_file"]
            if file_sha256(vector_path) != shard["vectors_sha256"]:
                raise RuntimeError(f"vector checksum failed for shard {index}")
            if file_sha256(metadata_path) != shard["metadata_sha256"]:
                raise RuntimeError(f"metadata checksum failed for shard {index}")
            started = time.monotonic()
            qdrant.upload_points(
                collection_name=args.collection,
                points=points_for_shard(
                    connection, catalog_path, vector_path, metadata_path, shard["count"]
                ),
                batch_size=args.batch_size,
                parallel=1,
                max_retries=3,
                wait=True,
            )
            elapsed = time.monotonic() - started
            state["completed_shards"].append({"index": index, "count": shard["count"], "seconds": elapsed})
            state["completed_points"] += shard["count"]
            state["updated_at_utc"] = utc_now()
            atomic_json(state_path, state)
            print(f"Completed {index + 1}/{len(manifest['shards'])}: {shard['count'] / elapsed:.0f} points/s", flush=True)
            if args.cooldown_seconds and index + 1 < len(manifest["shards"]):
                time.sleep(args.cooldown_seconds)
    finally:
        connection.close()

    qdrant.update_collection(
        collection_name=args.collection,
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=20_000, max_optimization_threads=2,
        ),
    )
    state["status"] = "optimizing"
    state["updated_at_utc"] = utc_now()
    atomic_json(state_path, state)
    print("Upload complete; Qdrant is building the runtime HNSW index.", flush=True)
    return 0


def status(args: argparse.Namespace) -> int:
    info = QdrantClient(url=args.url).get_collection(args.collection)
    result = {
        "collection": args.collection,
        "status": str(info.status),
        "optimizer_status": str(info.optimizer_status),
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "segments_count": info.segments_count,
    }
    state_path = args.embeddings / f"{args.collection}-import-state.json"
    if (
        str(info.status).casefold().endswith("green")
        and info.points_count == info.indexed_vectors_count
        and state_path.is_file()
    ):
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("collection") == args.collection:
            state["status"] = "complete"
            state["completed_at_utc"] = state.get("completed_at_utc", utc_now())
            state["updated_at_utc"] = utc_now()
            atomic_json(state_path, state)
    print(json.dumps(result, indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--url", default="http://127.0.0.1:6333")
    common.add_argument("--collection", default=RUNTIME_COLLECTION)
    builder = sub.add_parser("build", parents=[common])
    builder.add_argument("--embeddings", type=Path, default=Path(".data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1"))
    builder.add_argument("--catalog-manifest", type=Path, default=Path(".data/openlibrary/production/catalog-v1/manifest.json"))
    builder.add_argument("--batch-size", type=int, default=256)
    builder.add_argument("--cooldown-seconds", type=float, default=0.25)
    builder.set_defaults(function=build)
    checker = sub.add_parser("status", parents=[common])
    checker.add_argument("--embeddings", type=Path, default=Path(".data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1"))
    checker.set_defaults(function=status)
    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
