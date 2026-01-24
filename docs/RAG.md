# GraphGuard RAG Assistant

This module adds a local-first Retrieval-Augmented Generation (RAG) assistant that indexes your repo and serves answers via FastAPI.

## Local-first (free stack)

- Vector store: Simple local store (numpy + json) in `data/rag/indexes/`
- Embeddings: SentenceTransformers (local)
- LLM: Groq (optional) or Ollama (local)

### Quick start

```bash
# 1) Set env vars
cp .env.example .env

# 2) Install deps
pip install -e "ml[dev]"

# 3) Start API
uvicorn ml.serving.api:app --reload --port 8000

# 4) Ingest repo
curl -X POST http://localhost:8000/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_type":"repo","root_path":".","index":"graphguard"}'

# 5) Ask questions
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How does the Kafka -> Neo4j pipeline work?","index":"graphguard"}'
```

## Free-tier deployment targets

- Supabase (Postgres + pgvector): set `RAG_VECTOR_STORE=pgvector` and `RAG_PG_DSN`
- Upstash (Redis): optional for cache / rate limiting
- Railway: API + frontend hosting

## Environment variables

- `RAG_ENABLED=true|false`
- `RAG_VECTOR_STORE=simple|pgvector`
- `RAG_DEFAULT_INDEX=graphguard`
- `RAG_EMBEDDINGS_PROVIDER=sentence_transformers|hash`
- `RAG_EMBEDDINGS_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `RAG_LLM_PROVIDER=groq|openai_compatible|ollama`
- `RAG_LLM_MODEL=llama-3.3-70b-versatile` (or `openai/gpt-oss-120b` on Groq)
- `GROQ_API_KEY=...`
- `OPENAI_COMPATIBLE_BASE_URL=...`
- `OPENAI_COMPATIBLE_API_KEY=...`
- `RAG_PG_DSN=postgresql://...`
- `RAG_AUTO_INDEX_ON_STARTUP=true|false`
- `RAG_AUTO_INDEX_ROOT=.`
- `RAG_AUTO_INDEX_INDEX=graphguard`
- `RAG_AUTO_INDEX_BACKGROUND=true|false`

Frontend:

```
NEXT_PUBLIC_RAG_ALLOW_INGEST=true
```

## Notes

- RAG "learns" by indexing new content. It does not retrain the model.
- For large repos, use include/exclude filters to keep indexing fast.
