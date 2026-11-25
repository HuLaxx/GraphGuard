# FleetFlow Backend

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Run the server
uvicorn src.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/orders` | GET/POST | Order management |
| `/api/v1/drivers` | GET | Driver management |
| `/api/v1/drivers/{id}/location` | POST | GPS tracking |
| `/api/v1/routes` | GET | Route management |
| `/api/v1/vehicles` | GET | Vehicle management |
| `/api/v1/optimization/optimize` | POST | Route optimization |
| `/api/v1/rag/indexes` | GET/POST | List or create RAG indexes |
| `/api/v1/rag/ingest` | POST | Ingest documents into an index |
| `/api/v1/rag/query` | POST | Retrieve + answer with citations |

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## RAG Configuration

Configure an OpenAI-compatible LLM endpoint (or leave unset to use extractive fallback).

```
RAG_DATA_DIR=.rag
RAG_TOP_K=4
RAG_MIN_SCORE=0.2
RAG_MAX_CONTEXT_CHARS=4000
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your_key
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30
```
