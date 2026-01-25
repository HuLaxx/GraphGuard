"""
GraphGuard - Neo4j Graph Loader
================================
File: data-eng/neo4j/load_graph.py
Phase: 1.2 - Build Transaction Graph

Goal: Load transactions into Neo4j and create graph relationships.

Nodes:
- User
- Merchant  
- Device

Relationships:
- (User)-[TRANSACTED_WITH]->(Merchant)
- (User)-[USED_DEVICE]->(Device)
"""

import os
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase
from tqdm import tqdm


class GraphLoader:
    """Load transaction data into Neo4j graph."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships."""
        print("Clearing existing graph...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Graph cleared")
    
    def create_constraints(self):
        """Create uniqueness constraints for performance."""
        print("Creating constraints...")
        with self.driver.session() as session:
            # User constraint
            session.run("""
                CREATE CONSTRAINT user_id_unique IF NOT EXISTS
                FOR (u:User) REQUIRE u.id IS UNIQUE
            """)
            
            # Merchant constraint
            session.run("""
                CREATE CONSTRAINT merchant_id_unique IF NOT EXISTS
                FOR (m:Merchant) REQUIRE m.id IS UNIQUE
            """)
            
            # Device constraint
            session.run("""
                CREATE CONSTRAINT device_id_unique IF NOT EXISTS
                FOR (d:Device) REQUIRE d.id IS UNIQUE
            """)

            # Transaction constraint
            session.run("""
                CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS
                FOR (t:Transaction) REQUIRE t.id IS UNIQUE
            """)
        print("Constraints created")
    
    def load_users(self, users_df: pd.DataFrame):
        """Load users as nodes."""
        print(f"Loading {len(users_df):,} users...")
        
        with self.driver.session() as session:
            for _, user in tqdm(users_df.iterrows(), total=len(users_df), desc="Users"):
                session.run("""
                    MERGE (u:User {id: $user_id})
                    SET u.user_id = $user_id,
                        u.email = $email,
                        u.name = $name,
                        u.created_at = datetime($created_at),
                        u.risk_tier = $risk_tier,
                        u.avg_txn_amount = $avg_txn_amount
                """, {
                    'user_id': user['user_id'],
                    'email': user['email'],
                    'name': user['name'],
                    'created_at': user['created_at'].isoformat(),
                    'risk_tier': user['risk_tier'],
                    'avg_txn_amount': float(user['avg_txn_amount'])
                })
        
        print(f"Loaded {len(users_df):,} users")
    
    def load_merchants(self, merchants_df: pd.DataFrame):
        """Load merchants as nodes."""
        print(f"Loading {len(merchants_df):,} merchants...")
        
        with self.driver.session() as session:
            for _, merchant in tqdm(merchants_df.iterrows(), total=len(merchants_df), desc="Merchants"):
                session.run("""
                    MERGE (m:Merchant {id: $merchant_id})
                    SET m.merchant_id = $merchant_id,
                        m.name = $name,
                        m.category = $category,
                        m.base_fraud_rate = $base_fraud_rate,
                        m.avg_transaction_amount = $avg_transaction_amount,
                        m.is_high_risk = $is_high_risk
                """, {
                    'merchant_id': merchant['merchant_id'],
                    'name': merchant['name'],
                    'category': merchant['category'],
                    'base_fraud_rate': float(merchant['base_fraud_rate']),
                    'avg_transaction_amount': float(merchant['avg_transaction_amount']),
                    'is_high_risk': bool(merchant['is_high_risk'])
                })
        
        print(f"Loaded {len(merchants_df):,} merchants")
    
    def load_devices(self, devices_df: pd.DataFrame):
        """Load devices as nodes."""
        print(f"Loading {len(devices_df):,} devices...")
        
        with self.driver.session() as session:
            for _, device in tqdm(devices_df.iterrows(), total=len(devices_df), desc="Devices"):
                session.run("""
                    MERGE (d:Device {id: $device_id})
                    SET d.device_id = $device_id,
                        d.user_agent = $user_agent,
                        d.os = $os,
                        d.browser = $browser,
                        d.first_seen = datetime($first_seen),
                        d.is_shared = $is_shared,
                        d.expected_users = $expected_users
                """, {
                    'device_id': device['device_id'],
                    'user_agent': device['user_agent'],
                    'os': device['os'],
                    'browser': device['browser'],
                    'first_seen': device['first_seen'].isoformat(),
                    'is_shared': bool(device['is_shared']),
                    'expected_users': int(device['expected_users'])
                })
        
        print(f"Loaded {len(devices_df):,} devices")
    
    def load_transactions(self, transactions_df: pd.DataFrame):
        """Load transactions as relationships."""
        print(f"Loading {len(transactions_df):,} transactions...")
        
        # Batch transactions for performance
        batch_size = 1000
        
        cypher = """
        UNWIND $transactions AS txn
        MATCH (u:User {id: txn.user_id})
        MATCH (m:Merchant {id: txn.merchant_id})
        MATCH (d:Device {id: txn.device_id})

        MERGE (t:Transaction {id: txn.transaction_id})
        ON CREATE SET t.amount = txn.amount,
                      t.currency = txn.currency,
                      t.timestamp = datetime(txn.timestamp),
                      t.fraud_score = txn.fraud_score,
                      t.status = txn.status,
                      t.ip_address = txn.ip_address,
                      t.card_last4 = txn.card_last4,
                      t.fraud_type = txn.fraud_type,
                      t.user_id = txn.user_id,
                      t.merchant_id = txn.merchant_id,
                      t.device_id = txn.device_id
        ON MATCH SET t.amount = txn.amount,
                     t.currency = txn.currency,
                     t.timestamp = datetime(txn.timestamp),
                     t.fraud_score = txn.fraud_score,
                     t.status = txn.status,
                     t.ip_address = txn.ip_address,
                     t.card_last4 = txn.card_last4,
                     t.fraud_type = txn.fraud_type

        MERGE (u)-[:PERFORMED]->(t)
        MERGE (t)-[:PAID_TO]->(m)
        MERGE (t)-[:USED_DEVICE]->(d)

        MERGE (u)-[r:TRANSACTED_WITH {transaction_id: txn.transaction_id}]->(m)
        ON CREATE SET r.amount = txn.amount,
                      r.currency = txn.currency,
                      r.timestamp = datetime(txn.timestamp),
                      r.is_fraud = txn.is_fraud,
                      r.fraud_type = txn.fraud_type
        ON MATCH SET r.amount = txn.amount,
                     r.currency = txn.currency,
                     r.timestamp = datetime(txn.timestamp),
                     r.is_fraud = txn.is_fraud,
                     r.fraud_type = txn.fraud_type
        """

        with self.driver.session() as session:
            for i in tqdm(range(0, len(transactions_df), batch_size), desc="Transaction batches"):
                batch = transactions_df.iloc[i:i+batch_size]

                transactions_payload = []
                for _, txn in batch.iterrows():
                    is_fraud = int(txn['is_fraud'])
                    fraud_score = 0.92 if is_fraud == 1 else 0.08
                    transactions_payload.append({
                        'transaction_id': txn['transaction_id'],
                        'user_id': txn['user_id'],
                        'merchant_id': txn['merchant_id'],
                        'device_id': txn['device_id'],
                        'amount': float(txn['amount']),
                        'currency': txn.get('currency', 'USD'),
                        'timestamp': txn['timestamp'].isoformat(),
                        'fraud_score': fraud_score,
                        'status': 'PENDING',
                        'ip_address': txn.get('ip_address', ''),
                        'card_last4': txn.get('card_last4', ''),
                        'fraud_type': txn.get('fraud_type'),
                        'is_fraud': is_fraud
                    })

                session.run(cypher, transactions=transactions_payload)
        
        print(f"Loaded {len(transactions_df):,} transactions")


