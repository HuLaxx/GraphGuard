# ADR 010: FastAPI as Backend Framework

**Status:** Accepted  
**Date:** 2026-01-22

## Context

Sentinance backend needs:
- High-performance REST API
- WebSocket support for real-time streaming
- Async I/O for concurrent exchange API calls
- Automatic OpenAPI documentation

## Decision

Use **FastAPI** as the primary backend framework.

## Rationale

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| Async native | ✅ | ⚠️ (with extensions) | ⚠️ (with ASGI) |
| WebSocket | ✅ Built-in | ❌ Needs extension | ⚠️ Channels |
| OpenAPI docs | ✅ Auto-generated | ❌ Manual | ⚠️ With DRF |
| Performance | ~10K req/s | ~2K req/s | ~1K req/s |
| Type hints | ✅ Required | ⚠️ Optional | ⚠️ Optional |

## Key Features Used

1. **Async Endpoints**: For non-blocking exchange API calls
2. **Dependency Injection**: For auth, database sessions
3. **Pydantic Models**: For request/response validation
4. **Background Tasks**: For price streaming
5. **WebSocket**: For real-time client updates

## Implementation Pattern

```python
from fastapi import FastAPI, Depends, WebSocket, BackgroundTasks

app = FastAPI(title="Sentinance API")

@app.get("/api/prices/{symbol}")
async def get_price(symbol: str, user: User = Depends(get_current_user)):
    return await exchange.get_price(symbol)

@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
```

## Consequences

### Positive
- Excellent developer experience
- Auto-generated docs at `/docs`
- Native async for high concurrency
- Type safety with Pydantic

### Negative
- Smaller ecosystem than Django
- Less batteries-included

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI vs Flask Benchmark](https://www.techempower.com/benchmarks/)
