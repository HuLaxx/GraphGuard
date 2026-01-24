"""
GraphGuard - Rigorous XGBoost Training
======================================
File: ml/training/train_xgboost_rigorous.py
Phase: 2.2 - Train XGBoost (Rigorous Mode)

Goal: Train a high-performance fraud detection model using:
      - Optuna for Bayesian Hyperparameter Optimization
      - MLflow for experiment tracking
      - Handling of class imbalance
      - Detailed performance evaluation (Precision-Recall, Confusion Matrix)
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
import optuna
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, classification_report,
    average_precision_score
)
import matplotlib.pyplot as plt
import seaborn as sns
import json
import joblib
from pathlib import Path
import os
import shutil

# Set Optuna logging to warnings only
optuna.logging.set_verbosity(optuna.logging.WARNING)

class ModelTrainer:
    def __init__(self, data_dir: Path, model_dir: Path):
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self):
        print("Loading processed datasets...")
        train_df = pd.read_parquet(self.data_dir / 'train_rich.parquet')
        val_df = pd.read_parquet(self.data_dir / 'val_rich.parquet')
        test_df = pd.read_parquet(self.data_dir / 'test_rich.parquet')
        
        # Define features to exclude (IDs, timestamps, raw strings, target)
        exclude_cols = {
            'transaction_id', 'user_id', 'merchant_id', 'device_id', 
            'timestamp', 'is_fraud', 'fraud_type', 'fraud_ring_id', 'fraud_type', # Targets/IDs
            'user_meta_email', 'user_meta_name', 'user_meta_created_at', 'user_meta_preferred_categories', 'user_meta_risk_tier',
            'merchant_meta_name', 'merchant_meta_category', 'merchant_meta_created_at',
            'device_meta_user_agent', 'device_meta_os', 'device_meta_browser', 'device_meta_first_seen',
            'currency', 'ip_address', 'card_last4', 'graph_community_id'
        }
        
        # Dynamically select numeric/boolean features
        # Also drop any object/string columns just to be safe
        feature_cols = [
            c for c in train_df.columns 
            if c not in exclude_cols 
            and not pd.api.types.is_object_dtype(train_df[c])
            and not pd.api.types.is_string_dtype(train_df[c])
        ]
        
        print(f"Training with {len(feature_cols)} features: {feature_cols}")
        
        X_train = train_df[feature_cols]
        y_train = train_df['is_fraud']
        
        X_val = val_df[feature_cols]
        y_val = val_df['is_fraud']
        
        X_test = test_df[feature_cols]
        y_test = test_df['is_fraud']
        
        return X_train, y_train, X_val, y_val, X_test, y_test, feature_cols

    def optimize_hyperparameters(self, X_train, y_train, X_val, y_val, n_trials=20):
        print(f"Optimizing hyperparameters (Trials: {n_trials})...")
        
        # Calculate scale_pos_weight for imbalance
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
        print(f"Computed scale_pos_weight: {scale_pos_weight:.2f}")
        
        def objective(trial):
            params = {
                'verbosity': 0,
                'objective': 'binary:logistic',
                'booster': 'gbtree',
                'tree_method': 'hist',  # Faster training
                'scale_pos_weight': scale_pos_weight,
                'eval_metric': 'auc',
                # Hyperparameters to tune
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 7),
                'gamma': trial.suggest_float('gamma', 0, 0.5),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 1.0, 3.0),
            }
            
            # Train with early stopping
            model = xgb.XGBClassifier(**params, early_stopping_rounds=50)
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            
            # Predict probability on validation
            preds = model.predict_proba(X_val)[:, 1]
            auc = roc_auc_score(y_val, preds)
            
            return auc

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        print(f"Best trial: {study.best_trial.value}")
        print("Best params:", study.best_trial.params)
        
        return study.best_trial.params, scale_pos_weight

    def train_final_model(self, best_params, scale_pos_weight, X_train, y_train, X_val, y_val):
        print("Training final model using best parameters...")
        
        # Add fixed params
        final_params = best_params.copy()
        final_params['objective'] = 'binary:logistic'
        final_params['tree_method'] = 'hist'
        final_params['scale_pos_weight'] = scale_pos_weight
        final_params['eval_metric'] = 'auc'
        
        model = xgb.XGBClassifier(**final_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            verbose=100
        )
        return model

    def evaluate_model(self, model, X_test, y_test, feature_names):
        print("Evaluating model on Test Set...")
        
        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob > 0.5).astype(int) # Default threshold, can be tuned
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        ap = average_precision_score(y_test, y_prob)
        
        print("\n" + "="*40)
        print("FINAL TEST RESULTS (STRICT)")
        print("="*40)
        print(f"Accuracy:  {accuracy:.4f}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        print(f"ROC-AUC:   {auc:.4f}")
        print(f"Avg Prec:  {ap:.4f}")
        print("-" * 40)
        
        # Detailed Report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        
        # Plot Confusion Matrix
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')
        plt.savefig(self.model_dir / 'confusion_matrix.png')
        plt.close()
        
        # Feature Importance
        importance = model.feature_importances_
        feat_imp = pd.DataFrame({'feature': feature_names, 'importance': importance})
        feat_imp = feat_imp.sort_values('importance', ascending=False).head(20)
        
        plt.figure(figsize=(10, 8))
        sns.barplot(x='importance', y='feature', data=feat_imp)
        plt.title('Top 20 Feature Importance')
        plt.tight_layout()
        plt.savefig(self.model_dir / 'feature_importance.png')
        plt.close()
        
        print(f"Top 5 Features:\n{feat_imp.head(5)}")
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "auc": auc,
            "average_precision": ap
        }

def main():
    DATA_DIR = Path('data/processed')
    MODEL_DIR = Path('models/xgboost_rigorous')
    
    # Set up MLflow
    # Use local mlruns directory to avoid docker dependency
    mlflow.set_tracking_uri("file:./mlruns") 
    mlflow.set_experiment("GraphGuard_Rigorous_Training")
    
    trainer = ModelTrainer(DATA_DIR, MODEL_DIR)
    
    # 1. Load Data
    X_train, y_train, X_val, y_val, X_test, y_test, features = trainer.load_data()
    
    with mlflow.start_run(run_name="xgboost_optuna_run"):
        # 2. Hyperparameter Optimization
        best_params, scale_weight = trainer.optimize_hyperparameters(X_train, y_train, X_val, y_val, n_trials=15)
        
        mlflow.log_params(best_params)
        mlflow.log_param("scale_pos_weight", scale_weight)
        
        # 3. Train Final Model
        model = trainer.train_final_model(best_params, scale_weight, X_train, y_train, X_val, y_val)
        
        # 4. Evaluate
        metrics = trainer.evaluate_model(model, X_test, y_test, features)
        mlflow.log_metrics(metrics)
        
        # 5. Log Artifacts
        mlflow.log_artifact(str(MODEL_DIR / 'confusion_matrix.png'))
        mlflow.log_artifact(str(MODEL_DIR / 'feature_importance.png'))
        
        # Save model for serving (JSON format is standard for XGBoost)
        model_path = MODEL_DIR / 'xgboost_fraud.json'
        model.save_model(model_path)
        mlflow.log_artifact(str(model_path))
        
        print(f"\nModel saved to {model_path}")
        print("Done!")

if __name__ == "__main__":
    main()
