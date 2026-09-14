#!/usr/bin/env python3
"""Create and evaluate a fully local BGE retrieval pilot."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import duckdb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer


MODEL_ID = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
PILOT_SCHEMA_VERSION = 1

QUERIES = [
    {"query": "A gothic horror novel set in an old house", "genre": "horror"},
    {"query": "A sweeping space opera with interplanetary politics", "genre": "science-fiction"},
    {"query": "A cozy mystery in a small town", "genre": "mystery"},
    {"query": "A historical romance with wit and yearning", "genre": "romance"},
    {"query": "Something funny and weird", "genre": None},
    {"query": "Something creepy and historical, but not outright horror", "genre": "historical-fiction", "exclude_genre": "horror"},
    {"query": "Science fiction without a lot of complicated science", "genre": "science-fiction"},
    {"query": "A fast thriller about a dangerous conspiracy", "genre": "thriller"},
    {"query": "Epic fantasy with political intrigue and dangerous magic", "genre": "fantasy"},
    {"query": "Quiet, melancholy literary fiction about family", "genre": "literary-fiction"},
    {"query": "A young adult adventure about friendship", "genre": "young-adult"},
    {"query": "A paranormal romance", "genre": "romance"},
    {"query": "Psychological suspense with an unreliable narrator", "genre": "thriller"},
    {"query": "A story about time travel and changing history", "genre": "science-fiction"},
    {"query": "A family saga set during wartime", "genre": "historical-fiction"},
    {"query": "Something like Stephen King without Stephen King", "genre": "horror", "exclude_author": "stephen king"},
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_pilot(connection: duckdb.DuckDBPyConnection, size: int, seed: int) -> int:
    if not connection.execute("SELECT count(*) FROM duckdb_tables() WHERE table_name='retrieval_documents'").fetchone()[0]:
        raise RuntimeError("retrieval_documents does not exist; run prepare-documents first")
    connection.execute("DROP TABLE IF EXISTS embedding_pilot_staging")
    connection.execute("DROP TABLE IF EXISTS pilot_balanced")
    connection.execute("""
        CREATE TEMP TABLE pilot_balanced AS
        WITH candidates AS (
            SELECT r.*,
                   COALESCE(list_extract(r.genres, 1), 'general') || ':' || r.retrieval_quality AS stratum,
                   row_number() OVER (
                       PARTITION BY COALESCE(list_extract(r.genres, 1), 'general'), r.retrieval_quality
                       ORDER BY hash(r.work_key || ?)
                   ) AS stratum_rank
            FROM retrieval_documents r
        )
        SELECT * EXCLUDE (stratum_rank)
        FROM candidates
        WHERE stratum_rank <= 800
    """, [str(seed)])
    balanced = connection.execute("SELECT count(*) FROM pilot_balanced").fetchone()[0]
    if balanced > size:
        connection.execute("DELETE FROM pilot_balanced WHERE work_key NOT IN (SELECT work_key FROM pilot_balanced ORDER BY hash(work_key || ?) LIMIT ?)", [str(seed), size])
        balanced = size
    remaining = size - balanced
    connection.execute("""
        CREATE TABLE embedding_pilot_staging AS
        WITH selected AS (
            SELECT * FROM pilot_balanced
            UNION ALL
            (SELECT r.*,
                    COALESCE(list_extract(r.genres, 1), 'general') || ':' || r.retrieval_quality AS stratum
             FROM retrieval_documents r
             LEFT JOIN pilot_balanced p USING (work_key)
             WHERE p.work_key IS NULL
             ORDER BY hash(r.work_key || ?)
             LIMIT ?)
        )
        SELECT row_number() OVER (ORDER BY hash(work_key || ?), work_key) - 1 AS pilot_index,
               selected.*
        FROM selected
    """, [str(seed), remaining, str(seed)])
    actual = connection.execute("SELECT count(*) FROM embedding_pilot_staging").fetchone()[0]
    if actual != size:
        raise RuntimeError(f"pilot selection produced {actual} rows, expected {size}")
    connection.execute("DROP TABLE IF EXISTS embedding_pilot")
    connection.execute("ALTER TABLE embedding_pilot_staging RENAME TO embedding_pilot")
    return actual


def load_pilot(connection: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    result = connection.execute("""
        SELECT pilot_index, work_key, document_hash, embedding_text, title,
               author_names, genres, retrieval_quality, stratum
        FROM embedding_pilot ORDER BY pilot_index
    """)
    columns = [item[0] for item in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def render_report(report: Dict[str, Any]) -> str:
    lines = [
        "# BGE local retrieval pilot", "",
        f"Generated: {report['generated_at_utc']}", "",
        f"Model: `{report['model']['id']}`", "",
        f"Revision: `{report['model']['revision']}`", "",
        f"Device: `{report['runtime']['device']}`", "",
        f"Pilot books: {report['pilot']['count']:,}", "",
        f"Embedding runtime: {report['runtime']['embedding_seconds']:.1f} seconds", "",
        "## Automated summary", "",
        f"Mean expected-genre precision@10: {report['evaluation']['mean_genre_precision_at_10']:.1%}", "",
        f"Mean subject-only rate@10: {report['evaluation']['mean_subject_only_rate_at_10']:.1%}", "",
        "## Queries", "",
    ]
    for item in report["evaluation"]["queries"]:
        lines.extend([
            f"### {item['query']}", "",
            f"Expected genre precision@10: {item['genre_precision_at_10'] if item['genre_precision_at_10'] is not None else 'n/a'}", "",
            f"Expected genre matches@50: {item['expected_genre_matches_at_50'] if item['expected_genre_matches_at_50'] is not None else 'n/a'}", "",
            f"Excluded genre matches@50: {item['excluded_genre_matches_at_50'] if item['excluded_genre_matches_at_50'] is not None else 'n/a'}", "",
            f"Excluded author matches@50: {item['excluded_author_matches_at_50'] if item['excluded_author_matches_at_50'] is not None else 'n/a'}", "",
            "| # | Score | Title | Author | Genres | Quality |", "|---:|---:|---|---|---|---|",
        ])
        for rank, result in enumerate(item["results"][:10], 1):
            title = result["title"].replace("|", "\\|")
            author = "; ".join(result["authors"]).replace("|", "\\|")
            genres = "; ".join(result["genres"]).replace("|", "\\|")
            lines.append(f"| {rank} | {result['score']:.4f} | {title} | {author} | {genres} | {result['quality']} |")
        lines.append("")
    lines.extend([
        "## Interpretation limits", "",
        "- Genre precision uses incomplete Open Library-derived genre labels; it is a diagnostic, not ground truth.",
        "- The LLM stage is intentionally absent. These are raw local-vector candidates.",
        "- The pilot is stratified rather than a miniature copy of production prevalence.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=25_000)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    if args.size < 1 or args.batch_size < 1:
        parser.error("size and batch size must be positive")

    args.output.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(args.database))
    try:
        count = build_pilot(connection, args.size, args.seed)
        connection.execute("CHECKPOINT")
        records = load_pilot(connection)
    finally:
        connection.close()

    vector_path = args.output / "bge-small-en-v1.5-vectors.npy"
    metadata_path = args.output / "bge-small-en-v1.5-metadata.jsonl"
    vectors = None
    reused_vectors = False
    if vector_path.is_file() and metadata_path.is_file():
        existing_metadata = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines()]
        expected_identity = [(record["work_key"], record["document_hash"]) for record in records]
        existing_identity = [(record["work_key"], record["document_hash"]) for record in existing_metadata]
        if existing_identity == expected_identity:
            candidate_vectors = np.load(vector_path, allow_pickle=False)
            if candidate_vectors.shape == (count, 384) and np.isfinite(candidate_vectors).all():
                vectors = candidate_vectors.astype(np.float32, copy=False)
                reused_vectors = True

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = SentenceTransformer(
        MODEL_ID,
        revision=MODEL_REVISION,
        cache_folder=str((args.output.parent / "models").resolve()),
        device=device,
    )
    embedding_seconds = 0.0
    if vectors is None:
        started = time.monotonic()
        vectors = model.encode(
            [record["embedding_text"] for record in records],
            batch_size=args.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32, copy=False)
        embedding_seconds = time.monotonic() - started
        if vectors.shape != (count, 384) or not np.isfinite(vectors).all():
            raise RuntimeError(f"invalid vectors: shape={vectors.shape}, finite={np.isfinite(vectors).all()}")
        with tempfile.NamedTemporaryFile(prefix=f".{vector_path.name}.", dir=args.output, delete=False) as handle:
            temporary_vector_path = Path(handle.name)
            np.save(handle, vectors, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_vector_path, vector_path)
        metadata = b"".join(
            (json.dumps({key: value for key, value in record.items() if key != "embedding_text"}, ensure_ascii=False, default=str) + "\n").encode("utf-8")
            for record in records
        )
        atomic_write(metadata_path, metadata)

    query_vectors = model.encode(
        [QUERY_PREFIX + item["query"] for item in QUERIES],
        batch_size=len(QUERIES),
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32, copy=False)
    if query_vectors.shape != (len(QUERIES), 384) or not np.isfinite(query_vectors).all():
        raise RuntimeError(f"invalid query vectors: shape={query_vectors.shape}, finite={np.isfinite(query_vectors).all()}")
    # Avoid the Accelerate/BLAS matmul path, which emits spurious overflow
    # warnings with NumPy 2.0 and Apple BLAS on this Apple-silicon setup.
    scores = np.einsum("qd,nd->qn", query_vectors, vectors, optimize=False)
    if not np.isfinite(scores).all():
        raise RuntimeError("similarity evaluation produced non-finite scores")
    evaluations = []
    genre_precisions = []
    subject_only_rates = []
    for query_index, specification in enumerate(QUERIES):
        top_indices = np.argpartition(scores[query_index], -50)[-50:]
        top_indices = top_indices[np.argsort(scores[query_index, top_indices])[::-1]]
        results = []
        for index in top_indices:
            record = records[int(index)]
            results.append({
                "work_key": record["work_key"], "score": float(scores[query_index, index]),
                "title": record["title"], "authors": record["author_names"],
                "genres": record["genres"], "quality": record["retrieval_quality"],
            })
        expected = specification.get("genre")
        top_ten = results[:10]
        precision = None if expected is None else sum(expected in result["genres"] for result in top_ten) / len(top_ten)
        if precision is not None:
            genre_precisions.append(precision)
        subject_only_rate = sum(result["quality"] == "subject_only" for result in top_ten) / len(top_ten)
        subject_only_rates.append(subject_only_rate)
        exclude_genre = specification.get("exclude_genre")
        exclude_author = specification.get("exclude_author")
        evaluations.append({
            **specification,
            "genre_precision_at_10": precision,
            "expected_genre_matches_at_50": None if expected is None else sum(expected in result["genres"] for result in results),
            "excluded_genre_matches_at_50": None if exclude_genre is None else sum(exclude_genre in result["genres"] for result in results),
            "excluded_author_matches_at_50": None if exclude_author is None else sum(
                any(exclude_author in author.lower() for author in result["authors"]) for result in results
            ),
            "subject_only_rate_at_10": subject_only_rate,
            "results": results,
        })

    report = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "dimensions": 384, "query_prefix": QUERY_PREFIX},
        "pilot": {"count": count, "seed": args.seed, "selection": "up to 800 per primary-genre/retrieval-quality stratum, then deterministic fill"},
        "runtime": {
            "device": device, "batch_size": args.batch_size,
            "embedding_seconds": embedding_seconds,
            "documents_per_second": None if reused_vectors else count / embedding_seconds,
            "reused_vectors": reused_vectors,
        },
        "artifacts": {
            "vectors": str(vector_path.resolve()), "vectors_sha256": file_sha256(vector_path),
            "metadata": str(metadata_path.resolve()), "metadata_sha256": file_sha256(metadata_path),
        },
        "evaluation": {
            "mean_genre_precision_at_10": sum(genre_precisions) / len(genre_precisions),
            "mean_subject_only_rate_at_10": sum(subject_only_rates) / len(subject_only_rates),
            "queries": evaluations,
        },
    }
    atomic_write(args.output / "bge-pilot-report.json", (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    atomic_write(args.output / "bge-pilot-report.md", render_report(report).encode("utf-8"))
    print(json.dumps({"pilot_count": count, "runtime": report["runtime"], "evaluation": {key: value for key, value in report["evaluation"].items() if key != "queries"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
