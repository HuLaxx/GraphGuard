# ADR 006: WebSocket Architecture with Redis Pub/Sub

**Status:** Accepted  
**Date:** 2026-01-22

## Context

Sentinance requires real-time price streaming to connected clients with:
- Sub-100ms latency
- Support for 1000+ concurrent connections
- Horizontal scaling across multiple API instances

## Decision

Use **Redis Pub/Sub** as the message broker for WebSocket distribution.

## Architecture

```
Exchange APIs
    ↓
┌──────────────────┐
│  Price Stream    │ (Background Task)
│  Service         │
└──────────────────┘
    ↓
┌──────────────────┐
│  Redis Pub/Sub   │ (Channel: prices)
└──────────────────┘
    ↓
┌──────────────────────────────────┐
│  API Instance 1  │  API Instance 2  │
│  (WebSocket)     │  (WebSocket)     │
└──────────────────────────────────┘
    ↓
  Clients
```

## Implementation

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis = redis.Redis()
    
    async def broadcast_from_redis(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("prices")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self.broadcast(message["data"])
```

## Consequences

### Positive
- Horizontal scaling (any instance can serve any client)
- Low latency (<50ms)
- Simple implementation
- Built-in with existing Redis

### Negative
- No message persistence (acceptable for price streaming)
- At-most-once delivery

## References

- [Redis Pub/Sub Documentation](https://redis.io/docs/manual/pubsub/)
