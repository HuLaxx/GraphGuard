"""
GraphGuard - Evaluate Saved Model
=================================
File: ml/training/evaluate_saved_model.py

Goal: Load the trained XGBoost model and verify metrics on the test set.
"""

import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report
from pathlib import Path
import json

def main():
    MODEL_PATH = Path('models/xgboost_rigorous/xgboost_fraud.json')
    DATA_DIR = Path('data/processed')
    
    print(f"Loading model from {MODEL_PATH}...")
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    print("Loading test data...")
    test_df = pd.read_parquet(DATA_DIR / 'test_rich.parquet')
    
    # Feature selection logic (copy-paste strict exclusion from training)
    exclude_cols = {
        'transaction_id', 'user_id', 'merchant_id', 'device_id', 
        'timestamp', 'is_fraud', 'fraud_type', 'fraud_ring_id', 'fraud_type',
        'user_meta_email', 'user_meta_name', 'user_meta_created_at', 'user_meta_preferred_categories', 'user_meta_risk_tier',
        'merchant_meta_name', 'merchant_meta_category', 'merchant_meta_created_at',
        'device_meta_user_agent', 'device_meta_os', 'device_meta_browser', 'device_meta_first_seen',
        'currency', 'ip_address', 'card_last4', 'graph_community_id'
    }
    
    feature_cols = [
        c for c in test_df.columns 
        if c not in exclude_cols 
        and not pd.api.types.is_object_dtype(test_df[c])
        and not pd.api.types.is_string_dtype(test_df[c])
    ]
    
    print(f"Evaluating on {len(feature_cols)} features.")
    X_test = test_df[feature_cols]
    y_test = test_df['is_fraud']
    
    # Predict
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob > 0.5).astype(int)
    
    # Metrics
    auc = roc_auc_score(y_test, y_prob)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print("\n" + "="*40)
    print("STRICT TEST EVALUATION")
    print("="*40)
    print(f"ROC-AUC:   {auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print("-" * 40)
    
    # Verify High Quality
    if auc > 0.95:
        print("✅ PASSED: Excellent Model (AUC > 0.95)")
    elif auc > 0.90:
        print("⚠️ WARNING: Good Model (AUC > 0.90), but maybe not 'Best'")
    else:
        print("❌ FAILED: Suboptimal Model (AUC < 0.90)")

if __name__ == "__main__":
    main()
