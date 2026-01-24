# GraphGuard - Backend Services

This directory contains all backend Python services for the GraphGuard fraud detection platform.

## Structure

```
backend/
└── graphql/          # Strawberry GraphQL schema + resolvers
    ├── __init__.py
    ├── schema.py
    └── resolvers.py
```

## Services

### GraphQL Service (`graphql/`)
- Strawberry GraphQL schema and resolvers
- Neo4j-backed queries with safe fallbacks

### API Service (located in `ml/serving/`)
- FastAPI REST scoring + GraphQL router
- Main entrypoint: `ml/serving/api.py`

## Getting Started

```bash
pip install -e "ml[dev]"
uvicorn ml.serving.api:app --reload
```
