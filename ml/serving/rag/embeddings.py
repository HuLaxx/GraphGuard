"""
Embedding providers for RAG.
"""

from __future__ import annotations

import hashlib
import math
import random
from typing import List


class EmbeddingProvider:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    @property
    def dimension(self) -> int:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, lightweight embeddings for tests and offline fallback."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            vec = [rng.uniform(-1, 1) for _ in range(self._dimension)]
            embeddings.append(_normalize(vec))
        return embeddings


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """SentenceTransformers embeddings."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in vectors]


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]
