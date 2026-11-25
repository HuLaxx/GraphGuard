# ADR 008: Prometheus Metrics Strategy

**Status:** Accepted  
**Date:** 2026-01-22

## Context

Need observability for:
- API performance (latency, throughput)
- Business metrics (predictions served, chat sessions)
- Infrastructure health (Redis, DB connections)

## Decision

Use **Prometheus** with auto-instrumented FastAPI metrics.

## Metrics Defined

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sentinance_requests_total` | Counter | method, endpoint, status | Total requests |
| `sentinance_request_latency_seconds` | Histogram | method, endpoint | Request duration |
| `sentinance_websocket_connections` | Gauge | - | Active WS connections |
| `sentinance_prediction_latency_seconds` | Histogram | model, horizon | ML prediction time |
| `sentinance_chat_latency_seconds` | Histogram | model | AI chat response time |
| `sentinance_errors_total` | Counter | type, endpoint | Error count |

## Implementation

```python
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('sentinance_requests_total', 'Total requests', 
                        ['method', 'endpoint', 'status'])

REQUEST_LATENCY = Histogram('sentinance_request_latency_seconds', 
                            'Request latency', 
                            ['method', 'endpoint'],
                            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
```

## Consequences

### Positive
- Industry standard (Grafana integration)
- Low overhead
- Pull-based (no push infrastructure needed)

### Negative
- Cardinality explosion risk with high-cardinality labels
- Requires Prometheus server running

## Grafana Queries

```promql
# Request rate by endpoint
sum(rate(sentinance_requests_total[5m])) by (endpoint)

# P99 latency
histogram_quantile(0.99, rate(sentinance_request_latency_seconds_bucket[5m]))
```