def main():
    # Configuration
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'graphguard_dev')
    
    DATA_DIR = Path('data')
    
    print("="*60)
    print("GraphGuard Neo4j Graph Loader")
    print("="*60)
    print(f"\nConnecting to Neo4j: {NEO4J_URI}")
    
    # Initialize loader
    loader = GraphLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # Clear existing data
        loader.clear_database()
        
        # Create constraints
        loader.create_constraints()
        
        # Load entities
        print("\nLoading entities...")
        
        users_df = pd.read_parquet(DATA_DIR / 'users.parquet')
        loader.load_users(users_df)
        
        merchants_df = pd.read_parquet(DATA_DIR / 'merchants.parquet')
        loader.load_merchants(merchants_df)
        
        devices_df = pd.read_parquet(DATA_DIR / 'devices.parquet')
        loader.load_devices(devices_df)
        
        # Load transactions
        print("\nLoading relationships...")
        transactions_df = pd.read_parquet(DATA_DIR / 'transactions.parquet')
        loader.load_transactions(transactions_df)
        
        # Print stats
        print("\n" + "="*60)
        print("Graph loaded successfully.")
        print("="*60)
        
        with loader.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
            print("\nNode counts:")
            for record in result:
                print(f"  {record['label']}: {record['count']:,}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\nRelationship counts:")
            for record in result:
                print(f"  {record['type']}: {record['count']:,}")
        
        print("\nNext step: Run graph algorithms (graph_algorithms.cypher)")
        
    finally:
        loader.close()


if __name__ == '__main__':
    main()
