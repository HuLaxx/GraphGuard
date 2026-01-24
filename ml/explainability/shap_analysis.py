"""
GraphGuard - SHAP Explainability Analysis
==========================================
File: ml/explainability/shap_analysis.py
Reference: Specification.md Lines 1766-1811

Goal: Compute SHAP values for model explainability.

Explainers:
- XGBoost: shap.TreeExplainer (fast, exact)
- GAT: shap.KernelExplainer (slow, approximate)

Gotchas (from spec):
- KernelExplainer is O(n^2 * m) - very slow, use TreeExplainer when possible
- Cache SHAP values for frequently queried users (Redis)
"""

import os
from typing import Optional, Dict, Any, List

import numpy as np
import pandas as pd
import shap
import joblib
import redis
import json
import hashlib
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# SHAP Explainer Class
# ============================================

class FraudExplainer:
    """
    SHAP-based explainability for fraud detection models.
    Reference: Specification.md Lines 1766-1811
    """
    
    def __init__(
        self,
        xgb_model=None,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 900  # 15 minutes
    ):
        self.xgb_model = xgb_model
        self.xgb_explainer: Optional[shap.TreeExplainer] = None
        self.expected_value: Optional[float] = None
        self.feature_names: Optional[List[str]] = None
        
        # Redis for caching SHAP values
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        
        if xgb_model is not None:
            self._init_explainer()
    
    def _init_explainer(self) -> None:
        """Initialize SHAP TreeExplainer for XGBoost."""
        self.xgb_explainer = shap.TreeExplainer(self.xgb_model)
        self.expected_value = float(self.xgb_explainer.expected_value)
        
        if hasattr(self.xgb_model, 'feature_names_in_'):
            self.feature_names = list(self.xgb_model.feature_names_in_)
        
        logger.info("SHAP explainer initialized", expected_value=self.expected_value)
    
    def _cache_key(self, features_hash: str) -> str:
        """Generate cache key for SHAP values."""
        return f"shap:{features_hash}"
    
    def _compute_features_hash(self, features: np.ndarray) -> str:
        """Compute hash of feature values for caching."""
        return hashlib.md5(features.tobytes()).hexdigest()[:16]
    
    def explain(
        self,
        features: pd.DataFrame,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Compute SHAP explanation for a single transaction.
        
        Args:
            features: DataFrame with single row of features
            use_cache: Whether to check/store in Redis cache
        
        Returns:
            Dictionary with SHAP values and feature contributions
        """
        if self.xgb_explainer is None:
            raise ValueError("Explainer not initialized")
        
        # Convert to numpy if needed
        if isinstance(features, pd.DataFrame):
            feature_values = features.values[0]
            feature_names = list(features.columns)
        else:
            feature_values = features
            feature_names = self.feature_names or [f"feature_{i}" for i in range(len(features))]
        
        # Check cache
        if use_cache and self.redis_client:
            cache_key = self._cache_key(self._compute_features_hash(feature_values))
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug("SHAP cache hit", cache_key=cache_key)
                return json.loads(cached)
        
        # Compute SHAP values
        shap_values = self.xgb_explainer.shap_values(feature_values.reshape(1, -1))
        
        if isinstance(shap_values, list):
            # Binary classification returns list of [class_0, class_1]
            shap_values = shap_values[1][0]  # Use fraud class
        else:
            shap_values = shap_values[0]
        
        # Build explanation
        contributions = []
        for i, (name, value, shap_val) in enumerate(zip(feature_names, feature_values, shap_values)):
            contributions.append({
                'feature': name,
                'value': float(value),
                'shap_value': float(shap_val),
                'impact': 'increases' if shap_val > 0 else 'decreases'
            })
        
        # Sort by absolute SHAP value
        contributions.sort(key=lambda x: abs(x['shap_value']), reverse=True)
        
        explanation = {
            'base_value': self.expected_value,
            'prediction_contribution': float(sum(shap_values)),
            'top_features': contributions[:10],  # Top 10 features
            'all_features': contributions
        }
        
        # Cache result
        if use_cache and self.redis_client:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(explanation)
            )
        
        return explanation
    
    def explain_batch(
        self,
        features: pd.DataFrame,
        max_samples: int = 100
    ) -> List[Dict[str, Any]]:
        """Explain multiple transactions."""
        explanations = []
        
        for i in range(min(len(features), max_samples)):
            exp = self.explain(features.iloc[[i]], use_cache=False)
            explanations.append(exp)
        
        return explanations
    
    def generate_summary_plot_data(
        self,
        features: pd.DataFrame,
        max_samples: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate data for SHAP summary plot (beeswarm).
        
        Returns:
            Dictionary with feature importance rankings
        """
        if self.xgb_explainer is None:
            raise ValueError("Explainer not initialized")
        
        # Sample if too large
        if len(features) > max_samples:
            features = features.sample(max_samples, random_state=42)
        
        shap_values = self.xgb_explainer.shap_values(features)
        
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Fraud class
        
        # Compute mean absolute SHAP value per feature
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        feature_importance = []
        for i, name in enumerate(features.columns):
            feature_importance.append({
                'feature': name,
                'mean_abs_shap': float(mean_abs_shap[i]),
                'rank': 0  # Will be set after sorting
            })
        
        # Sort by importance
        feature_importance.sort(key=lambda x: x['mean_abs_shap'], reverse=True)
        for i, f in enumerate(feature_importance):
            f['rank'] = i + 1
        
        return {
            'feature_importance': feature_importance[:20],
            'total_features': len(features.columns),
            'samples_used': len(features)
        }
    
    def format_explanation_text(
        self,
        explanation: Dict[str, Any],
        top_n: int = 5
    ) -> str:
        """
        Generate human-readable explanation text.
        
        Args:
            explanation: SHAP explanation dict
            top_n: Number of top features to include
        
        Returns:
            Plain English explanation
        """
        lines = []
        lines.append("This transaction was flagged as suspicious due to:")
        
        for i, feat in enumerate(explanation['top_features'][:top_n]):
            feature = feat['feature']
            value = feat['value']
            impact = feat['impact']
            
            # Generate human-readable text
            if 'txn_count' in feature:
                if feat['shap_value'] > 0:
                    lines.append(f"  - High transaction velocity ({int(value)} transactions)")
                else:
                    lines.append(f"  - Normal transaction velocity ({int(value)} transactions)")
            elif 'amount' in feature.lower():
                if feat['shap_value'] > 0:
                    lines.append(f"  - Unusual amount (${value:.2f})")
                else:
                    lines.append(f"  - Normal amount (${value:.2f})")
            elif 'device' in feature.lower():
                if 'new' in feature.lower() and value:
                    lines.append("  - Transaction from new device")
                elif 'shared' in feature.lower() and value:
                    lines.append("  - Transaction from shared device")
            elif 'pagerank' in feature.lower():
                if feat['shap_value'] > 0:
                    lines.append(f"  - User is highly connected in network (PageRank: {value:.4f})")
            elif 'community' in feature.lower():
                lines.append(f"  - User belongs to suspicious community #{int(value)}")
            else:
                lines.append(f"  - {feature}: {value:.2f} ({impact} fraud risk)")
        
        return "\n".join(lines)
    
    def save(self, path: str) -> None:
        """Save explainer to disk."""
        joblib.dump({
            'explainer': self.xgb_explainer,
            'expected_value': self.expected_value,
            'feature_names': self.feature_names
        }, path)
        logger.info("Explainer saved", path=path)
    
    def load(self, path: str) -> None:
        """Load explainer from disk."""
        data = joblib.load(path)
        self.xgb_explainer = data['explainer']
        self.expected_value = data['expected_value']
        self.feature_names = data.get('feature_names')
        logger.info("Explainer loaded", path=path)


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    import xgboost as xgb
    
    parser = argparse.ArgumentParser(description="Generate SHAP explanations")
    parser.add_argument("--model", required=True, help="XGBoost model path")
    parser.add_argument("--data", required=True, help="Features Parquet path")
    parser.add_argument("--output", default="./shap_explainer.pkl", help="Output explainer path")
    args = parser.parse_args()
    
    # Load model
    model = xgb.XGBClassifier()
    model.load_model(args.model)
    
    # Load data
    df = pd.read_parquet(args.data)
    
    # Initialize explainer
    explainer = FraudExplainer(xgb_model=model)
    
    # Generate summary
    summary = explainer.generate_summary_plot_data(df)
    print("\nTop 10 Most Important Features:")
    for feat in summary['feature_importance'][:10]:
        print(f"  {feat['rank']}. {feat['feature']}: {feat['mean_abs_shap']:.4f}")
    
    # Save explainer
    explainer.save(args.output)
    print(f"\nExplainer saved to {args.output}")
