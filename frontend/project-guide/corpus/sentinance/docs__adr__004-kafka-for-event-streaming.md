# ADR 004: Kafka for Event Streaming

**Status:** Accepted  
**Date:** 2026-01-22  
**Deciders:** Engineering Team

## Context

Sentinance needs to handle:
- Real-time price updates from multiple exchanges
- Event-driven architecture for alerts and notifications
- Decoupled services for horizontal scaling
- Message persistence for replay capability

Current implementation uses Redis Pub/Sub, which works but has limitations.

## Decision

Add **Apache Kafka** for event streaming alongside Redis Pub/Sub.

**Architecture:**
```
Exchange APIs → Kafka → Consumers (API, Alerts, Analytics)
                ↓
            Redis (cache, fast pub/sub for WebSocket)
```

## Rationale

### Why Kafka?

| Feature | Redis Pub/Sub | Kafka |
|---------|---------------|-------|
| Message persistence | ❌ No | ✅ Configurable retention |
| Replay capability | ❌ No | ✅ Consumer can seek |
| Horizontal scaling | ⚠️ Limited | ✅ Partitions |
| Message ordering | ✅ Yes | ✅ Per partition |
| Throughput | 100K msg/s | 1M+ msg/s |

### When to Use Each

| Use Case | Technology | Reason |
|----------|------------|--------|
| WebSocket to clients | Redis Pub/Sub | Low latency, ephemeral |
| Price ingestion | Kafka | Persistence, replay |
| Alert triggers | Kafka | Reliable delivery |
| Analytics events | Kafka | Batch processing |

## Consequences

### Positive
- Message durability (no data loss on service restart)
- Horizontal scaling with consumer groups
- Event replay for debugging and analytics
- Decoupled architecture

### Negative
- Additional infrastructure complexity
- JVM-based (higher memory footprint)
- Learning curve for operations

## Fallback for Demo Mode

When Kafka is unavailable, the system falls back to Redis-only:

```python
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    log.warning("Kafka not available, using Redis-only mode")
```

## Topics

```
sentinance.prices      # All price updates
sentinance.alerts      # Alert triggers
sentinance.predictions # ML predictions
sentinance.trades      # Trade executions (future)
```

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Kafka vs Redis Pub/Sub](https://aws.amazon.com/compare/the-difference-between-kafka-and-redis/)
