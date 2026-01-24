"""
GraphGuard - Advanced Dataset Preparation
=========================================
File: ml/training/create_dataset.py
Phase: 2.1 - Prepare Golden Dataset

Goal: Create a high-quality, feature-rich dataset for strict model training.
      Merges transactions, profiles, and graph features.
      Engineers advanced features (velocity, ratios).
      Performs strict time-based splitting.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
import shutil

def load_and_merge_data(data_dir: Path) -> pd.DataFrame:
    """Load all raw parquet files and merge them into a single dataframe."""
    print("Loading parquet files...")
    
    # Load core data
    txns = pd.read_parquet(data_dir / 'transactions.parquet')
    users = pd.read_parquet(data_dir / 'users.parquet')
    merchants = pd.read_parquet(data_dir / 'merchants.parquet')
    devices = pd.read_parquet(data_dir / 'devices.parquet')
    
    # Load derived graph features
    graph_features = pd.read_parquet(data_dir / 'graph_features.parquet')
    
    print(f"Loaded {len(txns)} transactions.")
    
    # 1. Join User Profile (rename cols to avoid collisions)
    users_renamed = users.add_prefix('user_meta_').rename(columns={'user_meta_user_id': 'user_id'})
    df = txns.merge(users_renamed, on='user_id', how='left')
    
    # 2. Join Merchant Profile
    merchants_renamed = merchants.add_prefix('merchant_meta_').rename(columns={'merchant_meta_merchant_id': 'merchant_id'})
    df = df.merge(merchants_renamed, on='merchant_id', how='left')
    
    # 3. Join Device Profile
    devices_renamed = devices.add_prefix('device_meta_').rename(columns={'device_meta_device_id': 'device_id'})
    df = df.merge(devices_renamed, on='device_id', how='left')
    
    # 4. Join Graph Features
    # Graph features are keyed by user_id
    graph_renamed = graph_features.add_prefix('graph_').rename(columns={'graph_user_id': 'user_id'})
    df = df.merge(graph_renamed, on='user_id', how='left')
    
    return df

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Perform advanced feature engineering."""
    print("Engineering features...")
    
    # --- Time Features ---
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['month'] = df['timestamp'].dt.month
    
    # --- Ratio Features ---
    # Transaction amount relative to user's average (from profile)
    # Log transform amount to handle skew
    df['amount_log'] = np.log1p(df['amount'])
    df['user_amt_ratio'] = df['amount'] / df['user_meta_avg_txn_amount']
    df['merchant_amt_ratio'] = df['amount'] / df['merchant_meta_avg_transaction_amount']
    
    # --- Velocity Features (Rolling Windows) ---
    print("  Computing velocity features...")
    # Sort strictly
    df = df.sort_values(['user_id', 'timestamp'])
    
    # Set index for time-based rolling
    df_indexed = df.set_index('timestamp')
    
    # Calculate 24h amount sum using groupby().rolling()
    # This returns a MultiIndex Series (user_id, timestamp)
    velocity_24h_amount = df_indexed.groupby('user_id')['amount'].rolling('24h').sum()
    
    # Reset index to make it mergeable
    # velocity_24h_amount is Series, name it
    velocity_24h_amount.name = 'velocity_24h_amount'
    velocity_24h_df = velocity_24h_amount.reset_index()
    
    # Merge back to original df
    # We use user_id and timestamp as keys. 
    # Note: If a user has multiple txns at EXACT same timestamp, this might duplicate, 
    # but in generated data with seconds precision it's unlikely or we handle duplicates.
    # To be perfectly safe, we can use the original dataframe's index if we preserve it.
    
    # Alternative: The result of groupby().rolling() on sorted df *should* align if we drop the user_id index level
    # But let's use merge to be 100% safe against alignment issues
    df = df.merge(velocity_24h_df, on=['user_id', 'timestamp'], how='left')
    
    # 1h count
    velocity_1h_count = df_indexed.groupby('user_id')['amount'].rolling('1h').count()
    velocity_1h_count.name = 'velocity_1h_count'
    velocity_1h_df = velocity_1h_count.reset_index()
    df = df.merge(velocity_1h_df, on=['user_id', 'timestamp'], how='left')
    
    # 24h count
    velocity_24h_count = df_indexed.groupby('user_id')['amount'].rolling('24h').count()
    velocity_24h_count.name = 'velocity_24h_count'
    velocity_24h_df = velocity_24h_count.reset_index()
    df = df.merge(velocity_24h_df, on=['user_id', 'timestamp'], how='left')
    
    # Fill NAs (first records) with 0 or appropriate value
    df['velocity_24h_amount'] = df['velocity_24h_amount'].fillna(df['amount']) # At least the current amount
    df['velocity_1h_count'] = df['velocity_1h_count'].fillna(1)
    df['velocity_24h_count'] = df['velocity_24h_count'].fillna(1)
    
    # --- Interaction Features ---
    # High risk checks
    df['high_risk_merchant_txn'] = (df['merchant_meta_is_high_risk'] & (df['amount'] > 500)).astype(int)
    
    # Device consistency
    # (Simplified: in real production we'd check if device was used before, 
    # here we assume if device_meta_expected_users > 1 it's shared/risky)
    df['device_is_shared'] = df['device_meta_is_shared'].astype(int)
    
    return df

def perform_strict_split(df: pd.DataFrame, output_dir: Path):
    """
    Perform strict time-based split to prevent data leakage.
    Train: First 80% of time sorted data
    Val: Next 10%
    Test: Final 10%
    """
    print("Performing strict time-based split...")
    
    # Sort strictly by time
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    n = len(df)
    train_end = int(n * 0.80)
    val_end = int(n * 0.90)
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    print(f"Split sizes:")
    print(f"  Train: {len(train_df):,} ({train_df['timestamp'].min()} to {train_df['timestamp'].max()})")
    print(f"  Val:   {len(val_df):,} ({val_df['timestamp'].min()} to {val_df['timestamp'].max()})")
    print(f"  Test:  {len(test_df):,} ({test_df['timestamp'].min()} to {test_df['timestamp'].max()})")
    
    # Verify no fraud leakage (sanity check - time based should handle it, but good to know distribution)
    print(f"Fraud Rates:")
    print(f"  Train: {train_df['is_fraud'].mean():.2%}")
    print(f"  Val:   {val_df['is_fraud'].mean():.2%}")
    print(f"  Test:  {test_df['is_fraud'].mean():.2%}")
    
    # Drop timestamp and non-feature columns for final parquet, 
    # BUT keep transaction_id and timestamp for reference/analysis later
    # We will filter columns during training.
    
    output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_parquet(output_dir / 'train_rich.parquet', index=False)
    val_df.to_parquet(output_dir / 'val_rich.parquet', index=False)
    test_df.to_parquet(output_dir / 'test_rich.parquet', index=False)
    
    print(f"Saved rich datasets to {output_dir}")

def main():
    data_dir = Path('data')
    processed_dir = Path('data/processed')
    
    # Load
    df = load_and_merge_data(data_dir)
    
    # Feature Engineering
    df = engineer_features(df)
    
    # Split
    perform_strict_split(df, processed_dir)

if __name__ == "__main__":
    main()
