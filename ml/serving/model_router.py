"""
GraphGuard - Model Router with A/B Testing
============================================
File: ml/serving/model_router.py
Reference: Specification.md Lines 2089-2151

Goal: Route requests between champion and challenger models.

A/B Testing Strategy:
- 90% traffic → Champion (production model)
- 10% traffic → Challenger (new model being tested)
- Log all predictions for offline analysis

Gotchas (from spec):
- Use consistent hashing (user_id) instead of random() for same user experience
- Log BOTH champion and challenger predictions for unbiased comparison
"""

import os
import hashlib
from collections import deque
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Model Version Enum
# ============================================

class ModelVersion(Enum):
    """Model versions for A/B testing."""
    CHAMPION = "ensemble_v2"
    CHALLENGER = "ensemble_v3_gat_improved"


# ============================================
# Model Router Class (Spec Lines 2099-2141)
# ============================================

class ModelRouter:
    """
    Route requests between champion and challenger models.
    Reference: Specification.md Lines 2099-2141
    """
    
    def __init__(
        self,
        champion_weight: float = 0.9,
        challenger_weight: float = 0.1,
        feature_order: Optional[List[str]] = None,
        max_log_entries: int = 10000
    ):
        if abs(champion_weight + challenger_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        
        self.champion_weight = champion_weight
        self.challenger_weight = challenger_weight
        
        self.champion_model = None
        self.challenger_model = None
        self.feature_order = feature_order
        
        # Prediction logging
        self.predictions_log = deque(maxlen=max_log_entries)
    
    def _load_model(self, version: ModelVersion):
        """
        Load model from MLflow registry.
        Reference: Specification.md Lines 2108-2112
        """
        try:
            import mlflow
            model_uri = f"models:/fraud_ensemble/{version.value}"
            return mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            logger.warning("Could not load model from MLflow", version=version.value, error=str(e))
            return None
    
    def initialize(self) -> None:
        """Load models on startup."""
        self.champion_model = self._load_model(ModelVersion.CHAMPION)
        self.challenger_model = self._load_model(ModelVersion.CHALLENGER)
        
        logger.info(
            "Models loaded",
            champion_loaded=self.champion_model is not None,
            challenger_loaded=self.challenger_model is not None
        )
    
    def _get_bucket(self, user_id: str) -> float:
        """
        Get consistent bucket for user.
        Gotcha: Use consistent hashing so same user always gets same model.
        """
        hash_bytes = hashlib.md5(user_id.encode()).digest()
        bucket = int.from_bytes(hash_bytes[:2], 'little') / 65536.0
        return bucket
    
    def route_request(self, user_id: str) -> Tuple[Any, ModelVersion]:
        """
        Route request to champion or challenger.
        Reference: Specification.md Lines 2114-2119
        
        Args:
            user_id: User ID for consistent routing
        
        Returns:
            Tuple of (model, version)
        """
        bucket = self._get_bucket(user_id)
        
        if bucket < self.challenger_weight:
            model = self.challenger_model or self.champion_model
            version = ModelVersion.CHALLENGER if self.challenger_model else ModelVersion.CHAMPION
        else:
            model = self.champion_model
            version = ModelVersion.CHAMPION
        
        logger.debug(
            "Request routed",
            user_id=user_id[:8] + "...",
            version=version.value,
            bucket=f"{bucket:.3f}"
        )
        
        return model, version
    
    def predict(
        self,
        user_id: str,
        features: Dict[str, Any]
    ) -> Tuple[float, ModelVersion]:
        """
        Make prediction with routed model.
        Reference: Specification.md Lines 2121-2131
        """
        model, version = self.route_request(user_id)
        
        if model is None:
            logger.warning("No model available, returning default")
            return 0.5, ModelVersion.CHAMPION
        
        # Make prediction
        import numpy as np
        feature_vector = self._build_feature_vector(features)
        
        try:
            prediction = float(model.predict(feature_vector)[0])
        except Exception as e:
            logger.error("Prediction failed", error=str(e))
            prediction = 0.5
        
        # Log for A/B analysis
        self._log_prediction(user_id, version, prediction, features)
        
        return prediction, version

    def _build_feature_vector(self, features: Dict[str, Any]) -> Any:
        """Build deterministic feature vector from dict input."""
        if self.feature_order:
            ordered = [features.get(name, 0) for name in self.feature_order]
        else:
            ordered = [features[key] for key in sorted(features.keys())]
        import numpy as np
        return np.array([ordered], dtype=float)
    
    def _log_prediction(
        self,
        user_id: str,
        version: ModelVersion,
        prediction: float,
        features: Dict[str, Any]
    ) -> None:
        """
        Log prediction for A/B analysis.
        Reference: Specification.md Lines 2133-2140
        """
        log_entry = {
            'user_id': user_id,
            'model_version': version.value,
            'prediction': prediction,
            'timestamp': datetime.utcnow().isoformat(),
            'features_hash': hashlib.md5(str(features).encode()).hexdigest()[:8]
        }
        
        self.predictions_log.append(log_entry)
        
        # In production: publish to Kafka
        # kafka_producer.send('model.predictions', log_entry)
    
    def get_experiment_stats(self) -> Dict[str, Any]:
        """Get A/B experiment statistics."""
        champion_preds = [p for p in self.predictions_log if p['model_version'] == ModelVersion.CHAMPION.value]
        challenger_preds = [p for p in self.predictions_log if p['model_version'] == ModelVersion.CHALLENGER.value]
        
        return {
            'champion_count': len(champion_preds),
            'challenger_count': len(challenger_preds),
            'champion_avg_score': sum(p['prediction'] for p in champion_preds) / len(champion_preds) if champion_preds else 0,
            'challenger_avg_score': sum(p['prediction'] for p in challenger_preds) / len(challenger_preds) if challenger_preds else 0,
            'total_predictions': len(self.predictions_log)
        }


# ============================================
# Singleton for API Usage
# ============================================

_router_instance: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create model router singleton."""
    global _router_instance
    
    if _router_instance is None:
        _router_instance = ModelRouter()
        _router_instance.initialize()
    
    return _router_instance
