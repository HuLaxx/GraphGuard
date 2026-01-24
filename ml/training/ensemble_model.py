"""
GraphGuard - Ensemble Model (XGBoost + GAT)
=============================================
File: ml/training/ensemble_model.py
Reference: Specification.md Lines 1705-1780

Goal: Combine XGBoost and GAT predictions via weighted average.

Ensemble Strategy:
ensemble_proba = 0.6 * xgb_proba + 0.4 * gat_proba

Gotchas (from spec):
- Tune weights via cross-validation
- If GAT doesn't improve, keep XGBoost only
"""

from typing import Optional, Dict, Tuple, List

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    roc_auc_score, average_precision_score, 
    precision_recall_curve, f1_score
)
import mlflow
import structlog

from .baseline_xgboost import XGBoostFraudModel
from .gat_model import FraudGAT

logger = structlog.get_logger(__name__)


# ============================================
# Ensemble Model Class
# ============================================

class EnsembleFraudModel:
    """
    Ensemble of XGBoost and GAT models.
    Reference: Specification.md Lines 1705-1780
    """
    
    def __init__(
        self,
        xgb_weight: float = 0.6,
        gat_weight: float = 0.4
    ):
        if abs(xgb_weight + gat_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        
        self.xgb_weight = xgb_weight
        self.gat_weight = gat_weight
        
        self.xgb_model: Optional[XGBoostFraudModel] = None
        self.gat_model: Optional[FraudGAT] = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def load_xgboost(self, model_path: str) -> None:
        """Load XGBoost model from disk."""
        self.xgb_model = XGBoostFraudModel()
        self.xgb_model.load(model_path)
        logger.info("XGBoost model loaded", path=model_path)
    
    def load_gat(self, model_path: str, in_channels: int = 6) -> None:
        """Load GAT model from disk."""
        self.gat_model = FraudGAT(in_channels=in_channels)
        self.gat_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.gat_model.to(self.device)
        self.gat_model.eval()
        logger.info("GAT model loaded", path=model_path)
    
    def predict_proba_xgb(self, X: pd.DataFrame) -> np.ndarray:
        """Get XGBoost fraud probabilities."""
        if self.xgb_model is None or self.xgb_model.model is None:
            raise ValueError("XGBoost model not loaded")
        
        return self.xgb_model.model.predict_proba(X)[:, 1]
    
    @torch.no_grad()
    def predict_proba_gat(self, graph_data) -> np.ndarray:
        """Get GAT fraud probabilities."""
        if self.gat_model is None:
            raise ValueError("GAT model not loaded")
        if graph_data is None:
            raise ValueError("graph_data is required for GAT predictions")
        
        self.gat_model.eval()
        graph_data = graph_data.to(self.device)
        
        out = self.gat_model(graph_data)
        probs = torch.exp(out)[:, 1]  # Probability of fraud
        
        return probs.cpu().numpy()
    
    def predict_proba(
        self,
        X_tabular: pd.DataFrame,
        X_graph,
        xgb_only: bool = False
    ) -> np.ndarray:
        """
        Get ensemble fraud probabilities.
        
        Args:
            X_tabular: DataFrame with tabular features for XGBoost
            X_graph: PyG Data object for GAT
            xgb_only: If True, use only XGBoost (skip GAT)
        
        Returns:
            Array of fraud probabilities
        """
        xgb_proba = self.predict_proba_xgb(X_tabular)
        
        if xgb_only or self.gat_model is None or self.gat_weight <= 0:
            return xgb_proba
        if X_graph is None:
            raise ValueError("X_graph is required when GAT is enabled")
        
        gat_proba = self.predict_proba_gat(X_graph)
        if len(gat_proba) != len(xgb_proba):
            raise ValueError("XGBoost and GAT predictions have mismatched lengths")
        
        # Weighted ensemble
        ensemble_proba = (
            self.xgb_weight * xgb_proba + 
            self.gat_weight * gat_proba
        )
        
        return ensemble_proba
    
    def predict(
        self,
        X_tabular: pd.DataFrame,
        X_graph,
        threshold: float = 0.5
    ) -> np.ndarray:
        """Get ensemble predictions."""
        proba = self.predict_proba(X_tabular, X_graph)
        return (proba > threshold).astype(int)
    
    def evaluate(
        self,
        X_tabular: pd.DataFrame,
        X_graph,
        y_true: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate ensemble model."""
        y_proba = self.predict_proba(X_tabular, X_graph)
        y_pred = (y_proba > 0.5).astype(int)
        
        unique_labels = np.unique(y_true)
        single_class = len(unique_labels) < 2
        
        # Calculate metrics
        if single_class:
            roc_auc = 0.0
            avg_precision = 0.0
            precision_at_90_recall = 0.0
            logger.warning(
                "Single-class evaluation; ranking metrics are undefined",
                label=int(unique_labels[0]) if len(unique_labels) == 1 else None
            )
        else:
            roc_auc = roc_auc_score(y_true, y_proba)
            avg_precision = average_precision_score(y_true, y_proba)
            
            # Precision at 90% recall
            precision, recall, _ = precision_recall_curve(y_true, y_proba)
            precision_at_90_recall = precision[np.argmin(np.abs(recall - 0.9))]
        
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        return {
            'roc_auc': roc_auc,
            'avg_precision': avg_precision,
            'f1_score': f1,
            'precision_at_90_recall': precision_at_90_recall
        }
    
    def tune_weights(
        self,
        X_tabular: pd.DataFrame,
        X_graph,
        y_true: np.ndarray,
        weight_options: Optional[List[float]] = None,
        min_auc_gain: float = 0.0
    ) -> Tuple[float, float]:
        """
        Find optimal XGBoost weight via grid search.
        
        Returns:
            Best (xgb_weight, gat_weight) tuple
        """
        if self.gat_model is None:
            logger.warning("GAT model not loaded; using XGBoost only")
            self.xgb_weight = 1.0
            self.gat_weight = 0.0
            return 1.0, 0.0
        
        if weight_options is None:
            weight_options = [0.5, 0.6, 0.7, 0.8, 0.9]
        weight_options = [w for w in weight_options if 0.0 <= w <= 1.0]
        if not weight_options:
            raise ValueError("weight_options must include values between 0 and 1")
        
        if len(np.unique(y_true)) < 2:
            logger.warning("Single-class labels; defaulting to XGBoost only")
            self.xgb_weight = 1.0
            self.gat_weight = 0.0
            return 1.0, 0.0
        
        xgb_proba = self.predict_proba_xgb(X_tabular)
        gat_proba = self.predict_proba_gat(X_graph)
        if len(gat_proba) != len(xgb_proba):
            raise ValueError("XGBoost and GAT predictions have mismatched lengths")
        
        xgb_auc = roc_auc_score(y_true, xgb_proba)
        
        best_auc = -np.inf
        best_weight = weight_options[0]
        
        for w in weight_options:
            ensemble_proba = w * xgb_proba + (1 - w) * gat_proba
            auc = roc_auc_score(y_true, ensemble_proba)
            
            if auc > best_auc:
                best_auc = auc
                best_weight = w
        
        self.xgb_weight = best_weight
        self.gat_weight = 1 - best_weight
        
        if best_auc <= xgb_auc + min_auc_gain:
            logger.info(
                "GAT did not improve over XGBoost; using XGBoost only",
                xgb_auc=xgb_auc,
                best_auc=best_auc
            )
            self.xgb_weight = 1.0
            self.gat_weight = 0.0
        
        selected_auc = xgb_auc if self.gat_weight == 0.0 else best_auc
        logger.info(
            "Optimal weights found",
            xgb_weight=self.xgb_weight,
            gat_weight=self.gat_weight,
            roc_auc=selected_auc
        )
        
        return self.xgb_weight, self.gat_weight
    
    def log_to_mlflow(
        self,
        metrics: Dict[str, float],
        experiment_name: str = "fraud_detection",
        run_name: str = "ensemble_model"
    ) -> str:
        """Log ensemble model to MLflow."""
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params({
                "model": "ensemble",
                "xgb_weight": self.xgb_weight,
                "gat_weight": self.gat_weight
            })
            
            mlflow.log_metrics(metrics)
            
            return run.info.run_id


# ============================================
# Update __init__.py
# ============================================

# Add to ml/training/__init__.py:
# from .ensemble_model import EnsembleFraudModel
