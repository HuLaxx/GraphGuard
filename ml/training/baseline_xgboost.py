"""
GraphGuard - XGBoost Baseline Model
=====================================
File: ml/training/baseline_xgboost.py
Reference: Specification.md Lines 1380-1486

Goal: Train XGBoost baseline model for fraud detection.

Key Implementation Details:
- Load features from Feast offline store
- Temporal train/test split (not random - prevents data leakage)
- Handle imbalance with SMOTE + scale_pos_weight
- Early stopping on validation set
- Log to MLflow

Gotchas (from spec):
- Use scale_pos_weight for class imbalance, not just SMOTE
- eval_metric='aucpr' better than 'auc' for imbalanced data
- Temporal split (not random) prevents data leakage
"""

from typing import Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    classification_report, roc_auc_score, 
    precision_recall_curve, average_precision_score,
    confusion_matrix, f1_score
)
from imblearn.over_sampling import SMOTE
import mlflow
import mlflow.xgboost
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Feature Configuration
# ============================================

FEATURE_COLUMNS = [
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
    # Graph features (from Neo4j)
    'pagerank', 'community_id', 'betweenness',
    'degree', 'out_degree', 'in_degree',
    # Velocity features
    'rapid_fire_flag', 'high_value_flag', 'amount_pct_of_daily',
    # Raw transaction amount
    'amount',
]


# ============================================
# Model Trainer Class
# ============================================

