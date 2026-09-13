#!/usr/bin/env python3
"""Load and query the local PaperMast fiction vectors in Qdrant."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from qdrant_client import QdrantClient, models

from embedding_contract import MODEL_ID, MODEL_REVISION, QUERIES, QUERY_PREFIX, file_sha256, utc_now


COLLECTION = "papermast_fiction_bge_v1"
POINT_NAMESPACE = uuid.UUID("ff46e9fc-359f-58fd-9c33-58eb5b20be67")
STATE_VERSION = 1


def atomic_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def client(url: str) -> QdrantClient:
    return QdrantClient(url=url, timeout=120)


def source_identity(manifest: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model_id": manifest["model_id"],
        "model_revision": manifest["model_revision"],
        "dimensions": manifest["dimensions"],
        "distance": manifest["distance"],
        "document_version": manifest["document_version"],
        "source_count": manifest["target_count"],
        "source_identity_xor": manifest["source_identity_xor"],
        "shard_size": manifest["shard_size"],
        "shard_count": len(manifest["shards"]),
    }


def read_manifest(source: Path) -> Dict[str, Any]:
    path = source / "manifest.json"
    if not path.is_file():
        raise RuntimeError(f"embedding manifest does not exist: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError("embedding manifest is not complete")
    if manifest.get("dimensions") != 384 or manifest.get("distance") != "cosine":
        raise RuntimeError("embedding manifest has an unexpected vector contract")
    if sum(item["count"] for item in manifest["shards"]) != manifest["target_count"]:
        raise RuntimeError("embedding manifest shard counts do not match target count")
    return manifest


def create_collection(qdrant: QdrantClient, collection: str, dimensions: int) -> None:
    if qdrant.collection_exists(collection):
        return
    qdrant.create_collection(
        collection_name=collection,
        vectors_config=models.VectorParams(
            size=dimensions,
            distance=models.Distance.COSINE,
            on_disk=True,
        ),
        on_disk_payload=True,
        hnsw_config=models.HnswConfigDiff(
            m=16,
            ef_construct=100,
            on_disk=True,
            max_indexing_threads=2,
        ),
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=0,
            max_optimization_threads=2,
        ),
    )
    for field, schema in (
        ("genres", models.PayloadSchemaType.KEYWORD),
        ("retrieval_quality", models.PayloadSchemaType.KEYWORD),
        ("metadata_quality_score", models.PayloadSchemaType.INTEGER),
    ):
        qdrant.create_payload_index(collection, field, schema, wait=True)


def point_id(work_key: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, work_key))


def decoded_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "embedding_index": record["embedding_index"],
        "work_key": record["work_key"],
        "document_hash": record["document_hash"],
        "document_version": record["document_version"],
        "title": record["title"],
        "authors": record.get("author_names") or [],
        "genres": record.get("genres") or [],
        "retrieval_quality": record.get("retrieval_quality"),
        "metadata_quality_score": record.get("metadata_quality_score"),
        "representative_edition_key": record.get("representative_edition_key"),
        "covers": json.loads(record.get("representative_covers_json") or "[]"),
        "isbn_10": json.loads(record.get("representative_isbn_10_json") or "[]"),
        "isbn_13": json.loads(record.get("representative_isbn_13_json") or "[]"),
    }


def shard_points(vector_path: Path, metadata_path: Path, expected_count: int) -> Iterable[models.PointStruct]:
    vectors = np.load(vector_path, mmap_mode="r", allow_pickle=False)
    if vectors.shape != (expected_count, 384) or vectors.dtype != np.float32:
        raise RuntimeError(f"invalid vector shard: {vector_path.name}")
    with metadata_path.open("r", encoding="utf-8") as handle:
        count = 0
        for count, line in enumerate(handle, 1):
            if count > expected_count:
                raise RuntimeError(f"metadata has too many rows: {metadata_path.name}")
            record = json.loads(line)
            yield models.PointStruct(
                id=point_id(record["work_key"]),
                vector=vectors[count - 1].tolist(),
                payload=decoded_payload(record),
            )
    if count != expected_count:
        raise RuntimeError(f"metadata row count mismatch: {metadata_path.name}")


def import_catalog(args: argparse.Namespace) -> int:
    manifest = read_manifest(args.source)
    identity = source_identity(manifest)
    state_path = args.source / "qdrant-import-state.json"
    qdrant = client(args.url)
    create_collection(qdrant, args.collection, manifest["dimensions"])
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        expected = {"state_version": STATE_VERSION, "collection": args.collection, **identity}
        actual = {key: state.get(key) for key in expected}
        if actual != expected:
            raise RuntimeError("existing Qdrant import state does not match this collection/source")
    else:
        info = qdrant.get_collection(args.collection)
        if info.points_count:
            raise RuntimeError("collection contains points but has no matching local import state")
        state = {
            "state_version": STATE_VERSION,
            "collection": args.collection,
            **identity,
            "status": "importing",
            "completed_shards": [],
            "completed_points": 0,
            "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(),
        }
        atomic_json(state_path, state)

    completed = len(state["completed_shards"])
    if completed == len(manifest["shards"]):
        info = qdrant.get_collection(args.collection)
        if info.points_count != manifest["target_count"]:
            raise RuntimeError(
                f"Qdrant contains {info.points_count} points; expected {manifest['target_count']}"
            )
        if info.indexed_vectors_count == manifest["target_count"]:
            state["status"] = "complete"
            state["updated_at_utc"] = utc_now()
            state.setdefault("completed_at_utc", utc_now())
            atomic_json(state_path, state)
            print(json.dumps({
                "status": "complete",
                "collection": args.collection,
                "points": info.points_count,
                "indexed_vectors": info.indexed_vectors_count,
            }, indent=2))
            return 0
    for index, shard in enumerate(manifest["shards"]):
        if index < completed:
            recorded = state["completed_shards"][index]
            if (
                recorded["vectors_sha256"] != shard["vectors_sha256"]
                or recorded["metadata_sha256"] != shard["metadata_sha256"]
            ):
                raise RuntimeError(f"completed source shard {index} checksum changed")
            continue
        vector_path = args.source / shard["vectors_file"]
        metadata_path = args.source / shard["metadata_file"]
        if file_sha256(vector_path) != shard["vectors_sha256"] or file_sha256(metadata_path) != shard["metadata_sha256"]:
            raise RuntimeError(f"source checksum failed for shard {index}")
        print(f"Uploading shard {index + 1}/{len(manifest['shards'])} ({shard['count']:,} points)...", flush=True)
        started = time.monotonic()
        qdrant.upload_points(
            collection_name=args.collection,
            points=shard_points(vector_path, metadata_path, shard["count"]),
            batch_size=args.batch_size,
            parallel=1,
            max_retries=3,
            wait=True,
        )
        elapsed = time.monotonic() - started
        state["completed_shards"].append({
            "shard": index,
            "count": shard["count"],
            "vectors_sha256": shard["vectors_sha256"],
            "metadata_sha256": shard["metadata_sha256"],
            "seconds": elapsed,
        })
        state["completed_points"] += shard["count"]
        state["updated_at_utc"] = utc_now()
        atomic_json(state_path, state)
        print(f"Completed shard {index + 1} at {shard['count'] / elapsed:.1f} points/s", flush=True)
        if args.cooldown_seconds and index + 1 < len(manifest["shards"]):
            time.sleep(args.cooldown_seconds)

    qdrant.update_collection(
        collection_name=args.collection,
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=20_000,
            max_optimization_threads=2,
        ),
    )
    state["status"] = "optimizing"
    state["updated_at_utc"] = utc_now()
    atomic_json(state_path, state)
    print("Upload complete. Qdrant is building the HNSW index in the background.", flush=True)
    return 0


def collection_status(args: argparse.Namespace) -> int:
    qdrant = client(args.url)
    info = qdrant.get_collection(args.collection)
    result = {
        "collection": args.collection,
        "status": str(info.status),
        "optimizer_status": str(info.optimizer_status),
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "segments_count": info.segments_count,
    }
    print(json.dumps(result, indent=2, default=str))
    if args.source and info.points_count == info.indexed_vectors_count:
        state_path = args.source / "qdrant-import-state.json"
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("collection") == args.collection:
                state["status"] = "complete"
                state["completed_at_utc"] = utc_now()
                state["updated_at_utc"] = utc_now()
                atomic_json(state_path, state)
    return 0


def load_query_model(source: Path) -> Any:
    # These imports are intentionally lazy. The production librarian service uses
    # ONNX/FastEmbed and must not pay PyTorch's substantial import and memory cost.
    import torch
    from sentence_transformers import SentenceTransformer
    manifest = read_manifest(source)
    if manifest["model_id"] != MODEL_ID or manifest["model_revision"] != MODEL_REVISION:
        raise RuntimeError("source model does not match the pinned query model")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    return SentenceTransformer(
        MODEL_ID,
        revision=MODEL_REVISION,
        cache_folder=str((source.parent / "models").resolve()),
        device=device,
    )


def query_vectors(model: Any, queries: List[str]) -> np.ndarray:
    vectors = model.encode(
        [QUERY_PREFIX + query for query in queries],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32, copy=False)
    if vectors.shape != (len(queries), 384) or not np.isfinite(vectors).all():
        raise RuntimeError("query embeddings are invalid")
    return vectors


def make_filter(genre: Optional[str]) -> Optional[models.Filter]:
    if not genre:
        return None
    return models.Filter(
        must=[models.FieldCondition(key="genres", match=models.MatchValue(value=genre))]
    )


def search(qdrant: QdrantClient, collection: str, vector: np.ndarray, limit: int, genre: Optional[str] = None) -> List[Dict[str, Any]]:
    started = time.monotonic()
    hits = qdrant.query_points(
        collection_name=collection,
        query=vector,
        query_filter=make_filter(genre),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    ).points
    elapsed = time.monotonic() - started
    return [
        {"rank": rank, "score": float(hit.score), **(hit.payload or {}), "search_ms": elapsed * 1000}
        for rank, hit in enumerate(hits, 1)
    ]


def print_results(query: str, results: List[Dict[str, Any]]) -> None:
    print(f"\nQuery: {query}\n")
    for item in results:
        authors = "; ".join(item.get("authors") or []) or "Unknown author"
        genres = ", ".join(item.get("genres") or []) or "unclassified"
        print(f"{item['rank']:>2}. {item.get('title')} — {authors}")
        print(f"    score={item['score']:.4f}  genres={genres}  work={item.get('work_key')}")
    if results:
        print(f"\nQdrant search latency: {results[0]['search_ms']:.1f} ms")


def search_command(args: argparse.Namespace) -> int:
    vector = query_vectors(load_query_model(args.source), [args.query])[0]
    results = search(client(args.url), args.collection, vector, args.limit, args.genre)
    print_results(args.query, results)
    return 0


def render_evaluation(report: Dict[str, Any]) -> str:
    lines = [
        "# Full-catalog Qdrant retrieval evaluation", "",
        f"Generated: {report['generated_at_utc']}", "",
        f"Collection: `{report['collection']}`", "",
        f"Queries: {len(report['queries'])}", "",
        f"Mean Qdrant latency: {report['mean_search_ms']:.1f} ms", "",
    ]
    for item in report["queries"]:
        lines.extend([
            f"## {item['query']}", "",
            f"Expected genre matches@50: {item['expected_genre_matches_at_50'] if item['expected_genre_matches_at_50'] is not None else 'n/a'}", "",
            f"Excluded genre matches@50: {item['excluded_genre_matches_at_50'] if item['excluded_genre_matches_at_50'] is not None else 'n/a'}", "",
            f"Excluded author matches@50: {item['excluded_author_matches_at_50'] if item['excluded_author_matches_at_50'] is not None else 'n/a'}", "",
            "| # | Score | Title | Author | Genres |", "|---:|---:|---|---|---|",
        ])
        for result in item["results"][:10]:
            title = str(result.get("title") or "").replace("|", "\\|")
            authors = "; ".join(result.get("authors") or []).replace("|", "\\|")
            genres = "; ".join(result.get("genres") or []).replace("|", "\\|")
            lines.append(f"| {result['rank']} | {result['score']:.4f} | {title} | {authors} | {genres} |")
        lines.append("")
    return "\n".join(lines)


def evaluate_command(args: argparse.Namespace) -> int:
    qdrant = client(args.url)
    report_queries = []
    latencies = []
    vectors = query_vectors(load_query_model(args.source), [item["query"] for item in QUERIES])
    for specification, vector in zip(QUERIES, vectors):
        results = search(qdrant, args.collection, vector, 50)
        latencies.append(results[0]["search_ms"] if results else 0.0)
        expected = specification.get("genre")
        excluded_genre = specification.get("exclude_genre")
        excluded_author = specification.get("exclude_author")
        report_queries.append({
            **specification,
            "expected_genre_matches_at_50": None if not expected else sum(expected in (r.get("genres") or []) for r in results),
            "excluded_genre_matches_at_50": None if not excluded_genre else sum(excluded_genre in (r.get("genres") or []) for r in results),
            "excluded_author_matches_at_50": None if not excluded_author else sum(
                excluded_author in author.lower() for r in results for author in (r.get("authors") or [])
            ),
            "results": results,
        })
        print(f"Evaluated: {specification['query']}", flush=True)
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "collection": args.collection,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "query_prefix": QUERY_PREFIX},
        "mean_search_ms": sum(latencies) / len(latencies),
        "queries": report_queries,
    }
    atomic_json(args.output / "qdrant-retrieval-evaluation.json", report)
    markdown = render_evaluation(report).encode("utf-8")
    path = args.output / "qdrant-retrieval-evaluation.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(markdown)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    print(json.dumps({"queries": len(report_queries), "mean_search_ms": report["mean_search_ms"], "output": str(args.output.resolve())}, indent=2))
    return 0


def snapshot_command(args: argparse.Namespace) -> int:
    result = client(args.url).create_snapshot(args.collection, wait=True)
    print(json.dumps({"collection": args.collection, "snapshot": result.name, "size": result.size}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:6333")
    parser.add_argument("--collection", default=COLLECTION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    importer = subparsers.add_parser("import")
    importer.add_argument("--source", type=Path, required=True)
    importer.add_argument("--batch-size", type=int, default=128)
    importer.add_argument("--cooldown-seconds", type=float, default=5.0)
    importer.set_defaults(function=import_catalog)

    status = subparsers.add_parser("status")
    status.add_argument("--source", type=Path)
    status.set_defaults(function=collection_status)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--source", type=Path, required=True)
    search_parser.add_argument("--limit", type=int, default=50)
    search_parser.add_argument("--genre")
    search_parser.set_defaults(function=search_command)

    evaluator = subparsers.add_parser("evaluate")
    evaluator.add_argument("--source", type=Path, required=True)
    evaluator.add_argument("--output", type=Path, required=True)
    evaluator.set_defaults(function=evaluate_command)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.set_defaults(function=snapshot_command)

    args = parser.parse_args()
    if getattr(args, "batch_size", 1) < 1 or getattr(args, "cooldown_seconds", 0) < 0:
        parser.error("batch size must be positive and cooldown must be nonnegative")
    if getattr(args, "limit", 1) < 1:
        parser.error("limit must be positive")
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
