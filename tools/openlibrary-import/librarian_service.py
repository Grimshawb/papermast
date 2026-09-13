#!/usr/bin/env python3
"""Private HTTP service for PaperMast semantic retrieval and Gemini reranking."""

from __future__ import annotations

import os
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import psutil
from fastapi import FastAPI, HTTPException
from fastembed import TextEmbedding
from google import genai
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models

from embedding_contract import (
    FASTEMBED_MODEL_REVISION,
    MODEL_ID,
    MODEL_REVISION,
    QUERY_PREFIX,
    RUNTIME_COLLECTION,
)
from gemini_librarian import (
    GEMINI_MODEL, diversify_candidates, extract_constraints, load_api_key,
    local_fallback_rerank, rerank,
)


LOGGER = logging.getLogger(__name__)


class Settings:
    def __init__(self) -> None:
        self.qdrant_url = os.getenv("LIBRARIAN_QDRANT_URL", "http://127.0.0.1:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
        self.collection = os.getenv("LIBRARIAN_QDRANT_COLLECTION", RUNTIME_COLLECTION)
        self.gemini_model = os.getenv("LIBRARIAN_GEMINI_MODEL", GEMINI_MODEL)
        self.gemini_env_file = Path(os.getenv("LIBRARIAN_GEMINI_ENV_FILE", ".data/openlibrary/gemini.env"))
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or None
        self.model_cache = Path(os.getenv("LIBRARIAN_MODEL_CACHE", ".data/openlibrary/fastembed-models"))
        self.model_local_only = os.getenv("LIBRARIAN_MODEL_LOCAL_ONLY", "false").casefold() == "true"
        self.expected_points = int(os.getenv("LIBRARIAN_EXPECTED_POINTS", "676258"))
        self.max_concurrency = int(os.getenv("LIBRARIAN_MAX_CONCURRENCY", "2"))


class RecommendRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    result_count: int = Field(default=5, ge=3, le=5)


class BookRecommendation(BaseModel):
    work_key: str
    title: str
    authors: List[str]
    genres: List[str]
    description: str
    edition_key: Optional[str]
    cover_ids: List[int]
    isbn_10: List[str]
    isbn_13: List[str]
    publication_date: Optional[str]
    page_count: Optional[int]
    reason: str


class RecommendResponse(BaseModel):
    recommendations: List[BookRecommendation]
    elapsed_ms: float


class LibrarianEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
        self.embedder = TextEmbedding(
            model_name=MODEL_ID,
            cache_dir=str(settings.model_cache),
            threads=2,
            revision=FASTEMBED_MODEL_REVISION,
            local_files_only=settings.model_local_only,
        )
        api_key = settings.gemini_api_key or load_api_key(settings.gemini_env_file)
        self.gemini = genai.Client(api_key=api_key)
        self.slots = threading.BoundedSemaphore(settings.max_concurrency)

    def ready(self) -> Dict[str, Any]:
        info = self.qdrant.get_collection(self.settings.collection)
        ready = (
            info.points_count == self.settings.expected_points
            and info.indexed_vectors_count == self.settings.expected_points
            and str(info.status).casefold().endswith("green")
        )
        return {
            "ready": ready,
            "collection": self.settings.collection,
            "points": info.points_count,
            "indexed_vectors": info.indexed_vectors_count,
            "model": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "fastembed_model_revision": FASTEMBED_MODEL_REVISION,
            "rss_mib": round(psutil.Process().memory_info().rss / 1024 / 1024, 1),
        }

    def query_vector(self, text: str) -> np.ndarray:
        vector = np.asarray(next(self.embedder.embed([QUERY_PREFIX + text])), dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if vector.shape != (384,) or not norm:
            raise RuntimeError("query embedding has an invalid shape or norm")
        return vector / norm

    def author_reference_vector(self, authors: tuple[str, ...]) -> Optional[np.ndarray]:
        vectors: List[Any] = []
        for author in authors:
            records, _ = self.qdrant.scroll(
                collection_name=self.settings.collection,
                scroll_filter=models.Filter(must=[
                    models.FieldCondition(key="authors_normalized", match=models.MatchValue(value=author)),
                    models.FieldCondition(key="retrieval_quality", match=models.MatchValue(value="rich")),
                ]),
                limit=30,
                with_payload=False,
                with_vectors=True,
            )
            vectors.extend(point.vector for point in records if point.vector)
        if not vectors:
            return None
        vector = np.asarray(vectors, dtype=np.float32).mean(axis=0)
        norm = float(np.linalg.norm(vector))
        return None if not norm else vector / norm

    def resolve_requested_authors(self, candidates: tuple[str, ...]) -> tuple[str, ...]:
        """Keep only possible name spans that exactly exist in the catalog."""
        if not candidates:
            return ()
        candidate_set = set(candidates)
        records, _ = self.qdrant.scroll(
            collection_name=self.settings.collection,
            scroll_filter=models.Filter(should=[
                models.FieldCondition(
                    key="authors_normalized", match=models.MatchValue(value=candidate),
                )
                for candidate in candidates
            ]),
            limit=min(32, len(candidates) * 4),
            with_payload=["authors_normalized"],
            with_vectors=False,
        )
        resolved = {
            author
            for record in records
            for author in (record.payload or {}).get("authors_normalized", [])
            if author in candidate_set
        }
        return tuple(sorted(resolved))

    def candidates(self, query: str, retrieve_count: int = 200, candidate_count: int = 40) -> List[Dict[str, Any]]:
        constraints = extract_constraints(query)
        vector = self.query_vector(constraints.retrieval_query)
        reference = self.author_reference_vector(constraints.excluded_authors)
        if reference is not None:
            vector = reference
        requested_authors = self.resolve_requested_authors(
            constraints.requested_author_candidates
        )
        author_filter = None
        if requested_authors:
            author_filter = models.Filter(should=[
                models.FieldCondition(
                    key="authors_normalized", match=models.MatchValue(value=author),
                )
                for author in requested_authors
            ])
        hits = self.qdrant.query_points(
            collection_name=self.settings.collection,
            query=vector,
            query_filter=author_filter,
            limit=retrieve_count,
            with_payload=True,
            with_vectors=False,
        ).points
        records = []
        seen = set()
        for rank, hit in enumerate(hits, 1):
            payload = hit.payload or {}
            identity = (
                " ".join(str(payload.get("title") or "").casefold().split()),
                tuple(sorted(payload.get("authors_normalized") or [])),
            )
            if not identity[0] or identity in seen:
                continue
            seen.add(identity)
            records.append({
                "work_key": payload["work_key"],
                "title": payload["title"],
                "authors": payload.get("authors") or [],
                "genres": payload.get("genres") or [],
                "description": payload.get("description") or "",
                "retrieval_quality": payload.get("retrieval_quality"),
                "metadata_quality_score": payload.get("metadata_quality_score", 0),
                "representative_edition_key": payload.get("representative_edition_key"),
                "cover_ids": payload.get("covers") or [],
                "isbn_10": payload.get("isbn_10") or [],
                "isbn_13": payload.get("isbn_13") or [],
                "publication_date": payload.get("publication_date"),
                "page_count": payload.get("page_count"),
                "retrieval_rank": rank,
                "similarity_score": float(hit.score),
            })
        return diversify_candidates(records, constraints, candidate_count)

    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        if not self.slots.acquire(timeout=1):
            raise RuntimeError("librarian is at its concurrency limit")
        started = time.monotonic()
        try:
            candidates = self.candidates(request.query)
            try:
                result = rerank(
                    self.gemini, request.query, candidates, request.result_count,
                    self.settings.gemini_model,
                )
            except Exception:
                # Retrieval is still useful when Gemini is empty, blocked,
                # rate-limited, or temporarily unavailable. Keep provider
                # failures from turning a healthy local catalog into a 503.
                LOGGER.warning(
                    "Gemini reranking failed; returning diversified local retrieval",
                    exc_info=True,
                )
                result = local_fallback_rerank(candidates, request.result_count)
            output = []
            for item in result["recommendations"]:
                output.append(BookRecommendation(
                    work_key=item["work_key"], title=item["title"], authors=item["authors"],
                    genres=item["genres"], description=item["description"],
                    edition_key=item.get("representative_edition_key"),
                    cover_ids=item.get("cover_ids") or [], isbn_10=item.get("isbn_10") or [],
                    isbn_13=item.get("isbn_13") or [], publication_date=item.get("publication_date"),
                    page_count=item.get("page_count"), reason=item["reason"],
                ))
            return RecommendResponse(
                recommendations=output,
                elapsed_ms=round((time.monotonic() - started) * 1000, 1),
            )
        finally:
            self.slots.release()


engine: Optional[LibrarianEngine] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global engine
    engine = LibrarianEngine(Settings())
    yield
    engine = None


app = FastAPI(title="PaperMast Librarian", version="0.1.0", lifespan=lifespan)


@app.get("/health/live")
def live() -> Dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def ready() -> Dict[str, Any]:
    if engine is None:
        raise HTTPException(status_code=503, detail="service is starting")
    result = engine.ready()
    if not result["ready"]:
        raise HTTPException(status_code=503, detail=result)
    return result


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    if engine is None:
        raise HTTPException(status_code=503, detail="service is starting")
    try:
        return engine.recommend(request)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
