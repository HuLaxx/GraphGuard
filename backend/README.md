# GraphGuard - Backend Services

This directory contains all backend Python services for the GraphGuard fraud detection platform.

## Structure

```
backend/
├── api/              # FastAPI main API service
│   └── pyproject.toml
└── graphql/          # GraphQL resolvers (Strawberry)
    └── pyproject.toml
```

## Services

### API Service (`api/`)
- FastAPI-based REST and GraphQL endpoints
- Real-time fraud scoring
- Case management APIs

### GraphQL Service (`graphql/`)
- Strawberry GraphQL schema and resolvers
- DataLoader for efficient batching

## Getting Started

```bash
cd backend/api
pip install -e .
uvicorn app.main:app --reload
```
