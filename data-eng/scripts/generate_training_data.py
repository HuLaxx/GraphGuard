"""
GraphGuard - Synthetic Training Data Generator
==============================================
File: data-eng/scripts/generate_training_data.py
Phase: 1.1 - Data Foundation

Goal: Generate realistic transaction dataset with fraud patterns for model training.

Output:
- 100,000+ transactions (70% legitimate, 30% fraud)
- 5,000 users with behavioral profiles
- 500 merchants with industry categories
- 3,000 devices with sharing patterns
- Realistic fraud patterns:
  * Account takeover (rapid high-value)
  * Card testing (multiple small amounts)
  * Fraud rings (connected users/devices)
  * Velocity abuse (unusual frequency)
"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib

import pandas as pd
import numpy as np
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)


# ============================================
# Configuration
# ============================================

class Config:
    """Data generation configuration."""
    
    # Counts
    NUM_USERS = 5000
    NUM_MERCHANTS = 500
    NUM_DEVICES = 3000
    NUM_TRANSACTIONS = 100000
    
    # Fraud ratios
    FRAUD_RATE = 0.30  # 30% fraud
    
    # Fraud pattern distributions
    FRAUD_PATTERNS = {
        'account_takeover': 0.25,    # High-value rapid transactions
        'card_testing': 0.20,        # Multiple small transactions
        'fraud_ring': 0.30,          # Connected users/devices
        'velocity_abuse': 0.15,      # Unusual frequency
        'random_fraud': 0.10         # Random suspicious activity
    }
    
    # Transaction amounts (USD)
    LEGIT_AMOUNT_MEAN = 85
    LEGIT_AMOUNT_STD = 120
    FRAUD_AMOUNT_MEAN = 450
    FRAUD_AMOUNT_STD = 800
    
    # Merchant categories with fraud rates
    MERCHANT_CATEGORIES = {
        'electronics': 0.35,
        'fashion': 0.15,
        'groceries': 0.05,
        'travel': 0.40,
        'entertainment': 0.20,
        'jewelry': 0.50,
        'home_goods': 0.12,
        'restaurants': 0.08,
        'gas_stations': 0.06,
        'pharmacies': 0.04
    }


# ============================================
# Entity Generators
# ============================================

def generate_users(num_users: int) -> pd.DataFrame:
    """Generate user profiles with behavioral attributes."""
    
    users = []
    
    for i in range(num_users):
        # User risk profile
        risk_tier = random.choices(
            ['low_risk', 'medium_risk', 'high_risk'],
            weights=[0.70, 0.25, 0.05]
        )[0]
        
        user = {
            'user_id': f'user_{i+1:05d}',
            'email': fake.email(),
            'name': fake.name(),
            'created_at': fake.date_time_between(start_date='-3y', end_date='-1y'),
            'risk_tier': risk_tier,
            'avg_txn_amount': np.random.lognormal(4.2, 0.8),  # ~$80 avg
            'txn_frequency_days': random.uniform(1, 30),  # Days between transactions
            'preferred_categories': random.sample(list(Config.MERCHANT_CATEGORIES.keys()), k=random.randint(2, 5))
        }
        
        users.append(user)
    
    return pd.DataFrame(users)


def generate_merchants(num_merchants: int) -> pd.DataFrame:
    """Generate merchant profiles with fraud rates."""
    
    merchants = []
    
    for i in range(num_merchants):
        category = random.choice(list(Config.MERCHANT_CATEGORIES.keys()))
        base_fraud_rate = Config.MERCHANT_CATEGORIES[category]
        
        merchant = {
            'merchant_id': f'merchant_{i+1:04d}',
            'name': fake.company(),
            'category': category,
            'base_fraud_rate': base_fraud_rate,
            'avg_transaction_amount': np.random.lognormal(4.0, 1.0),
            'created_at': fake.date_time_between(start_date='-5y', end_date='-6m'),
            'is_high_risk': base_fraud_rate > 0.3
        }
        
        merchants.append(merchant)
    
    return pd.DataFrame(merchants)


def generate_devices(num_devices: int) -> pd.DataFrame:
    """Generate device fingerprints with sharing patterns."""
    
    devices = []
    
    for i in range(num_devices):
        # Some devices are shared (fraud indicator)
        is_shared = random.random() < 0.15  # 15% shared devices
        
        device = {
            'device_id': f'device_{hashlib.md5(str(i).encode()).hexdigest()[:16]}',
            'user_agent': fake.user_agent(),
            'os': random.choice(['iOS', 'Android', 'Windows', 'MacOS', 'Linux']),
            'browser': random.choice(['Chrome', 'Safari', 'Firefox', 'Edge']),
            'first_seen': fake.date_time_between(start_date='-2y', end_date='-1m'),
            'is_shared': is_shared,
            'expected_users': random.randint(2, 5) if is_shared else 1
        }
        
        devices.append(device)
    
    return pd.DataFrame(devices)


# ============================================
# Fraud Pattern Generators
# ============================================

class FraudPatternGenerator:
    """Generate transactions with specific fraud patterns."""
    
    def __init__(self, users: pd.DataFrame, merchants: pd.DataFrame, devices: pd.DataFrame):
        self.users = users
        self.merchants = merchants
        self.devices = devices
        self.fraud_rings = self._create_fraud_rings()
    
    def _create_fraud_rings(self) -> List[Dict]:
        """Create fraud rings (connected users using shared devices)."""
        rings = []
        
        # Create 20 fraud rings
        for ring_id in range(20):
            ring_size = random.randint(3, 8)
            ring_users = self.users.sample(n=ring_size)['user_id'].tolist()
            ring_devices = self.devices[self.devices['is_shared']].sample(n=min(3, len(ring_users)))['device_id'].tolist()
            
            rings.append({
                'ring_id': f'ring_{ring_id:02d}',
                'users': ring_users,
                'devices': ring_devices,
                'active': True
            })
        
        return rings
    
    def account_takeover(self, timestamp: datetime) -> Dict:
        """Generate account takeover pattern: rapid high-value transactions."""
        user = self.users.sample(n=1).iloc[0]
        device = self.devices[~self.devices['device_id'].isin([user['user_id']])].sample(n=1).iloc[0]  # New device
        merchant = self.merchants[self.merchants['is_high_risk']].sample(n=1).iloc[0]
        
        return {
            'user_id': user['user_id'],
            'merchant_id': merchant['merchant_id'],
            'device_id': device['device_id'],
            'amount': np.random.lognormal(6.5, 0.5),  # High value: $500-$2000
            'is_fraud': 1,
            'fraud_type': 'account_takeover',
            'timestamp': timestamp,
            'ip_address': fake.ipv4(),
            'card_last4': str(random.randint(1000, 9999))
        }
    
    def card_testing(self, timestamp: datetime) -> List[Dict]:
        """Generate card testing pattern: multiple small amounts in quick succession."""
        user = self.users.sample(n=1).iloc[0]
        device = self.devices.sample(n=1).iloc[0]
        num_tests = random.randint(5, 15)
        
        transactions = []
        for i in range(num_tests):
            merchant = self.merchants.sample(n=1).iloc[0]
            
            txn = {
                'user_id': user['user_id'],
                'merchant_id': merchant['merchant_id'],
                'device_id': device['device_id'],
                'amount': round(random.uniform(1.0, 10.0), 2),  # Small amounts
                'is_fraud': 1,
                'fraud_type': 'card_testing',
                'timestamp': timestamp + timedelta(minutes=i*2),
                'ip_address': fake.ipv4(),
                'card_last4': str(random.randint(1000, 9999))
            }
            transactions.append(txn)
        
        return transactions
    
    def fraud_ring_transaction(self, timestamp: datetime) -> Dict:
        """Generate fraud ring transaction: connected users/devices."""
        ring = random.choice(self.fraud_rings)
        user_id = random.choice(ring['users'])
        device_id = random.choice(ring['devices'])
        merchant = self.merchants[self.merchants['is_high_risk']].sample(n=1).iloc[0]
        
        return {
            'user_id': user_id,
            'merchant_id': merchant['merchant_id'],
            'device_id': device_id,
            'amount': np.random.lognormal(5.8, 0.8),  # $200-$800
            'is_fraud': 1,
            'fraud_type': 'fraud_ring',
            'fraud_ring_id': ring['ring_id'],
            'timestamp': timestamp,
            'ip_address': fake.ipv4(),
            'card_last4': str(random.randint(1000, 9999))
        }
    
    def velocity_abuse(self, timestamp: datetime) -> List[Dict]:
        """Generate velocity abuse: unusual transaction frequency."""
        user = self.users.sample(n=1).iloc[0]
        device = self.devices.sample(n=1).iloc[0]
        num_txns = random.randint(10, 25)  # Many transactions in short time
        
        transactions = []
        for i in range(num_txns):
            merchant = self.merchants.sample(n=1).iloc[0]
            
            txn = {
                'user_id': user['user_id'],
                'merchant_id': merchant['merchant_id'],
                'device_id': device['device_id'],
                'amount': np.random.lognormal(4.5, 0.6),
                'is_fraud': 1,
                'fraud_type': 'velocity_abuse',
                'timestamp': timestamp + timedelta(minutes=i*5),
                'ip_address': fake.ipv4(),
                'card_last4': str(random.randint(1000, 9999))
            }
            transactions.append(txn)
        
        return transactions
    
    def legitimate_transaction(self, timestamp: datetime) -> Dict:
        """Generate legitimate transaction."""
        user = self.users.sample(n=1).iloc[0]
        
        # Choose merchant from user's preferred categories
        preferred_cats = user['preferred_categories']
        merchant = self.merchants[self.merchants['category'].isin(preferred_cats)].sample(n=1).iloc[0]
        
        # Use consistent device for user
        device = self.devices.sample(n=1).iloc[0]
        
        return {
            'user_id': user['user_id'],
            'merchant_id': merchant['merchant_id'],
            'device_id': device['device_id'],
            'amount': max(5.0, np.random.lognormal(4.4, 0.7)),  # $50-$150 typically
            'is_fraud': 0,
            'fraud_type': None,
            'timestamp': timestamp,
            'ip_address': fake.ipv4(),
            'card_last4': str(random.randint(1000, 9999))
        }


# ============================================
# Main Generation Logic
# ============================================

def generate_transactions(
    num_transactions: int,
    users: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame
) -> pd.DataFrame:
    """Generate complete transaction dataset."""
    
    print(f"Generating {num_transactions:,} transactions...")
    
    fraud_gen = FraudPatternGenerator(users, merchants, devices)
    
    # Calculate fraud counts by pattern
    num_fraud = int(num_transactions * Config.FRAUD_RATE)
    num_legit = num_transactions - num_fraud
    
    pattern_counts = {
        pattern: int(num_fraud * ratio)
        for pattern, ratio in Config.FRAUD_PATTERNS.items()
    }
    
    print(f"  Legitimate: {num_legit:,}")
    print(f"  Fraud: {num_fraud:,}")
    for pattern, count in pattern_counts.items():
        print(f"    - {pattern}: {count:,}")
    
    transactions = []
    
    # Start date: 1 year ago
    start_date = datetime.now() - timedelta(days=365)
    
    # Generate legitimate transactions
    print("\nGenerating legitimate transactions...")
    for i in range(num_legit):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))  # Random time in year
        txn = fraud_gen.legitimate_transaction(timestamp)
        transactions.append(txn)
    
    # Generate fraud patterns
    print("Generating fraud patterns...")
    
    # Account takeovers (single high-value txns)
    for i in range(pattern_counts['account_takeover']):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
        txn = fraud_gen.account_takeover(timestamp)
        transactions.append(txn)
    
    # Card testing (bursts of small txns)
    num_bursts = pattern_counts['card_testing'] // 10  # Each burst ~10 txns
    for i in range(num_bursts):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
        txns = fraud_gen.card_testing(timestamp)
        transactions.extend(txns)
    
    # Fraud rings
    for i in range(pattern_counts['fraud_ring']):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
        txn = fraud_gen.fraud_ring_transaction(timestamp)
        transactions.append(txn)
    
    # Velocity abuse (bursts of many txns)
    num_bursts = pattern_counts['velocity_abuse'] // 15  # Each burst ~15 txns
    for i in range(num_bursts):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
        txns = fraud_gen.velocity_abuse(timestamp)
        transactions.extend(txns)
    
    # Random fraud (fill remainder)
    remaining = num_fraud - len([t for t in transactions if t.get('is_fraud')])
    for i in range(remaining):
        timestamp = start_date + timedelta(minutes=random.randint(0, 525600))
        txn = fraud_gen.account_takeover(timestamp)  # Use ATO as default
        txn['fraud_type'] = 'random_fraud'
        transactions.append(txn)
    
    # Convert to DataFrame
    df = pd.DataFrame(transactions)
    
    # Add transaction IDs
    df['transaction_id'] = [f'txn_{i:08d}' for i in range(len(df))]
    
    # Add currency
    df['currency'] = 'USD'
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"\nGenerated {len(df):,} total transactions")
    print(f"Fraud rate: {df['is_fraud'].mean():.1%}")
    
    return df


def save_datasets(
    transactions: pd.DataFrame,
    users: pd.DataFrame,
    merchants: pd.DataFrame,
    devices: pd.DataFrame,
    output_dir: Path
):
    """Save all datasets to parquet files."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSaving datasets to {output_dir}/...")
    
    transactions.to_parquet(output_dir / 'transactions.parquet', index=False)
    print(f"  ✓ transactions.parquet ({len(transactions):,} rows)")
    
    users.to_parquet(output_dir / 'users.parquet', index=False)
    print(f"  ✓ users.parquet ({len(users):,} rows)")
    
    merchants.to_parquet(output_dir / 'merchants.parquet', index=False)
    print(f"  ✓ merchants.parquet ({len(merchants):,} rows)")
    
    devices.to_parquet(output_dir / 'devices.parquet', index=False)
    print(f"  ✓ devices.parquet ({len(devices):,} rows)")
    
    # Create fraud labels file (for easy model training)
    fraud_labels = transactions[['transaction_id', 'is_fraud', 'fraud_type']].copy()
    fraud_labels.to_parquet(output_dir / 'fraud_labels.parquet', index=False)
    print(f"  ✓ fraud_labels.parquet ({len(fraud_labels):,} rows)")
    
    print("\n✅ All datasets saved successfully!")


