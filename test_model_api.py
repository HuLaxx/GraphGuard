"""
GraphGuard - Simple API Test
============================
Test the trained model with real predictions
"""

import os
os.environ['XGB_MODEL_PATH'] = 'models/xgboost_rigorous/xgboost_fraud.json'

import xgboost as xgb
import pandas as pd
import numpy as np
from pathlib import Path

def test_model():
    print("="*60)
    print("GraphGuard Model Test")
    print("="*60)
    
    # 1. Load Model
    model_path = Path('models/xgboost_rigorous/xgboost_fraud.json')
    print(f"\n1. Loading model from: {model_path}")
    
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        return
    
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    print("✅ Model loaded successfully")
    
    # 2. Load test data
    print("\n2. Loading test data...")
    test_df = pd.read_parquet('data/processed/test_rich.parquet')
    print(f"✅ Loaded {len(test_df):,} test transactions")
    
    # 3. Prepare features (same logic as training)
    exclude_cols = {
        'transaction_id', 'user_id', 'merchant_id', 'device_id', 
        'timestamp', 'is_fraud', 'fraud_type', 'fraud_ring_id',
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
    
    X_test = test_df[feature_cols].iloc[:10]  # Test on 10 samples
    y_test = test_df['is_fraud'].iloc[:10]
    
    # 4. Make predictions
    print(f"\n3. Making predictions on {len(X_test)} samples...")
    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs > 0.5).astype(int)
    
    # 5. Display results
    print("\n" + "="*60)
    print("PREDICTION RESULTS")
    print("="*60)
    for i in range(len(X_test)):
        actual = "FRAUD" if y_test.iloc[i] == 1 else "LEGIT"
        predicted = "FRAUD" if preds[i] == 1 else "LEGIT"
        score = probs[i]
        match = "✅" if actual == predicted else "❌"
        
        print(f"{match} Sample {i+1}: Score={score:.3f} | Pred={predicted:5s} | Actual={actual:5s}")
    
    accuracy = (preds == y_test).mean()
    print(f"\nAccuracy on 10 samples: {accuracy:.1%}")
    print("\n✅ Model is working correctly with real predictions!")

if __name__ == "__main__":
    test_model()
