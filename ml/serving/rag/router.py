"""
FastAPI router for RAG endpoints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import anyio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ml.serving.rag.settings import get_rag_settings
from ml.serving.rag.embeddings import HashEmbeddingProvider, SentenceTransformersEmbeddingProvider
from ml.serving.rag.vector_store import PgVectorStore, SimpleVectorStore
from ml.serving.rag.llm import GroqClient, OpenAICompatibleClient, OllamaClient, LLMClient
from ml.serving.rag.pipeline import RagPipeline, RagDocument
from ml.serving.rag.indexer import iter_repo_documents

router = APIRouter(prefix="/rag", tags=["RAG"])


@dataclass
class RagContext:
    settings: Any
    pipeline: RagPipeline


_RAG_CTX: RagContext | None = None


def _build_embedder(settings) -> Any:
    provider = settings.embeddings_provider.lower()
    if provider == "hash":
        return HashEmbeddingProvider()
    if provider == "sentence_transformers":
        try:
            return SentenceTransformersEmbeddingProvider(settings.embeddings_model)
        except Exception:
            return HashEmbeddingProvider()
    return HashEmbeddingProvider()


def _build_store(settings, embedding_dim: int):
    store_name = settings.vector_store.lower()
    if store_name == "pgvector":
        if not settings.pg_dsn:
            raise RuntimeError("RAG_PG_DSN or SUPABASE_DB_URL is required for pgvector store")
        return PgVectorStore(settings.pg_dsn, embedding_dim, settings.pg_table)
    return SimpleVectorStore(settings.index_dir)


def _build_llm(settings) -> Optional[LLMClient]:
    provider = settings.llm_provider.lower()
    if provider == "groq" and settings.groq_api_key:
        return GroqClient(settings.groq_api_key, settings.llm_model, settings.llm_temperature, settings.llm_max_tokens)
    if provider in {"openai_compatible", "openai"} and settings.openai_base_url:
        return OpenAICompatibleClient(
            settings.openai_base_url,
            settings.openai_api_key,
            settings.llm_model,
            settings.llm_temperature,
            settings.llm_max_tokens,
        )
    if provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.llm_model, settings.llm_temperature, settings.llm_max_tokens)
    return None


def get_rag_context() -> RagContext:
    global _RAG_CTX
    if _RAG_CTX is not None:
        return _RAG_CTX

    settings = get_rag_settings()
    embedder = _build_embedder(settings)
    store = _build_store(settings, embedder.dimension)
    llm = _build_llm(settings)
    pipeline = RagPipeline(
        embedder=embedder,
        store=store,
        llm=llm,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        default_top_k=settings.top_k,
        score_threshold=settings.score_threshold,
    )
    _RAG_CTX = RagContext(settings=settings, pipeline=pipeline)
    return _RAG_CTX


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    index: str | None = None
    top_k: Optional[int] = None
    score_threshold: Optional[float] = None


class RagQueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    model: str
    index: str
    latency_ms: int


class RagIngestRequest(BaseModel):
    source_type: Literal["text", "repo"] = "text"
    index: Optional[str] = None
    text: Optional[str] = None
    root_path: Optional[str] = None
    include_exts: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None
    max_file_kb: Optional[int] = None


class RagIngestResponse(BaseModel):
    indexed_chunks: int
    files_indexed: int
    skipped_files: int
    index: str


@router.get("/status")
async def rag_status():
    settings = get_rag_settings()
    ctx = get_rag_context()
    return {
        "enabled": settings.enabled,
        "vector_store": settings.vector_store,
        "embeddings_provider": settings.embeddings_provider,
        "llm_provider": settings.llm_provider,
        "llm_model": ctx.pipeline._model_name(),
        "index_dir": str(settings.index_dir),
        "auto_index_enabled": settings.auto_index_enabled,
        "auto_index_root": str(settings.auto_index_root),
        "auto_index_index": settings.auto_index_index,
    }


@router.get("/indexes")
async def rag_indexes():
    ctx = get_rag_context()
    return {
        "indexes": ctx.pipeline.store.list_indexes(),
        "default": ctx.settings.default_index,
    }


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(payload: RagQueryRequest):
    settings = get_rag_settings()
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled")

    ctx = get_rag_context()
    index_name = payload.index or settings.default_index

    result = await anyio.to_thread.run_sync(
        ctx.pipeline.query,
        index_name,
        payload.question,
        payload.top_k,
        payload.score_threshold,
    )

    return RagQueryResponse(
        answer=result.answer,
        sources=result.sources,
        model=result.model,
        index=result.index_name,
        latency_ms=result.latency_ms,
    )


@router.post("/ingest", response_model=RagIngestResponse)
async def rag_ingest(payload: RagIngestRequest):
    settings = get_rag_settings()
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled")

    ctx = get_rag_context()
    index_name = payload.index or settings.default_index

    if payload.source_type == "text":
        if not payload.text:
            raise HTTPException(status_code=400, detail="text is required for source_type=text")

        document = RagDocument(id=f"manual:{int(time.time())}", text=payload.text, metadata={"source": "manual"})
        count = await anyio.to_thread.run_sync(ctx.pipeline.ingest_documents, index_name, [document])
        return RagIngestResponse(indexed_chunks=count, files_indexed=1, skipped_files=0, index=index_name)

    root_path = Path(payload.root_path or Path.cwd())
    include_exts = payload.include_exts or settings.repo_include_exts
    exclude_dirs = payload.exclude_dirs or settings.repo_exclude_dirs
    max_file_kb = payload.max_file_kb or settings.repo_max_file_kb

    documents = list(iter_repo_documents(root_path, include_exts, exclude_dirs, max_file_kb))
    if not documents:
        return RagIngestResponse(indexed_chunks=0, files_indexed=0, skipped_files=0, index=index_name)

    count = await anyio.to_thread.run_sync(ctx.pipeline.ingest_documents, index_name, documents)
    return RagIngestResponse(indexed_chunks=count, files_indexed=len(documents), skipped_files=0, index=index_name)
