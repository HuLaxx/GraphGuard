"""
GraphGuard - Feast Feature Definitions
=======================================
File: data-eng/feast/feature_repo/features.py
Reference: Specification.md Lines 1083-1127

Defines entities and feature views for the GraphGuard fraud detection system.

Gotchas (from spec):
- TTL determines how long features stay in Redis - set based on freshness requirements
- materialize-incremental only works if timestamp_field is properly set
"""

from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Float64, Int64, String, Bool


# ============================================
# Entities
# ============================================

user = Entity(
    name="user",
    join_keys=["user_id"],
    description="User who performs transactions"
)

merchant = Entity(
    name="merchant",
    join_keys=["merchant_id"],
    description="Merchant receiving payments"
)


# ============================================
# Feature Sources
# ============================================

transaction_source = FileSource(
    name="transaction_features_source",
    path="data/transaction_features.parquet",  # s3://graphguard/... for production
    timestamp_field="event_timestamp"
)

graph_source = FileSource(
    name="graph_features_source",
    path="data/graph_features.parquet",  # s3://graphguard/... for production
    timestamp_field="event_timestamp"
)


# ============================================
# Transaction Features (Spec Lines 1091-1107)
# ============================================

transaction_features = FeatureView(
    name="transaction_features",
    entities=[user],
    ttl=timedelta(days=365),
    schema=[
        # Temporal features
        Field(name="txn_count_1h", dtype=Int64),
        Field(name="txn_count_24h", dtype=Int64),
        Field(name="txn_count_7d", dtype=Int64),
        Field(name="amount_sum_1h", dtype=Float32),
        Field(name="amount_sum_24h", dtype=Float32),
        Field(name="amount_mean_7d", dtype=Float32),
        Field(name="amount_std_7d", dtype=Float32),
        Field(name="amount_zscore", dtype=Float32),
        Field(name="time_since_last_txn", dtype=Float32),
        Field(name="hour_of_day", dtype=Int64),
        Field(name="day_of_week", dtype=Int64),
        
        # Device features
        Field(name="device_age_days", dtype=Float32),
        Field(name="device_user_count", dtype=Int64),
        Field(name="is_new_device", dtype=Bool),
        Field(name="is_shared_device", dtype=Bool),
        
        # Merchant features (precomputed for user)
        Field(name="merchant_avg_amount", dtype=Float32),
        Field(name="merchant_fraud_rate", dtype=Float32),
        Field(name="amount_vs_merchant_avg", dtype=Float32),
        
        # User aggregate features
        Field(name="user_total_txn_count", dtype=Int64),
        Field(name="user_avg_amount", dtype=Float32),
        Field(name="user_unique_merchants", dtype=Int64),
        Field(name="user_unique_devices", dtype=Int64),
        
        # Velocity features
        Field(name="rapid_fire_flag", dtype=Bool),
        Field(name="high_value_flag", dtype=Bool),
        Field(name="amount_pct_of_daily", dtype=Float32),
    ],
    source=transaction_source,
    online=True  # Materialize to Redis
)


# ============================================
# Graph Features (Spec Lines 1109-1121)
# ============================================

graph_features = FeatureView(
    name="graph_features",
    entities=[user],
    ttl=timedelta(days=7),  # Update weekly (graph algorithms are expensive)
    schema=[
        Field(name="pagerank", dtype=Float32),
        Field(name="community_id", dtype=Int64),
        Field(name="betweenness", dtype=Float32),
        Field(name="degree", dtype=Int64),
        Field(name="out_degree", dtype=Int64),
        Field(name="in_degree", dtype=Int64),
    ],
    source=graph_source,
    online=True  # Materialize to Redis
)


# ============================================
# Merchant Features (Additional)
# ============================================

merchant_source = FileSource(
    name="merchant_features_source",
    path="data/merchant_features.parquet",
    timestamp_field="event_timestamp"
)

merchant_features = FeatureView(
    name="merchant_features",
    entities=[merchant],
    ttl=timedelta(days=30),
    schema=[
        Field(name="merchant_avg_amount", dtype=Float32),
        Field(name="merchant_std_amount", dtype=Float32),
        Field(name="merchant_txn_count", dtype=Int64),
        Field(name="merchant_fraud_rate", dtype=Float32),
    ],
    source=merchant_source,
    online=True
)
