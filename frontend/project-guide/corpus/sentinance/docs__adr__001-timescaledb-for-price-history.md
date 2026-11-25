# ADR 001: Use TimescaleDB for Price History Storage

**Status:** Accepted  
**Date:** 2026-01-21  
**Deciders:** Engineering Team

## Context

Sentinance needs to store time-series price data for:
- 8 assets (4 crypto + 4 market indices)
- Multiple time granularities (tick, 1m, 1h, 1d)
- 5+ years of historical data for ML training
- Real-time ingestion with sub-second latency

This results in approximately:
- 21M+ rows per year (8 assets × 365 days × 1440 minutes)
- 100M+ rows for 5-year training data

## Decision

Use **TimescaleDB** (PostgreSQL extension) instead of:
- Regular PostgreSQL
- InfluxDB
- MongoDB

## Rationale

### Why TimescaleDB?

1. **Automatic Partitioning**: Hypertables automatically partition by time
2. **SQL Compatibility**: Full PostgreSQL SQL support (joins, CTEs, window functions)
3. **Compression**: 10-20x compression ratio for time-series data
4. **Continuous Aggregates**: Pre-computed OHLCV rollups (hourly, daily)
5. **Mature Ecosystem**: Production-ready, extensive documentation

### Alternatives Considered

| Database | Pros | Cons | Decision |
|----------|------|------|----------|
| **InfluxDB** | Purpose-built for time-series | InfluxQL learning curve, no joins | Rejected |
| **PostgreSQL** | Familiar, reliable | Manual partitioning, no time-series optimizations | Rejected |
| **MongoDB** | Flexible schema | Not optimized for time-series, aggregations slower | Rejected |
| **QuestDB** | Very fast ingestion | Less mature, smaller community | Rejected |

## Consequences

### Positive
- Fast time-range queries (automatic index on time)
- Pre-computed aggregates reduce query load
- Can use existing SQLAlchemy ORM with minor changes
- Built-in retention policies for data lifecycle

### Negative
- Requires TimescaleDB-specific knowledge
- Slightly more complex than vanilla PostgreSQL
- Additional Docker image size (~200MB)

## Implementation

```sql
-- Create hypertable
SELECT create_hypertable('price_history', 'time', chunk_time_interval => INTERVAL '1 day');

-- Continuous aggregate for hourly OHLCV
CREATE MATERIALIZED VIEW price_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(price, time) as open,
    max(price) as high,
    min(price) as low,
    last(price, time) as close,
    sum(volume) as volume
FROM price_history
GROUP BY bucket, symbol;
```

## References

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [TimescaleDB vs InfluxDB Benchmark](https://www.timescale.com/blog/timescaledb-vs-influxdb/)
