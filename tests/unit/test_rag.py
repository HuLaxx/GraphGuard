import pytest

from ml.serving.rag.embeddings import HashEmbeddingProvider
from ml.serving.rag.vector_store import SimpleVectorStore, RagChunk
from ml.serving.rag.pipeline import RagPipeline, RagDocument, chunk_text
from ml.serving.rag.llm import MockLLM


def test_chunk_text_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert chunks[0] == "abcdefghij"
    assert chunks[1].startswith("ij")


def test_simple_vector_store_query(tmp_path):
    embedder = HashEmbeddingProvider(dimension=32)
    store = SimpleVectorStore(tmp_path)

    docs = [
        RagDocument(id="doc1", text="neo4j graph pipeline", metadata={"source": "doc1"}),
        RagDocument(id="doc2", text="xgboost training metrics", metadata={"source": "doc2"}),
    ]

    pipeline = RagPipeline(
        embedder=embedder,
        store=store,
        llm=None,
        chunk_size=80,
        chunk_overlap=10,
        default_top_k=2,
        score_threshold=0.0,
    )

    pipeline.ingest_documents("test", docs)
    response = pipeline.query("test", "neo4j graph pipeline")

    assert response.sources
    assert any("neo4j" in src["preview"].lower() for src in response.sources)


def test_rag_pipeline_with_mock_llm(tmp_path):
    embedder = HashEmbeddingProvider(dimension=16)
    store = SimpleVectorStore(tmp_path)
    llm = MockLLM()

    pipeline = RagPipeline(
        embedder=embedder,
        store=store,
        llm=llm,
        chunk_size=80,
        chunk_overlap=10,
        default_top_k=2,
        score_threshold=0.0,
    )

    pipeline.ingest_documents(
        "demo",
        [RagDocument(id="doc", text="redis caching layer", metadata={"source": "cache"})],
    )

    response = pipeline.query("demo", "redis caching layer")
    assert response.answer.startswith("MOCK_RESPONSE")
    assert response.model == "mock"
