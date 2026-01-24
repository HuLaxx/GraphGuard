"""
Vector store implementations for RAG.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


@dataclass
class RagChunk:
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: List[float]


@dataclass
class RagMatch:
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float


class VectorStore:
    def upsert(self, index_name: str, chunks: Iterable[RagChunk]) -> int:
        raise NotImplementedError

    def query(self, index_name: str, embedding: List[float], top_k: int, score_threshold: float) -> List[RagMatch]:
        raise NotImplementedError

    def list_indexes(self) -> List[str]:
        raise NotImplementedError


class SimpleVectorStore(VectorStore):
    """Local numpy-based vector store for free local usage."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def upsert(self, index_name: str, chunks: Iterable[RagChunk]) -> int:
        index = self._load_index(index_name)
        new_chunks = list(chunks)
        if not new_chunks:
            return 0

        vectors = np.array([c.embedding for c in new_chunks], dtype=np.float32)
        texts = [c.text for c in new_chunks]
        metas = [c.metadata for c in new_chunks]
        ids = [c.id for c in new_chunks]

        if index["vectors"].size == 0:
            index["vectors"] = vectors
        else:
            index["vectors"] = np.vstack([index["vectors"], vectors])

        index["texts"].extend(texts)
        index["metas"].extend(metas)
        index["ids"].extend(ids)

        self._persist_index(index_name, index)
        return len(new_chunks)

    def query(self, index_name: str, embedding: List[float], top_k: int, score_threshold: float) -> List[RagMatch]:
        index = self._load_index(index_name)
        if index["vectors"].size == 0:
            return []

        query_vec = np.array(embedding, dtype=np.float32)
        query_vec = _normalize_np(query_vec)
        vectors = index["vectors"]
        vectors = _normalize_matrix(vectors)
        scores = vectors @ query_vec

        top_indices = np.argsort(scores)[::-1][:top_k]
        matches: List[RagMatch] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < score_threshold:
                continue
            matches.append(
                RagMatch(
                    id=index["ids"][idx],
                    text=index["texts"][idx],
                    metadata=index["metas"][idx],
                    score=score,
                )
            )
        return matches

    def list_indexes(self) -> List[str]:
        return sorted([p.name for p in self.root_dir.iterdir() if p.is_dir()])

    def _load_index(self, index_name: str) -> Dict[str, Any]:
        if index_name in self._cache:
            return self._cache[index_name]

        index_dir = self.root_dir / index_name
        vectors_path = index_dir / "vectors.npy"
        meta_path = index_dir / "metadata.jsonl"

        index_dir.mkdir(parents=True, exist_ok=True)
        if vectors_path.exists() and meta_path.exists():
            vectors = np.load(vectors_path)
            ids: List[str] = []
            texts: List[str] = []
            metas: List[Dict[str, Any]] = []
            with meta_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    ids.append(record["id"])
                    texts.append(record["text"])
                    metas.append(record.get("metadata", {}))
        else:
            vectors = np.zeros((0, 1), dtype=np.float32)
            ids, texts, metas = [], [], []

        data = {"vectors": vectors, "ids": ids, "texts": texts, "metas": metas}
        self._cache[index_name] = data
        return data

    def _persist_index(self, index_name: str, index: Dict[str, Any]) -> None:
        index_dir = self.root_dir / index_name
        index_dir.mkdir(parents=True, exist_ok=True)
        vectors_path = index_dir / "vectors.npy"
        meta_path = index_dir / "metadata.jsonl"

        np.save(vectors_path, index["vectors"])
        with meta_path.open("w", encoding="utf-8") as handle:
            for idx, chunk_id in enumerate(index["ids"]):
                record = {
                    "id": chunk_id,
                    "text": index["texts"][idx],
                    "metadata": index["metas"][idx],
                }
                handle.write(json.dumps(record) + "\n")


class PgVectorStore(VectorStore):
    """Postgres + pgvector implementation (Supabase-ready)."""

    def __init__(self, dsn: str, embedding_dim: int, table_name: str = "rag_chunks"):
        import psycopg
        from pgvector.psycopg import register_vector

        self.dsn = dsn
        self.embedding_dim = embedding_dim
        self.table_name = table_name
        self._psycopg = psycopg
        self._register_vector = register_vector
        self._ensure_schema()

    def _connect(self):
        conn = self._psycopg.connect(self.dsn)
        self._register_vector(conn)
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    index_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding VECTOR({self.embedding_dim}) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {self.table_name}_index_name_idx ON {self.table_name} (index_name);"
            )
            conn.commit()

    def upsert(self, index_name: str, chunks: Iterable[RagChunk]) -> int:
        new_chunks = list(chunks)
        if not new_chunks:
            return 0
        from pgvector import Vector

        with self._connect() as conn:
            for chunk in new_chunks:
                conn.execute(
                    f"""
                    INSERT INTO {self.table_name} (id, index_name, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        index_name = EXCLUDED.index_name,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                    """,
                    (
                        chunk.id,
                        index_name,
                        chunk.text,
                        json.dumps(chunk.metadata),
                        Vector(chunk.embedding),
                    ),
                )
            conn.commit()
        return len(new_chunks)

    def query(self, index_name: str, embedding: List[float], top_k: int, score_threshold: float) -> List[RagMatch]:
        from pgvector import Vector

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, content, metadata, 1 - (embedding <=> %s) AS score
                FROM {self.table_name}
                WHERE index_name = %s
                ORDER BY embedding <=> %s
                LIMIT %s;
                """,
                (Vector(embedding), index_name, Vector(embedding), top_k),
            ).fetchall()

        matches: List[RagMatch] = []
        for row in rows:
            score = float(row[3])
            if score < score_threshold:
                continue
            metadata = row[2]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            matches.append(
                RagMatch(
                    id=row[0],
                    text=row[1],
                    metadata=metadata,
                    score=score,
                )
            )
        return matches

    def list_indexes(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT index_name FROM {self.table_name} ORDER BY index_name;"
            ).fetchall()
        return [row[0] for row in rows]


def create_chunk_id(prefix: str = "chunk") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _normalize_np(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def _normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms
