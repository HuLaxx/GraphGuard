"""
GraphGuard - FastAPI Inference API
====================================
File: ml/serving/api.py
Reference: Specification.md Lines 1887-2023

Goal: Real-time fraud scoring API with latency < 100ms.

Latency Budget:
- Feast feature retrieval: 15ms
- Neo4j graph query: 30ms
- XGBoost inference: 10ms
- GAT inference: 25ms
- SHAP values: 10ms
- Network latency: 5ms

Gotchas (from spec):
- Use async def for I/O-bound operations (Feast, Neo4j)
- Set Uvicorn workers=4 for parallelism
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import structlog
import anyio
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from ml.serving.feature_cache import FeatureCache

logger = structlog.get_logger(__name__)


app = FastAPI(
    title="GraphGuard Fraud Detection API",
    description="Real-time transaction fraud scoring with explainability",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Ensure project root is on sys.path for sibling imports (GraphQL schema)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# CORS middleware
cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
if not cors_origins:
    cors_origins = ["*"]
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (production)
if os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true":
    try:
        from ml.serving.rate_limiter import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)
        logger.info("Rate limiting middleware enabled")
    except ImportError as e:
        logger.warning("Rate limiting not available", error=str(e))

# API key auth
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(api_key_header)) -> None:
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if api_key != expected_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# Optional GraphQL endpoint
try:
    from strawberry.fastapi import GraphQLRouter
    from backend.graphql.resolvers import schema as graphql_schema

    def graphql_context_getter(request: Request) -> dict:
        return {"request": request}

    graphql_app = GraphQLRouter(graphql_schema, context_getter=graphql_context_getter)
    app.include_router(graphql_app, prefix="/graphql")
    logger.info("GraphQL endpoint enabled")
except Exception as e:
    logger.warning("GraphQL endpoint not enabled", error=str(e))


# ============================================
# Feature Definitions (Default Ordering)
# ============================================

DEFAULT_FEATURE_ORDER = [
    # Temporal features
    'txn_count_1h', 'txn_count_24h', 'txn_count_7d',
    'amount_sum_1h', 'amount_sum_24h',
    'amount_mean_7d', 'amount_std_7d',
    'amount_zscore', 'time_since_last_txn',
    'hour_of_day', 'day_of_week',
    # Device features
    'device_age_days', 'device_user_count',
    'is_new_device', 'is_shared_device',
    # Merchant features
    'merchant_avg_amount', 'merchant_fraud_rate',
    'amount_vs_merchant_avg',
    # User features
    'user_total_txn_count', 'user_avg_amount',
    'user_unique_merchants', 'user_unique_devices',
    # Graph features
    'pagerank', 'community_id', 'betweenness',
    'degree', 'out_degree', 'in_degree',
    # Velocity features
    'rapid_fire_flag', 'high_value_flag', 'amount_pct_of_daily'
]

TRANSACTION_FEATURES = {
    'txn_count_1h', 'txn_count_24h', 'txn_count_7d',
    'amount_sum_1h', 'amount_sum_24h',
    'amount_mean_7d', 'amount_std_7d',
    'amount_zscore', 'time_since_last_txn',
    'hour_of_day', 'day_of_week',
    'device_age_days', 'device_user_count',
    'is_new_device', 'is_shared_device',
    'merchant_avg_amount', 'merchant_fraud_rate',
    'amount_vs_merchant_avg',
    'user_total_txn_count', 'user_avg_amount',
    'user_unique_merchants', 'user_unique_devices',
    'rapid_fire_flag', 'high_value_flag', 'amount_pct_of_daily'
}

GRAPH_FEATURES = {
    'pagerank', 'community_id', 'betweenness',
    'degree', 'out_degree', 'in_degree'
}

RUNTIME_FEATURES = {'amount'}


# ============================================
# Request/Response Models (Spec Lines 1914-1929)
# ============================================

class TransactionRequest(BaseModel):
    """Transaction scoring request."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    user_id: str = Field(..., description="User initiating transaction")
    merchant_id: str = Field(..., description="Merchant receiving payment")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    device_id: str = Field(..., description="Device fingerprint")
    ip_address: str = Field(..., description="Client IP address")
    timestamp: Optional[datetime] = Field(default=None, description="Transaction time")


class FeatureContribution(BaseModel):
    """Feature contribution to fraud score."""
    feature: str
    value: float
    importance: float
    impact: str  # 'increases' or 'decreases'


