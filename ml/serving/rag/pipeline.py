"""
RAG pipeline: chunking, retrieval, and answer generation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from ml.serving.rag.embeddings import EmbeddingProvider
from ml.serving.rag.vector_store import RagChunk, RagMatch, VectorStore, create_chunk_id
from ml.serving.rag.llm import LLMClient


@dataclass
class RagDocument:
    id: str
    text: str
    metadata: Dict[str, Any]


@dataclass
class RagResponse:
    answer: str
    sources: List[Dict[str, Any]]
    model: str
    index_name: str
    latency_ms: int


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    if chunk_size <= 0:
        return [text]
    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size // 4)

    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == length:
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return chunks


def build_prompt(question: str, matches: List[RagMatch]) -> List[Dict[str, str]]:
    context_lines = []
    for i, match in enumerate(matches, start=1):
        source = match.metadata.get("source", "unknown")
        context_lines.append(f"[Source {i}] {source}\n{match.text}")

    context = "\n\n".join(context_lines)

    system = (
        "You are GraphGuard Assistant. Answer only using the provided context. "
        "If the context is insufficient, say you do not have enough information. "
        "Cite sources as [Source #]."
    )

    user = (
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        "Answer with citations."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


class RagPipeline:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        llm: Optional[LLMClient],
        chunk_size: int,
        chunk_overlap: int,
        default_top_k: int,
        score_threshold: float,
    ):
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_top_k = default_top_k
        self.score_threshold = score_threshold

    def ingest_documents(self, index_name: str, documents: Iterable[RagDocument]) -> int:
        chunks: List[RagChunk] = []
        for doc in documents:
            parts = chunk_text(doc.text, self.chunk_size, self.chunk_overlap)
            for idx, part in enumerate(parts):
                chunk_id = create_chunk_id("rag")
                metadata = dict(doc.metadata)
                metadata["doc_id"] = doc.id
                metadata["chunk_index"] = idx
                chunks.append(
                    RagChunk(
                        id=chunk_id,
                        text=part,
                        metadata=metadata,
                        embedding=[],
                    )
                )

        if not chunks:
            return 0

        embeddings = self.embedder.embed_texts([c.text for c in chunks])
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        return self.store.upsert(index_name, chunks)

    def query(
        self,
        index_name: str,
        question: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> RagResponse:
        start = time.time()
        top_k = top_k or self.default_top_k
        threshold = score_threshold if score_threshold is not None else self.score_threshold

        query_embedding = self.embedder.embed_query(question)
        matches = self.store.query(index_name, query_embedding, top_k, threshold)

        if not matches:
            answer = "I do not have enough information in the current index to answer that."
            latency = int((time.time() - start) * 1000)
            return RagResponse(answer=answer, sources=[], model=self._model_name(), index_name=index_name, latency_ms=latency)

        if self.llm is None:
            answer = "LLM not configured. Retrieved sources only."
        else:
            prompt = build_prompt(question, matches)
            answer = self.llm.complete(prompt)

        sources = []
        for match in matches:
            sources.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata,
                "preview": match.text[:240],
            })

        latency = int((time.time() - start) * 1000)
        return RagResponse(
            answer=answer,
            sources=sources,
            model=self._model_name(),
            index_name=index_name,
            latency_ms=latency,
        )

    def _model_name(self) -> str:
        return self.llm.model if self.llm else "none"
