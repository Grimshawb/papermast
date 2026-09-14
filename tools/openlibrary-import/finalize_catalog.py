#!/usr/bin/env python3
"""Export the accepted fiction catalog as a compact, versioned runtime artifact."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import duckdb
from qdrant_client import QdrantClient

from embedding_contract import MODEL_ID, MODEL_REVISION, file_sha256, utc_now


SCHEMA_VERSION = 1
CATALOG_VERSION = 1
DIMENSIONS = 384


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
        Path(temporary).unlink(missing_ok=True)
        raise


def load_embedding_identity(path: Path) -> Dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "dimensions": DIMENSIONS,
        "normalized": True,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise RuntimeError(f"embedding manifest {key} does not match: {manifest.get(key)!r}")
    if manifest.get("status") != "complete":
        raise RuntimeError("embedding manifest is not complete")
    if sum(item.get("count", 0) for item in manifest.get("shards", [])) != manifest.get("target_count"):
        raise RuntimeError("embedding manifest counts do not match")
    return manifest


def export_catalog(database: Path, destination: Path) -> Dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".parquet", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    connection = duckdb.connect(str(database), read_only=True)
    try:
        connection.execute("""
            COPY (
                SELECT
                    r.work_key,
                    r.title,
                    r.author_names AS authors,
                    r.genres,
                    r.cleaned_subjects AS subjects,
                    r.cleaned_description AS description,
                    r.representative_edition_key AS edition_key,
                    CAST(CAST(r.representative_covers_json AS JSON) AS BIGINT[]) AS cover_ids,
                    CAST(CAST(r.representative_isbn_10_json AS JSON) AS VARCHAR[]) AS isbn_10,
                    CAST(CAST(r.representative_isbn_13_json AS JSON) AS VARCHAR[]) AS isbn_13,
                    COALESCE(f.representative_publish_date, f.first_publish_date) AS publication_date,
                    f.representative_number_of_pages AS page_count,
                    f.edition_count,
                    f.english_edition_count,
                    r.retrieval_quality,
                    r.metadata_quality_score,
                    r.document_version,
                    r.document_hash
                FROM retrieval_documents r
                INNER JOIN fiction_catalog f USING (work_key)
                ORDER BY r.work_key
            ) TO ? (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
        """, [str(temporary)])
        source = connection.execute("""
            SELECT count(*) AS count,
                   count(DISTINCT work_key) AS distinct_work_keys,
                   count(*) FILTER (WHERE title IS NULL OR trim(title) = '') AS missing_titles,
                   count(*) FILTER (WHERE len(author_names) = 0) AS missing_authors,
                   bit_xor(hash(work_key || ':' || document_hash)) AS identity_xor,
                   min(work_key) AS first_work_key,
                   max(work_key) AS last_work_key,
                   min(document_version) AS min_document_version,
                   max(document_version) AS max_document_version
            FROM retrieval_documents
        """).fetchone()
        columns = [item[0] for item in connection.description]
        source_stats = dict(zip(columns, source))
    finally:
        connection.close()
    validation = duckdb.connect()
    try:
        exported_count, distinct_keys = validation.execute(
            "SELECT count(*), count(DISTINCT work_key) FROM read_parquet(?)", [str(temporary)]
        ).fetchone()
        schema = [
            {"name": row[0], "type": row[1]}
            for row in validation.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(temporary)]).fetchall()
        ]
    finally:
        validation.close()
    expected = source_stats["count"]
    if (
        exported_count != expected
        or distinct_keys != expected
        or source_stats["distinct_work_keys"] != expected
        or source_stats["missing_titles"]
        or source_stats["missing_authors"]
        or source_stats["min_document_version"] != source_stats["max_document_version"]
    ):
        temporary.unlink(missing_ok=True)
        raise RuntimeError("catalog export validation failed")
    os.replace(temporary, destination)
    return {"source": source_stats, "schema": schema}


def qdrant_identity(url: str, collection: str, expected_count: int) -> Dict[str, Any]:
    client = QdrantClient(url=url)
    info = client.get_collection(collection)
    vectors = info.config.params.vectors
    if info.points_count != expected_count or info.indexed_vectors_count != expected_count:
        raise RuntimeError(
            f"Qdrant counts do not match catalog: points={info.points_count}, "
            f"indexed={info.indexed_vectors_count}, expected={expected_count}"
        )
    snapshots = sorted(client.list_snapshots(collection), key=lambda item: item.creation_time)
    if not snapshots:
        raise RuntimeError("Qdrant collection has no snapshot")
    latest = snapshots[-1]
    return {
        "url": url,
        "collection": collection,
        "status": getattr(info.status, "value", str(info.status)),
        "points_count": info.points_count,
        "indexed_vectors_count": info.indexed_vectors_count,
        "dimensions": vectors.size,
        "distance": getattr(vectors.distance, "value", str(vectors.distance)).casefold(),
        "snapshot": {
            "name": latest.name,
            "bytes": latest.size,
            "created_at": (
                latest.creation_time.isoformat()
                if hasattr(latest.creation_time, "isoformat")
                else str(latest.creation_time)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path(".data/openlibrary/catalog.duckdb"))
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=Path(".data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1/manifest.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path(".data/openlibrary/production/catalog-v1")
    )
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    parser.add_argument("--collection", default="papermast_fiction_bge_v1")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error(f"database does not exist: {args.database}")
    if not args.embeddings.is_file():
        parser.error(f"embedding manifest does not exist: {args.embeddings}")
    embedding = load_embedding_identity(args.embeddings)
    args.output.mkdir(parents=True, exist_ok=True)
    parquet = args.output / "fiction-catalog.parquet"
    exported = export_catalog(args.database, parquet)
    source = exported["source"]
    if source["count"] != embedding["target_count"]:
        raise RuntimeError(
            f"catalog rows ({source['count']}) do not match embeddings ({embedding['target_count']})"
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "status": "complete",
        "generated_at_utc": utc_now(),
        "row_count": source["count"],
        "first_work_key": source["first_work_key"],
        "last_work_key": source["last_work_key"],
        "source_identity_xor": str(source["identity_xor"]),
        "document_version": source["min_document_version"],
        "embedding": {
            "model_id": embedding["model_id"],
            "model_revision": embedding["model_revision"],
            "dimensions": embedding["dimensions"],
            "distance": embedding["distance"],
            "source_identity_xor": embedding["source_identity_xor"],
            "count": embedding["target_count"],
        },
        "artifact": {
            "file": parquet.name,
            "bytes": parquet.stat().st_size,
            "sha256": file_sha256(parquet),
            "format": "parquet",
            "compression": "zstd",
        },
        "schema": exported["schema"],
    }
    if manifest["source_identity_xor"] != manifest["embedding"]["source_identity_xor"]:
        raise RuntimeError("catalog identity does not match the embedding corpus")
    manifest["qdrant"] = qdrant_identity(
        args.qdrant_url, args.collection, manifest["row_count"]
    )
    if (
        manifest["qdrant"]["dimensions"] != manifest["embedding"]["dimensions"]
        or manifest["qdrant"]["distance"] != manifest["embedding"]["distance"]
    ):
        raise RuntimeError("Qdrant vector configuration does not match embeddings")
    atomic_json(args.output / "manifest.json", manifest)
    print(json.dumps({
        "rows": manifest["row_count"],
        "bytes": manifest["artifact"]["bytes"],
        "sha256": manifest["artifact"]["sha256"],
        "output": str(args.output.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
