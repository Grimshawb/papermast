"""Lightweight shared identity for offline and runtime embedding components."""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any, Dict, List


MODEL_ID = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
# FastEmbed uses Qdrant's quantized ONNX conversion of the model above. Pin its
# separate repository revision so container rebuilds cannot silently change it.
FASTEMBED_MODEL_REVISION = "52398278842ec682c6f32300af41344b1c0b0bb2"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RUNTIME_COLLECTION = "papermast_fiction_bge_runtime_v1"

QUERIES: List[Dict[str, Any]] = [
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
