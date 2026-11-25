# ADR 005: Graceful Degradation for Demo Mode

**Status:** Accepted  
**Date:** 2026-01-22  
**Deciders:** Engineering Team

## Context

Sentinance has two deployment modes:

1. **Local/Production**: Full stack with all services
2. **Demo/Free-tier**: Simplified deployment on Vercel/Railway

The demo mode should work with limited infrastructure while clearly indicating 
what features are unavailable.

## Decision

Implement **graceful degradation patterns** throughout the codebase so one codebase 
works in both modes.

## Implementation Patterns

### Pattern 1: Try/Except Imports

```python
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

# Usage
if KAFKA_AVAILABLE:
    producer.send('topics', message)
else:
    await redis.publish('channel', message)
```

### Pattern 2: Environment Detection

```python
def is_production() -> bool:
    return os.getenv("ENVIRONMENT") == "production"

def get_database_url() -> str:
    if is_production():
        return os.getenv("TIMESCALEDB_URL")  # Full TimescaleDB
    return os.getenv("DATABASE_URL")  # Regular PostgreSQL/Supabase
```

### Pattern 3: Feature Flags

```python
FEATURES = {
    "kafka": os.getenv("KAFKA_ENABLED", "false").lower() == "true",
    "mlflow": os.getenv("MLFLOW_ENABLED", "false").lower() == "true",
    "tracing": os.getenv("JAEGER_ENABLED", "false").lower() == "true",
}
```

### Pattern 4: Fallback Responses

```python
async def get_prediction(symbol: str) -> dict:
    try:
        # Try ML model
        return await ml_model.predict(symbol)
    except ModelNotAvailable:
        # Fallback to rule-based
        return await rule_based_prediction(symbol)
```

## Components with Fallbacks

| Component | Production | Demo Fallback |
|-----------|------------|---------------|
| Database | TimescaleDB | Supabase PostgreSQL |
| Cache | Redis Cluster | Upstash Redis |
| Streaming | Kafka | Redis Pub/Sub only |
| ML Tracking | MLflow | Local files |
| Tracing | Jaeger | Disabled |
| AI Chat | LangGraph + Gemini | Simple responses |

## Demo Mode Disclaimer

The frontend displays a banner in demo mode:

```tsx
{isDemoMode && (
  <Banner type="warning">
    This is a simplified demo. For full features including ML predictions, 
    real-time Kafka streaming, and distributed tracing, 
    <a href="https://github.com/...">run locally</a>.
  </Banner>
)}
```

## Consequences

### Positive
- One codebase for all environments
- Easy testing of production code locally
- Progressive enhancement

### Negative
- More conditional logic
- Need to test both paths
- Documentation must cover both modes

## References

- [Graceful Degradation Pattern](https://martinfowler.com/bliki/GracefulDegradation.html)
- [Feature Flags Best Practices](https://launchdarkly.com/blog/what-are-feature-flags/)
