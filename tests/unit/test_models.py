"""
GraphGuard - Unit Tests for ML Models
=======================================
File: tests/unit/test_models.py

Tests for XGBoost, GAT, and Ensemble models.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_features():
    """Sample feature DataFrame for testing."""
    return pd.DataFrame({
        'txn_count_1h': [3, 8, 1, 15, 2],
        'txn_count_24h': [10, 25, 5, 50, 8],
        'amount_sum_1h': [150.0, 2500.0, 50.0, 5000.0, 100.0],
        'amount_mean_7d': [100.0, 500.0, 75.0, 300.0, 80.0],
        'amount_zscore': [0.5, 4.0, -0.5, 3.5, 0.2],
        'device_age_days': [365, 1, 180, 0, 90],
        'pagerank': [0.001, 0.015, 0.002, 0.025, 0.001],
        'amount': [125.0, 1500.0, 45.0, 3000.0, 95.0],
        'fraud': [0, 1, 0, 1, 0],
        'timestamp': pd.date_range('2024-01-01', periods=5, freq='D')
    })


@pytest.fixture
def sample_graph_data():
    """Sample graph data for GAT testing."""
    import torch
    from torch_geometric.data import Data
    
    # 5 nodes, 8 edges
    x = torch.randn(5, 6)  # 6 features per node
    edge_index = torch.tensor([
        [0, 0, 1, 1, 2, 2, 3, 4],
        [1, 2, 0, 3, 0, 4, 4, 3]
    ], dtype=torch.long)
    y = torch.tensor([0], dtype=torch.long)
    
    return Data(x=x, edge_index=edge_index, y=y)


# ============================================
# XGBoost Model Tests
# ============================================

class TestXGBoostFraudModel:
    """Tests for XGBoostFraudModel."""
    
    def test_prepare_data_temporal_split(self, sample_features):
        """Test that temporal split works correctly."""
        from ml.training.baseline_xgboost import XGBoostFraudModel
        
        model = XGBoostFraudModel()
        X_train, X_val, X_test, y_train, y_val, y_test = model.prepare_data(
            sample_features,
            split_date='2024-01-03'
        )
        
        # First 2 samples should be in train+val, last 3 in test
        assert len(X_train) == 1
        assert len(X_val) == 1
        assert len(X_test) == 3
        assert len(y_train) == 1
        assert len(y_val) == 1
        assert len(y_test) == 3
    
    def test_apply_smote(self, sample_features):
        """Test SMOTE balancing."""
        from ml.training.baseline_xgboost import XGBoostFraudModel
        
        model = XGBoostFraudModel(smote_ratio=0.5)
        
        X = sample_features.drop(['fraud', 'timestamp'], axis=1)
        y = sample_features['fraud']
        
        X_balanced, y_balanced = model.apply_smote(X, y)
        
        # After SMOTE, should have more fraud samples
        assert y_balanced.sum() > y.sum()
    
    def test_make_decision(self):
        """Test decision logic thresholds."""
        from ml.serving.api import make_decision
        
        assert make_decision(0.1) == "AUTO_APPROVE"
        assert make_decision(0.3) == "REVIEW"
        assert make_decision(0.5) == "REVIEW"
        assert make_decision(0.7) == "AUTO_DECLINE"
        assert make_decision(0.9) == "AUTO_DECLINE"
    
    def test_feature_columns_defined(self):
        """Test that feature columns are properly defined."""
        from ml.training.baseline_xgboost import FEATURE_COLUMNS
        
        assert len(FEATURE_COLUMNS) > 20  # Should have 30+ features
        assert 'txn_count_1h' in FEATURE_COLUMNS
        assert 'pagerank' in FEATURE_COLUMNS
        assert 'amount' in FEATURE_COLUMNS


# ============================================
# GAT Model Tests
# ============================================

class TestFraudGAT:
    """Tests for FraudGAT model."""
    
    @pytest.mark.skipif(not pytest.importorskip("torch"), reason="PyTorch not installed")
    def test_forward_pass(self, sample_graph_data):
        """Test forward pass produces valid output."""
        from ml.training.gat_model import FraudGAT
        import torch
        
        model = FraudGAT(in_channels=6, hidden_channels=32, out_channels=2, heads=2)
        model.eval()
        
        # Add batch for single graph
        sample_graph_data.batch = torch.zeros(5, dtype=torch.long)
        
        with torch.no_grad():
            output = model(sample_graph_data)
        
        # Should output log probabilities for 2 classes
        assert output.shape == (1, 2)
        assert torch.isfinite(output).all()
    
    @pytest.mark.skipif(not pytest.importorskip("torch"), reason="PyTorch not installed")
    def test_model_parameters(self):
        """Test model has trainable parameters."""
        from ml.training.gat_model import FraudGAT
        
        model = FraudGAT(in_channels=3, hidden_channels=64, out_channels=2)
        
        params = list(model.parameters())
        assert len(params) > 0
        
        total_params = sum(p.numel() for p in params)
        assert total_params > 1000  # Should have non-trivial parameters


# ============================================
# Ensemble Model Tests
# ============================================

class TestEnsembleFraudModel:
    """Tests for EnsembleFraudModel."""
    
    def test_weight_validation(self):
        """Test weight validation."""
        from ml.training.ensemble_model import EnsembleFraudModel
        
        # Valid weights
        model = EnsembleFraudModel(xgb_weight=0.6, gat_weight=0.4)
        assert model.xgb_weight == 0.6
        
        # Invalid weights should raise
        with pytest.raises(ValueError):
            EnsembleFraudModel(xgb_weight=0.5, gat_weight=0.3)


# ============================================
# Feature Cache Tests
# ============================================

class TestFeatureCache:
    """Tests for FeatureCache."""
    
    def test_cache_key_deterministic(self):
        """Test cache key generation is deterministic."""
        from ml.serving.feature_cache import FeatureCache
        
        cache = FeatureCache(redis_client=None)
        
        features = ['feature_a', 'feature_b', 'feature_c']
        
        key1 = cache._cache_key('user_123', features)
        key2 = cache._cache_key('user_123', features)
        key3 = cache._cache_key('user_123', ['feature_c', 'feature_a', 'feature_b'])
        
        assert key1 == key2  # Same inputs = same key
        assert key1 == key3  # Order shouldn't matter (sorted internally)
    
    def test_cache_key_includes_features(self):
        """Test different features produce different keys."""
        from ml.serving.feature_cache import FeatureCache
        
        cache = FeatureCache(redis_client=None)
        
        key1 = cache._cache_key('user_123', ['feature_a'])
        key2 = cache._cache_key('user_123', ['feature_b'])
        
        assert key1 != key2


# ============================================
# SHAP Explainer Tests
# ============================================

class TestFraudExplainer:
    """Tests for FraudExplainer."""
    
    def test_format_explanation_text(self):
        """Test human-readable explanation generation."""
        from ml.explainability.shap_analysis import FraudExplainer
        
        explainer = FraudExplainer(xgb_model=None)
        
        explanation = {
            'base_value': 0.15,
            'prediction_contribution': 0.7,
            'top_features': [
                {'feature': 'txn_count_1h', 'value': 10, 'shap_value': 0.3, 'impact': 'increases'},
                {'feature': 'amount', 'value': 1500, 'shap_value': 0.25, 'impact': 'increases'},
                {'feature': 'device_age_days', 'value': 0, 'shap_value': 0.15, 'impact': 'increases'}
            ],
            'all_features': []
        }
        
        text = explainer.format_explanation_text(explanation)
        
        assert 'suspicious' in text.lower()
        assert 'transaction velocity' in text.lower() or 'amount' in text.lower()


# ============================================
# Drift Detection Tests
# ============================================

class TestDriftDetector:
    """Tests for DriftDetector."""
    
    def test_should_retrain_critical_drift(self):
        """Test retraining trigger on critical feature drift."""
        from ml.monitoring.drift_detection import DriftDetector
        
        detector = DriftDetector()
        
        result = {
            'dataset_drift': True,
            'drift_score': 0.2,
            'drifted_features': ['amount', 'txn_count_1h']  # amount is critical
        }
        
        assert detector.should_retrain(result) == True
    
    def test_should_not_retrain_minor_drift(self):
        """Test no retraining on non-critical drift."""
        from ml.monitoring.drift_detection import DriftDetector
        
        detector = DriftDetector()
        
        result = {
            'dataset_drift': False,
            'drift_score': 0.05,
            'drifted_features': ['device_age_days']  # Not critical
        }
        
        assert detector.should_retrain(result) == False


# ============================================
# Model Router Tests
# ============================================

class TestModelRouter:
    """Tests for ModelRouter A/B testing."""
    
    def test_consistent_routing(self):
        """Test same user always gets same model."""
        from ml.serving.model_router import ModelRouter
        
        router = ModelRouter()
        
        model1, version1 = router.route_request('user_abc')
        model2, version2 = router.route_request('user_abc')
        
        assert version1 == version2  # Consistent hashing
    
    def test_traffic_split(self):
        """Test traffic roughly follows weight distribution."""
        from ml.serving.model_router import ModelRouter
        
        router = ModelRouter(champion_weight=0.9, challenger_weight=0.1)
        
        versions = []
        for i in range(100):
            _, version = router.route_request(f'user_{i}')
            versions.append(version.value)
        
        challenger_count = sum(1 for v in versions if 'challenger' in v.lower())
        
        # Should be roughly 10% (+/-10% tolerance for small sample)
        assert 0 <= challenger_count <= 30


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