class ExplanationResponse(BaseModel):
    """SHAP-based explanation."""
    top_features: List[FeatureContribution]
    graph_reasoning: str
    plain_english: str


class PredictionResponse(BaseModel):
    """Fraud prediction response."""
    transaction_id: str
    fraud_score: float = Field(..., ge=0, le=1)
    decision: str = Field(..., description="AUTO_APPROVE, REVIEW, or AUTO_DECLINE")
    latency_ms: int
    model_version: str
    explanation: ExplanationResponse
    cached: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    redis_connected: bool
    feast_connected: bool
    version: str


# ============================================
# Dependency Injection
# ============================================

class ModelContext:
    """Container for ML models and connections."""
    
    def __init__(self):
        self.xgb_model = None
        self.gat_model = None
        self.feast_store = None
        self.redis_client = None
        self.feature_cache: Optional[FeatureCache] = None
        self.shap_explainer = None
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization of models."""
        if self._initialized:
            return
        
        import redis
        import xgboost as xgb
        
        # Redis
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Redis connected", host=redis_host)
        except Exception as e:
            logger.warning("Redis not available", error=str(e))
            self.redis_client = None
        
        # XGBoost model
        model_path = os.getenv('XGB_MODEL_PATH', 'models/xgboost_fraud.json')
        if os.path.exists(model_path):
            self.xgb_model = xgb.XGBClassifier()
            self.xgb_model.load_model(model_path)
            logger.info("XGBoost model loaded", path=model_path)
        else:
            logger.warning("XGBoost model not found", path=model_path)

        # Feast store (optional)
        try:
            from feast import FeatureStore
            default_repo_path = Path(__file__).resolve().parents[2] / 'data-eng' / 'feast' / 'feature_repo'
            repo_path = Path(os.getenv('FEAST_REPO_PATH', str(default_repo_path)))
            if repo_path.exists():
                self.feast_store = FeatureStore(repo_path=str(repo_path))
                logger.info("Feast store loaded", path=str(repo_path))
            else:
                logger.warning("Feast repo not found", path=str(repo_path))
        except Exception as e:
            logger.warning("Feast not available", error=str(e))
            self.feast_store = None

        # Feature cache
        self.feature_cache = FeatureCache(
            redis_client=self.redis_client,
            feast_store=self.feast_store
        )

        # Note: GAT can be loaded similarly
        self._initialized = True
    
    @property
    def is_ready(self) -> bool:
        return self._initialized and self.xgb_model is not None


# Global model context
model_ctx = ModelContext()


def get_model_context() -> ModelContext:
    """Dependency for model context."""
    if not model_ctx._initialized:
        model_ctx.initialize()
    return model_ctx


def _build_feature_refs(feature_names: List[str]) -> List[str]:
    """Map feature names to Feast feature references."""
    refs = []
    for name in feature_names:
        if name in GRAPH_FEATURES:
            refs.append(f"graph_features:{name}")
        elif name in TRANSACTION_FEATURES:
            refs.append(f"transaction_features:{name}")
    return refs


def _apply_runtime_overrides(
    features: Dict[str, Any],
    request: TransactionRequest
) -> Dict[str, Any]:
    """Apply request-derived features and computed fallbacks."""
    features['amount'] = request.amount

    # Compute z-score if missing
    if features.get('amount_zscore') is None:
        mean_7d = features.get('amount_mean_7d')
        std_7d = features.get('amount_std_7d')
        if std_7d and std_7d > 0:
            features['amount_zscore'] = (request.amount - mean_7d) / std_7d

    # Compute amount vs merchant avg if missing
    if features.get('amount_vs_merchant_avg') is None:
        merchant_avg = features.get('merchant_avg_amount')
        if merchant_avg and merchant_avg > 0:
            features['amount_vs_merchant_avg'] = request.amount / merchant_avg
        else:
            features['amount_vs_merchant_avg'] = 1.0

    # Fill time-based features if provided
    if request.timestamp:
        if features.get('hour_of_day') is None:
            features['hour_of_day'] = request.timestamp.hour
        if features.get('day_of_week') is None:
            weekday = request.timestamp.weekday()
            features['day_of_week'] = ((weekday + 1) % 7) + 1

    return features


def _normalize_feature_values(features: Dict[str, Any]) -> Dict[str, float]:
    """Coerce feature values to numeric types with safe defaults."""
    normalized: Dict[str, float] = {}
    for key, value in features.items():
        if value is None:
            normalized[key] = 0.0
        elif isinstance(value, bool):
            normalized[key] = float(int(value))
        else:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                normalized[key] = 0.0
    return normalized


def _get_feature_order(model) -> List[str]:
    """Get feature order from model if available, otherwise use defaults."""
    if model is not None and hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)
    return DEFAULT_FEATURE_ORDER


async def _run_blocking(func, *args, **kwargs):
    """Run blocking I/O in a thread to avoid blocking the event loop."""
    return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))


# ============================================
# Core Scoring Logic
# ============================================

async def score_with_xgboost(
    features: Dict[str, float],
    ctx: ModelContext
) -> float:
    """Score transaction with XGBoost model."""
    if ctx.xgb_model is None:
        return 0.5  # Default if model not loaded
    
    import numpy as np
    
    feature_order = _get_feature_order(ctx.xgb_model)
    feature_vector = np.array(
        [[features.get(name, 0.0) for name in feature_order]],
        dtype=float
    )
    
    proba = ctx.xgb_model.predict_proba(feature_vector)[0, 1]
    return float(proba)


def make_decision(fraud_score: float) -> str:
    """
    Convert fraud score to decision.
    Reference: Specification.md Lines 1983-1988
    """
    if fraud_score < 0.3:
        return "AUTO_APPROVE"
    elif fraud_score < 0.7:
        return "REVIEW"
    else:
        return "AUTO_DECLINE"


def generate_explanation(
    features: Dict[str, float],
    fraud_score: float
) -> ExplanationResponse:
    """Generate SHAP-style explanation."""
    # Simplified explanation (full SHAP would use FraudExplainer)
    contributions = []
    
    # Identify top contributing features
    if features.get('txn_count_1h', 0) > 5:
        contributions.append(FeatureContribution(
            feature='txn_count_1h',
            value=features.get('txn_count_1h', 0),
            importance=0.3,
            impact='increases'
        ))
    
    if features.get('amount', 0) > 1000:
        contributions.append(FeatureContribution(
            feature='amount',
            value=features.get('amount', 0),
            importance=0.25,
            impact='increases'
        ))
    
    if features.get('device_age_days', 30) < 1:
        contributions.append(FeatureContribution(
            feature='device_age_days',
            value=features.get('device_age_days', 0),
            importance=0.2,
            impact='increases'
        ))
    
    # Plain English explanation
    reasons = []
    if features.get('txn_count_1h', 0) > 5:
        reasons.append(f"high transaction velocity ({int(features.get('txn_count_1h', 0))} in 1h)")
    if features.get('amount', 0) > 1000:
        reasons.append(f"large amount (${features.get('amount', 0):.2f})")
    if features.get('device_age_days', 30) < 1:
        reasons.append("new device")
    
    plain_english = "Flagged due to: " + ", ".join(reasons) if reasons else "Normal transaction"
    
    return ExplanationResponse(
        top_features=contributions,
        graph_reasoning=f"PageRank: {features.get('pagerank', 0):.4f}",
        plain_english=plain_english
    )


# ============================================
# API Endpoints
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    model_ctx.initialize()
    logger.info("API startup complete")


@app.post("/score", response_model=PredictionResponse)
async def score_transaction(
    request: TransactionRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_api_key),
    ctx: ModelContext = Depends(get_model_context)
):
    """
    Score a transaction for fraud risk.
    
    Reference: Specification.md Lines 1931-2014
    """
    start_time = time.time()
    
    # 1. Check cache
    cached = False
    if ctx.redis_client:
        cache_key = f"fraud_score:{request.user_id}:{request.transaction_id}"
        try:
            cached_score = await _run_blocking(ctx.redis_client.get, cache_key)
            if cached_score:
                fraud_score = float(cached_score)
                latency_ms = int((time.time() - start_time) * 1000)
                
                return PredictionResponse(
                    transaction_id=request.transaction_id,
                    fraud_score=fraud_score,
                    decision=make_decision(fraud_score),
                    latency_ms=latency_ms,
                    model_version="cached",
                    explanation=ExplanationResponse(
                        top_features=[],
                        graph_reasoning="",
                        plain_english="Cached result"
                    ),
                    cached=True
                )
        except Exception as e:
            logger.warning("Cache read failed", error=str(e))
    
    # 2. Build features (Feast -> cache -> defaults)
    feature_names = [f for f in DEFAULT_FEATURE_ORDER if f not in RUNTIME_FEATURES]
    feature_refs = _build_feature_refs(feature_names)
    features: Dict[str, Any] = {}
    if ctx.feature_cache:
        features.update(
            await _run_blocking(ctx.feature_cache.get_features, request.user_id, feature_refs)
        )

    features = _apply_runtime_overrides(features, request)
    features = _normalize_feature_values(features)

    # Ensure all expected features exist
    for name in DEFAULT_FEATURE_ORDER:
        features.setdefault(name, 0.0)
    
    # 3. Score with XGBoost
    xgb_score = await score_with_xgboost(features, ctx)
    
    # 4. GAT score (placeholder for now)
    gat_score = None
    
    # 5. Ensemble score
    if gat_score is None:
        fraud_score = xgb_score
        model_version = "xgb_only"
    else:
        fraud_score = 0.6 * xgb_score + 0.4 * gat_score
        model_version = "ensemble_v2"
    
    # 6. Make decision
    decision = make_decision(fraud_score)
    
    # 7. Generate explanation
    explanation = generate_explanation(features, fraud_score)
    
    # 8. Cache result
    if ctx.redis_client:
        try:
            cache_key = f"fraud_score:{request.user_id}:{request.transaction_id}"
            await _run_blocking(ctx.redis_client.setex, cache_key, 900, str(fraud_score))  # 15 min TTL
        except Exception as e:
            logger.warning("Cache write failed", error=str(e))
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # 9. Log for audit (background task)
    background_tasks.add_task(
        log_prediction,
        request.transaction_id,
        fraud_score,
        decision,
        latency_ms
    )

    # 10. Update metrics (background task)
    background_tasks.add_task(
        update_metrics,
        ctx,
        decision,
        latency_ms,
        fraud_score > 0.7 # Simple high-risk threshold for 'potential fraud'
    )
    
    logger.info(
        "Transaction scored",
        transaction_id=request.transaction_id,
        fraud_score=fraud_score,
        decision=decision,
        latency_ms=latency_ms
    )
    
    return PredictionResponse(
        transaction_id=request.transaction_id,
        fraud_score=fraud_score,
        decision=decision,
        latency_ms=latency_ms,
        model_version=model_version,
        explanation=explanation,
        cached=cached
    )


@app.get("/health", response_model=HealthResponse)
async def health_check(ctx: ModelContext = Depends(get_model_context)):
    """Health check endpoint."""
    redis_ok = False
    if ctx.redis_client:
        try:
            await _run_blocking(ctx.redis_client.ping)
            redis_ok = True
        except:
            pass
    
    return HealthResponse(
        status="healthy" if ctx.is_ready else "degraded",
        model_loaded=ctx.xgb_model is not None,
        redis_connected=redis_ok,
        feast_connected=ctx.feast_store is not None,
        version="2.0.0"
    )


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint (placeholder)."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response
    
    # Would export actual metrics in production
    return Response(
        content=b"# No metrics yet\n",
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================
# Background Tasks
# ============================================

async def log_prediction(
    transaction_id: str,
    fraud_score: float,
    decision: str,
    latency_ms: int
):
    """Log prediction for audit trail."""
    logger.info(
        "Audit log",
        transaction_id=transaction_id,
        fraud_score=fraud_score,
        decision=decision,
        latency_ms=latency_ms
    )
    # In production: publish to Kafka for audit trail


async def update_metrics(
    ctx: ModelContext,
    decision: str,
    latency_ms: int,
    is_fraud: bool
):
    """Update dashboard metrics in Redis."""
    if not ctx.redis_client:
        return
        
    try:
        # Use a pipeline for atomicity
        pipe = ctx.redis_client.pipeline()
        
        # global counters
        pipe.incr("metrics:total_transactions")
        
        # decision counters
        if decision == "AUTO_APPROVE":
            pipe.incr("metrics:auto_approved")
        elif decision == "AUTO_DECLINE":
            pipe.incr("metrics:auto_declined")
        elif decision == "REVIEW":
            pipe.incr("metrics:pending_review")
            
        # fraud tracking (based on high score > 0.9 or label)
        if is_fraud:
            pipe.incr("metrics:potential_fraud")
            
        # latency tracking (simple moving average for demo)
        # In prod: use Prometheus histograms
        current_avg = float(ctx.redis_client.get("metrics:avg_latency") or 0.0)
        new_avg = (current_avg * 0.9) + (latency_ms * 0.1)
        pipe.set("metrics:avg_latency", new_avg)
        
        await _run_blocking(pipe.execute)
        
    except Exception as e:
        logger.warning("Failed to update metrics", error=str(e))


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        reload=True
    )
