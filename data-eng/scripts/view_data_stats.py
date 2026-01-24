"""
Quick script to view generated data statistics
"""
import pandas as pd

# Load datasets
print("Loading datasets...")
transactions = pd.read_parquet('data/transactions.parquet')
users = pd.read_parquet('data/users.parquet')
merchants = pd.read_parquet('data/merchants.parquet')
devices = pd.read_parquet('data/devices.parquet')
fraud_labels = pd.read_parquet('data/fraud_labels.parquet')

print("\n" + "="*60)
print("DATASET STATISTICS")
print("="*60)

print(f"\n📊 Transaction Metrics:")
print(f"  Total transactions: {len(transactions):,}")
print(f"  Legitimate: {(transactions['is_fraud']==0).sum():,} ({(transactions['is_fraud']==0).mean():.1%})")
print(f"  Fraudulent: {(transactions['is_fraud']==1).sum():,} ({(transactions['is_fraud']==1).mean():.1%})")
print(f"  Date range: {transactions['timestamp'].min()} to {transactions['timestamp'].max()}")

print(f"\n💰 Amount Statistics:")
print(f"  Overall mean: ${transactions['amount'].mean():.2f}")
print(f"  Overall median: ${transactions['amount'].median():.2f}")
print(f"  Legit mean: ${transactions[transactions['is_fraud']==0]['amount'].mean():.2f}")
print(f"  Fraud mean: ${transactions[transactions['is_fraud']==1]['amount'].mean():.2f}")

print(f"\n🎯 Fraud Pattern Distribution:")
fraud_txns = transactions[transactions['is_fraud'] == 1]
for pattern, count in fraud_txns['fraud_type'].value_counts().items():
    print(f"  {pattern}: {count:,} ({count/len(fraud_txns):.1%})")

print(f"\n👥 User Metrics:")
print(f"  Total users: {len(users):,}")
print(f"  Avg transactions per user: {len(transactions) / len(users):.1f}")

print(f"\n🏪 Merchant Metrics:")
print(f"  Total merchants: {len(merchants):,}")
print(f"  High-risk merchants: {merchants['is_high_risk'].sum():,}")

print(f"\n📱 Device Metrics:")
print(f"  Total devices: {len(devices):,}")
print(f"  Shared devices: {devices['is_shared'].sum():,} ({devices['is_shared'].mean():.1%})")

print("\n" + "="*60)
print(f"✅ Data generation successful!")
print(f"   Files saved to: data/")
print("="*60)