class XGBoostFraudModel:
    """
    XGBoost baseline model for fraud detection.
    Reference: Specification.md Lines 1380-1486
    """
    
    def __init__(
        self,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        n_estimators: int = 200,
        smote_ratio: float = 0.1,
        random_state: int = 42
    ):
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.smote_ratio = smote_ratio
        self.random_state = random_state
        
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_columns = FEATURE_COLUMNS
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        split_date: str = '2024-06-01',
        val_fraction: float = 0.1
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Prepare data with temporal train/val/test split.
        Gotcha: Temporal split prevents data leakage.
        
        Args:
            df: DataFrame with features and 'fraud' label
            split_date: Date to split train/test
        
        Returns:
            X_train, X_val, X_test, y_train, y_val, y_test
        """
        # Ensure timestamp column exists
        if 'timestamp' not in df.columns and 'date' not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' or 'date' column")
        
        date_col = 'timestamp' if 'timestamp' in df.columns else 'date'
        
        # Temporal split
        train_mask = pd.to_datetime(df[date_col]) < pd.to_datetime(split_date)

        train_df = df[train_mask].copy()
        test_df = df[~train_mask].copy()

        # Sort train data by time and split off validation tail
        train_df = train_df.sort_values(date_col)
        val_size = 0
        if len(train_df) > 1:
            val_size = max(1, int(len(train_df) * val_fraction))

        if val_size > 0:
            val_df = train_df.iloc[-val_size:]
            train_df = train_df.iloc[:-val_size]
        else:
            val_df = train_df.iloc[0:0]

        # Select features
        available_features = [c for c in self.feature_columns if c in df.columns]

        def _prepare_features(frame: pd.DataFrame) -> pd.DataFrame:
            X_frame = frame[available_features].copy()
            for col in X_frame.select_dtypes(include=['bool']).columns:
                X_frame[col] = X_frame[col].astype(int)
            return X_frame.fillna(0)

        X_train = _prepare_features(train_df)
        X_val = _prepare_features(val_df)
        X_test = _prepare_features(test_df)

        y_train = train_df['fraud'].copy()
        y_val = val_df['fraud'].copy()
        y_test = test_df['fraud'].copy()
        
        logger.info(
            "Data prepared",
            train_size=len(X_train),
            val_size=len(X_val),
            test_size=len(X_test),
            train_fraud_rate=y_train.mean(),
            val_fraud_rate=y_val.mean() if len(y_val) > 0 else 0.0,
            test_fraud_rate=y_test.mean(),
            features=len(available_features)
        )

        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def apply_smote(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Apply SMOTE to handle class imbalance.
        Reference: Specification.md Lines 1418-1420
        
        Gotcha: Only apply SMOTE to training data, not test data.
        """
        if self.smote_ratio <= 0:
            logger.info("SMOTE skipped", reason="smote_ratio<=0")
            return X_train, y_train

        minority = int((y_train == 1).sum())
        majority = int((y_train == 0).sum())
        current_ratio = minority / max(majority, 1)

        if minority < 2 or majority < 1:
            logger.info("SMOTE skipped", reason="insufficient class samples", minority=minority, majority=majority)
            return X_train, y_train

        # If requested ratio is below current, treat it as a boost amount.
        target_ratio = self.smote_ratio
        if target_ratio < current_ratio:
            target_ratio = min(1.0, current_ratio + self.smote_ratio)

        k_neighbors = min(5, minority - 1)
        if k_neighbors < 1:
            logger.info("SMOTE skipped", reason="k_neighbors<1", minority=minority)
            return X_train, y_train

        smote = SMOTE(
            sampling_strategy=target_ratio,
            random_state=self.random_state,
            k_neighbors=k_neighbors
        )

        X_balanced, y_balanced = smote.fit_resample(X_train, y_train)
        
        logger.info(
            "SMOTE applied",
            original_size=len(X_train),
            balanced_size=len(X_balanced),
            original_fraud_rate=y_train.mean(),
            balanced_fraud_rate=y_balanced.mean()
        )
        
        return pd.DataFrame(X_balanced, columns=X_train.columns), pd.Series(y_balanced)
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        apply_smote: bool = True,
        early_stopping_rounds: int = 20
    ) -> xgb.XGBClassifier:
        """
        Train XGBoost model.
        Reference: Specification.md Lines 1422-1443
        """
        # Apply SMOTE if requested
        if apply_smote:
            X_train, y_train = self.apply_smote(X_train, y_train)
        
        # Calculate class weight
        # Gotcha: Use BOTH scale_pos_weight AND SMOTE
        scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        
        self.model = xgb.XGBClassifier(
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            n_estimators=self.n_estimators,
            scale_pos_weight=scale_pos_weight,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=1,
            reg_lambda=10,
            random_state=self.random_state,
            eval_metric='aucpr',  # Gotcha: Better than 'auc' for imbalanced
            verbosity=1
        )
        
        # Train with early stopping
        fit_kwargs: Dict[str, Any] = {
            "eval_set": [(X_val, y_val)],
            "verbose": 10
        }
        if early_stopping_rounds and early_stopping_rounds > 0:
            fit_kwargs["early_stopping_rounds"] = early_stopping_rounds
        
        self.model.fit(X_train, y_train, **fit_kwargs)
        
        logger.info(
            "Model trained",
            best_iteration=self.model.best_iteration if hasattr(self.model, 'best_iteration') else self.n_estimators,
            n_features=len(X_train.columns)
        )
        
        return self.model
    
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Evaluate model performance.
        Reference: Specification.md Lines 1445-1458
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba > threshold).astype(int)
        
        unique_labels = np.unique(y_test)
        single_class = len(unique_labels) < 2
        
        # Calculate metrics
        if single_class:
            roc_auc = 0.0
            avg_precision = 0.0
            precision_at_90_recall = 0.0
            recall_at_90_precision = 0.0
            logger.warning(
                "Single-class evaluation; ranking metrics are undefined",
                label=int(unique_labels[0]) if len(unique_labels) == 1 else None
            )
        else:
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            avg_precision = average_precision_score(y_test, y_pred_proba)
            
            # Precision at 90% recall
            precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
            precision_at_90_recall = precision[np.argmin(np.abs(recall - 0.9))]
            
            # Recall at 90% precision
            recall_at_90_precision = recall[np.argmin(np.abs(precision - 0.9))]
        
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # Confusion matrix (force 2x2 for consistency)
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        
        metrics = {
            'roc_auc': roc_auc,
            'avg_precision': avg_precision,
            'f1_score': f1,
            'precision_at_90_recall': precision_at_90_recall,
            'recall_at_90_precision': recall_at_90_precision,
            'confusion_matrix': cm.tolist()
        }
        
        logger.info("Model evaluated", **{k: v for k, v in metrics.items() if k != 'confusion_matrix'})
        
        # Print classification report
        print(classification_report(
            y_test,
            y_pred,
            labels=[0, 1],
            target_names=['Legitimate', 'Fraud'],
            zero_division=0
        ))
        
        return metrics
    
    def log_to_mlflow(
        self,
        metrics: Dict[str, Any],
        experiment_name: str = "fraud_detection",
        run_name: str = "xgboost_baseline"
    ) -> str:
        """
        Log model and metrics to MLflow.
        Reference: Specification.md Lines 1460-1481
        """
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=run_name) as run:
            # Log parameters
            mlflow.log_params({
                "model": "xgboost",
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "n_estimators": self.n_estimators,
                "smote_ratio": self.smote_ratio
            })
            
            # Log metrics
            mlflow.log_metrics({
                "roc_auc": metrics['roc_auc'],
                "avg_precision": metrics['avg_precision'],
                "f1_score": metrics['f1_score'],
                "precision_at_90_recall": metrics['precision_at_90_recall'],
                "recall_at_90_precision": metrics['recall_at_90_precision']
            })
            
            # Log model
            if self.model is not None:
                mlflow.xgboost.log_model(self.model, "model")
            
            logger.info(
                "Logged to MLflow",
                run_id=run.info.run_id,
                experiment=experiment_name
            )
            
            return run.info.run_id
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance from trained model."""
        if self.model is None:
            raise ValueError("Model not trained")
        
        importance = self.model.feature_importances_
        feature_names = self.model.feature_names_in_
        
        return pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
    
    def save(self, path: str) -> None:
        """Save model to disk."""
        if self.model is not None:
            self.model.save_model(path)
            logger.info("Model saved", path=path)
    
    def load(self, path: str) -> None:
        """Load model from disk."""
        self.model = xgb.XGBClassifier()
        self.model.load_model(path)
        logger.info("Model loaded", path=path)


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train XGBoost fraud detection model")
    parser.add_argument("--input", required=True, help="Input features Parquet path")
    parser.add_argument("--output", default="./model.json", help="Output model path")
    parser.add_argument("--split-date", default="2024-06-01", help="Train/test split date")
    parser.add_argument("--mlflow-tracking", default="http://localhost:5000", help="MLflow tracking URI")
    args = parser.parse_args()
    
    # Set MLflow tracking
    mlflow.set_tracking_uri(args.mlflow_tracking)
    
    # Load data
    df = pd.read_parquet(args.input)
    print(f"Loaded {len(df)} rows with {len(df.columns)} columns")
    
    # Train model
    trainer = XGBoostFraudModel()
    X_train, X_val, X_test, y_train, y_val, y_test = trainer.prepare_data(df, args.split_date)
    trainer.train(X_train, y_train, X_val, y_val)
    
    # Evaluate
    metrics = trainer.evaluate(X_test, y_test)
    print(f"\nROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"Average Precision: {metrics['avg_precision']:.4f}")
    
    # Log to MLflow
    trainer.log_to_mlflow(metrics)
    
    # Save model
    trainer.save(args.output)
    
    # Show feature importance
    print("\nTop 10 Features:")
    print(trainer.get_feature_importance().head(10))
