"""Qdrant client and local query embeddings, shared by catalog sync and semantic ranking."""

import logging
import os
import threading
import time
from functools import lru_cache

import numpy as np
from qdrant_client import QdrantClient  # Imported eagerly: a first import inside two threads at once fails.

from .config import settings

logger = logging.getLogger(__name__)
MODEL_NAME = "all-MiniLM-L6-v2"
DIMENSIONS = 256
_down_until = 0.0
_ready = threading.Event()
_warming = threading.Lock()


@lru_cache(maxsize=1)
def qdrant():
    if not settings.qdrant_url:
        raise RuntimeError("QDRANT_VECTOR_DB_URL is not configured")
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=15,
                        check_compatibility=False)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer  # pylint: disable=import-outside-toplevel

    return SentenceTransformer(MODEL_NAME, local_files_only=os.getenv("ECOS_MODEL_LOCAL_ONLY", "true") == "true")


def embed(texts: list[str]) -> np.ndarray:
    """Normalised vectors truncated to the 256 dimensions the catalog was indexed with."""
    vectors = _model().encode(texts, batch_size=64, normalize_embeddings=True, convert_to_numpy=True,
                              show_progress_bar=False).astype(np.float32)[:, :DIMENSIONS]
    return vectors / np.clip(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12, None)


@lru_cache(maxsize=512)
def embed_query(text: str) -> list[float]:
    """Repeated searches (reruns, paging, other users) skip the model entirely."""
    return embed([text])[0].tolist()


def ready() -> bool:
    """True once the model is loaded. Requests never wait for it: until then they rank without semantics."""
    return _ready.is_set()


def _warm_up() -> None:
    try:
        embed_query("warm up")
        qdrant().get_collections()
        _ready.set()
    except Exception as error:  # Optional feature: stay on goal-based ranking and retry later.
        logger.warning("Semantic ranking is not available yet: %s", error)
        cool_down(60)
    finally:
        _warming.release()


def start_warm_up() -> None:
    """Load the model in the background (idempotent), so the first user request is as fast as any other."""
    if not settings.semantic or ready() or cooling_down() or not _warming.acquire(blocking=False):
        return
    threading.Thread(target=_warm_up, daemon=True, name="semantic-warm-up").start()


def cooling_down() -> bool:
    return time.monotonic() < _down_until


def cool_down(seconds: float = 60.0) -> None:
    """Skip semantic calls for a while after a failure so a dead Qdrant never slows every request."""
    global _down_until  # pylint: disable=global-statement
    _down_until = time.monotonic() + seconds