def print_statistics(transactions: pd.DataFrame, users: pd.DataFrame, merchants: pd.DataFrame, devices: pd.DataFrame):
    """Print dataset statistics."""
    
    print("\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    
    print(f"\n📊 Transaction Metrics:")
    print(f"  Total transactions: {len(transactions):,}")
    print(f"  Legitimate: {(~transactions['is_fraud'].astype(bool)).sum():,} ({(~transactions['is_fraud'].astype(bool)).mean():.1%})")
    print(f"  Fraudulent: {transactions['is_fraud'].sum():,} ({transactions['is_fraud'].mean():.1%})")
    print(f"  Date range: {transactions['timestamp'].min()} to {transactions['timestamp'].max()}")
    
    print(f"\n💰 Amount Statistics:")
    print(f"  Overall mean: ${transactions['amount'].mean():.2f}")
    print(f"  Overall median: ${transactions['amount'].median():.2f}")
    print(f"  Legit mean: ${transactions[transactions['is_fraud']==0]['amount'].mean():.2f}")
    print(f"  Fraud mean: ${transactions[transactions['is_fraud']==1]['amount'].mean():.2f}")
    
    print(f"\n🎯 Fraud Pattern Distribution:")
    fraud_txns = transactions[transactions['is_fraud'] == 1]
    for pattern in fraud_txns['fraud_type'].value_counts().items():
        print(f"  {pattern[0]}: {pattern[1]:,} ({pattern[1]/len(fraud_txns):.1%})")
    
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


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic fraud detection training data')
    parser.add_argument('--output', type=str, default='data', help='Output directory')
    parser.add_argument('--transactions', type=int, default=Config.NUM_TRANSACTIONS, help='Number of transactions')
    parser.add_argument('--users', type=int, default=Config.NUM_USERS, help='Number of users')
    parser.add_argument('--merchants', type=int, default=Config.NUM_MERCHANTS, help='Number of merchants')
    parser.add_argument('--devices', type=int, default=Config.NUM_DEVICES, help='Number of devices')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    
    print("="*60)
    print("GraphGuard Synthetic Data Generator")
    print("="*60)
    
    # Generate entities
    print("\n📋 Generating entities...")
    users = generate_users(args.users)
    merchants = generate_merchants(args.merchants)
    devices = generate_devices(args.devices)
    
    # Generate transactions
    transactions = generate_transactions(args.transactions, users, merchants, devices)
    
    # Save datasets
    save_datasets(transactions, users, merchants, devices, output_dir)
    
    # Print statistics
    print_statistics(transactions, users, merchants, devices)
    
    print(f"\n✨ Data generation complete! Files saved to: {output_dir.absolute()}")


if __name__ == '__main__':
    main()
