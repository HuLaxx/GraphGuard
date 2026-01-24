"""
GraphGuard - Production FastAPI Server
======================================
Streamlined fraud detection API with trained XGBoost model
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import xgboost as xgb
import pandas as pd
import numpy as np

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="GraphGuard Fraud Detection API",
    description="Real-time transaction fraud scoring with XGBoost",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def require_api_key(api_key: str = Security(api_key_header)) -> None:
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        # Allow if no key configured (dev mode)
        return
    if api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ============================================
# Models
# ============================================

class TransactionRequest(BaseModel):
    """Transaction scoring request"""
    transaction_id: str
    user_id: str
    merchant_id: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    device_id: str
    ip_address: str
    timestamp: Optional[datetime] = None

class FeatureContribution(BaseModel):
    """Feature contribution to score"""
    feature: str
    value: float
    impact: str  # 'high', 'medium', 'low'

class ExplanationResponse(BaseModel):
    """Fraud score explanation"""
    top_features: List[FeatureContribution]
    reasoning: str

class PredictionResponse(BaseModel):
    """Fraud prediction response"""
    transaction_id: str
    fraud_score: float = Field(..., ge=0, le=1)
    decision: str  # AUTO_APPROVE, REVIEW, AUTO_DECLINE
    latency_ms: int
    model_version: str
    explanation: ExplanationResponse

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    redis_available: bool
    version: str
    uptime_seconds: int

# ============================================
# Global State
# ============================================

class AppState:
    """Application state"""
    def __init__(self):
        self.model: Optional[xgb.XGBClassifier] = None
        self.model_loaded = False
        self.start_time = time.time()
        self.redis_client = None
        
    def load_model(self):
        """Load XGBoost model"""
        if self.model_loaded:
            return
            
        model_path = os.getenv('XGB_MODEL_PATH', 'models/xgboost_rigorous/xgboost_fraud.json')
        
        if not Path(model_path).exists():
            print(f"⚠️  Model not found at {model_path}, using default scores")
            return
        
        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(model_path)
            self.model_loaded = True
            print(f"✅ Model loaded from {model_path}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
    
    def check_redis(self):
        """Check Redis availability"""
        if self.redis_client:
            return True
            
        try:
            import redis
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_timeout=2
            )
            self.redis_client.ping()
            return True
        except:
            return False

state = AppState()

# ============================================
# Startup
# ============================================

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    print("\n" + "="*60)
    print("GraphGuard API Starting...")
    print("="*60)
    state.load_model()
    redis_ok = state.check_redis()
    print(f"Redis: {'✅ Connected' if redis_ok else '⚠️  Not available'}")
    print("="*60 + "\n")

# ============================================
# Helper Functions
# ============================================

def extract_features(request: TransactionRequest) -> Dict[str, float]:
    """
    Extract features from transaction request.
    In production, this would fetch from Feast/Neo4j.
    For now, we use simplified mock features based on the request.
    """
    
    # Time features
    ts = request.timestamp or datetime.now()
    hour = ts.hour
    day_of_week = ts.weekday()
    is_weekend = 1.0 if day_of_week >= 5 else 0.0
    
    # Simple heuristics for demo
    # In production, these come from Feast feature store
    features = {
        # Transaction features
        'amount': request.amount,
        'amount_log': np.log1p(request.amount),
        'hour_of_day': float(hour),
        'day_of_week': float(day_of_week),
        'is_weekend': is_weekend,
        
        # Mock velocity features (would be from Feast)
        'velocity_1h_count': 1.0,
        'velocity_24h_count': 3.0,
        'velocity_24h_amount': request.amount * 3.0,
        
        # Mock user features (would be from Feast)
        'user_meta_avg_txn_amount': 100.0,
        'user_amt_ratio': request.amount / 100.0,
        
        # Mock merchant features
        'merchant_meta_avg_transaction_amount': 150.0,
        'merchant_meta_is_high_risk': 0.0,
        'merchant_amt_ratio': request.amount / 150.0,
        
        # Mock device features
        'device_meta_is_shared': 0.0,
        'device_is_shared': 0.0,
        
        # Mock graph features (would be from Neo4j)
        'graph_pagerank': 0.0002,
        'graph_degree': 10.0,
        'graph_out_degree': 5.0,
        'graph_in_degree': 5.0,
        'graph_betweenness': 0.5,
        
        # Interaction features
        'high_risk_merchant_txn': 0.0,
    }
    
    return features

def make_decision(score: float) -> str:
    """Convert fraud score to decision"""
    if score < 0.3:
        return "AUTO_APPROVE"
    elif score < 0.7:
        return "REVIEW"
    else:
        return "AUTO_DECLINE"

def generate_explanation(score: float, features: Dict[str, float]) -> ExplanationResponse:
    """Generate simple explanation"""
    
    # Top contributing features (simplified)
    top_features = [
        FeatureContribution(
            feature="amount",
            value=features.get('amount', 0),
            impact="high" if features.get('amount', 0) > 500 else "low"
        ),
        FeatureContribution(
            feature="velocity_24h_count",
            value=features.get('velocity_24h_count', 0),
            impact="medium"
        ),
        FeatureContribution(
            feature="graph_pagerank",
            value=features.get('graph_pagerank', 0),
            impact="medium"
        ),
    ]
    
    if score < 0.3:
        reasoning = "Transaction appears legitimate based on normal patterns."
    elif score < 0.7:
        reasoning = "Transaction flagged for manual review due to moderate risk indicators."
    else:
        reasoning = "High fraud probability detected. Recommended decline."
    
    return ExplanationResponse(
        top_features=top_features,
        reasoning=reasoning
    )

# ============================================
# Endpoints
# ============================================

@app.get("/", tags=["Info"])
async def root():
    """API root"""
    return {
        "service": "GraphGuard Fraud Detection API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if state.model_loaded else "degraded",
        model_loaded=state.model_loaded,
        redis_available=state.check_redis(),
        version="2.0.0",
        uptime_seconds=int(time.time() - state.start_time)
    )

@app.post("/score", response_model=PredictionResponse, tags=["Prediction"], dependencies=[Security(require_api_key)])
async def score_transaction(request: TransactionRequest):
    """
    Score a transaction for fraud
    
    Returns fraud score (0-1) and decision recommendation.
    """
    start_time = time.time()
    
    # Extract features
    features = extract_features(request)
    
    # Predict
    if state.model_loaded and state.model:
        # Prepare features for model (must match training feature order)
        # Get feature names from model
        try:
            # Create DataFrame with features
            X = pd.DataFrame([features])
            
            # Predict probability
            fraud_prob = state.model.predict_proba(X)[0, 1]
            fraud_score = float(fraud_prob)
            
        except Exception as e:
            print(f"Prediction error: {e}")
            # Fallback to simple heuristic
            fraud_score = 0.5 if request.amount > 1000 else 0.2
    else:
        # Model not loaded - use simple heuristic
        fraud_score = 0.8 if request.amount > 1000 else 0.2
    
    # Make decision
    decision = make_decision(fraud_score)
    
    # Generate explanation
    explanation = generate_explanation(fraud_score, features)
    
    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)
    
    return PredictionResponse(
        transaction_id=request.transaction_id,
        fraud_score=fraud_score,
        decision=decision,
        latency_ms=latency_ms,
        model_version="xgboost_v2_rigorous",
        explanation=explanation
    )

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    uptime = int(time.time() - state.start_time)
    
    metrics_text = f"""# HELP graphguard_uptime_seconds API uptime in seconds
# TYPE graphguard_uptime_seconds gauge
graphguard_uptime_seconds {uptime}

# HELP graphguard_model_loaded Whether ML model is loaded
# TYPE graphguard_model_loaded gauge
graphguard_model_loaded {1 if state.model_loaded else 0}
"""
    
    return metrics_text

# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"\n🚀 Starting GraphGuard API on port {port}...")
    print(f"📖 Docs: http://localhost:{port}/docs\n")
    
    uvicorn.run(
        "api_production:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
