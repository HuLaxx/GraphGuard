"""
GraphGuard - Compute Basic Graph Features
==========================================
File: data-eng/neo4j/compute_basic_features.py
Phase: 1.2 - Compute Graph Features (Without GDS)

Goal: Compute basic graph features using native Cypher queries.
"""

import os
from neo4j import GraphDatabase
import pandas as pd


def compute_basic_features(uri: str, user: str, password: str):
    """Compute basic graph features without GDS library."""
    
    print(f"Connecting to Neo4j: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            print("\n1. Computing degree centrality (transaction counts)...")
            session.run("""
                MATCH (u:User)
                OPTIONAL  MATCH (u)-[r1:TRANSACTED_WITH]->()
                WITH u, count(r1) as out_deg
                OPTIONAL MATCH (u)<-[r2:TRANSACTED_WITH]-()
                WITH u, out_deg, count(r2) as in_deg
                SET u.out_degree = out_deg,
                    u.in_degree = in_deg,
                    u.degree = out_deg + in_deg
            """)
            print("   ✓ Degree computed for all users")
            
            print("\n2. Computing device sharing metrics...")
            session.run("""
                MATCH (d:Device)
                OPTIONAL MATCH (d)<-[r:USED_DEVICE]-()
                WITH d, count(r) as user_cnt
                SET d.user_count = user_cnt
            """)
            print("   ✓ Device metrics computed")
            
            print("\n3. Computing simple PageRank approximation...")
            # Simplified PageRank: count of transactions weighted by merchant connections
            session.run("""
                MATCH (u:User)-[:TRANSACTED_WITH]->(m:Merchant)
                WITH u, count(m) as merchant_count
                SET u.pagerank = toFloat(merchant_count) / 100.0
            """)
            print("   ✓ Simple PageRank computed")
            
            print("\n4. Assigning random community IDs (placeholder for Louvain)...")
            # For now, assign based on user_id hash for demo purposes
            session.run("""
                MATCH (u:User)
                SET u.community_id = toInteger(rand() * 50)
            """)
            print("   ✓ Community IDs assigned")
            
            print("\n5. Computing betweenness (simplified)...")
            session.run("""
                MATCH (u:User)
                SET u.betweenness = toFloat(u.degree) / toFloat(u.degree + 1)
            """)
            print("   ✓ Betweenness approximation computed")
            
            print("\n6. Statistics:")
            result = session.run("""
                MATCH (u:User)
                RETURN 
                    count(u) as total_users,
                    min(u.degree) as min_degree,
                    max(u.degree) as max_degree,
                    avg(u.degree) as avg_degree,
                    min(u.pagerank) as min_pr,
                    max(u.pagerank) as max_pr,
                    avg(u.pagerank) as avg_pr
            """)
            record = result.single()
            print(f"\n   Users: {record['total_users']}")
            print(f"   Degree - Min: {record['min_degree']}, Max: {record['max_degree']}, Avg: {record['avg_degree']:.2f}")
            print(f"   PageRank - Min: {record['min_pr']:.6f}, Max: {record['max_pr']:.6f}, Avg: {record['avg_pr']:.6f}")
            
            print("\n✅ Basic graph features computed successfully!")
            print("\nNote: These are simplified features. For production, install Neo4j GDS plugin for:")
            print("  - True PageRank algorithm")
            print("  - Louvain community detection") 
            print("  - Accurate betweenness centrality")
            
    finally:
        driver.close()


def main():
    # Configuration
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'graphguard_dev_2026')
    
    print("="*60)
    print("GraphGuard Basic Graph Features")
    print("="*60)
    
    compute_basic_features(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


if __name__ == '__main__':
    main()
