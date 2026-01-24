"""
GraphGuard - Export Graph Features
===================================
File: data-eng/neo4j/export_graph_features.py
Phase: 1.2 - Export Graph Features to Parquet

Goal: Export computed graph features (PageRank, community_id, etc.) from Neo4j
      to parquet format for ML training.
"""

import os
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase


def export_graph_features(uri: str, user: str, password: str, output_file: str):
    """Export graph features from Neo4j to parquet."""
    
    print(f"Connecting to Neo4j: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # Query to get all graph features for users
            query = """
            MATCH (u:User)
            RETURN 
                u.user_id as user_id,
                u.pagerank as pagerank,
                u.community_id as community_id,
                u.degree as degree,
                u.out_degree as out_degree,
                u.in_degree as in_degree,
                COALESCE(u.betweenness, 0.0) as betweenness
            ORDER BY u.user_id
            """
            
            print("Querying graph features...")
            result = session.run(query)
            
            # Convert to DataFrame
            records = [record.data() for record in result]
            df = pd.DataFrame(records)
            
            # Fill NaN values with 0
            df = df.fillna(0)
            
            # Save to parquet
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(output_path, index=False)
            
            print(f"\n✅ Exported {len(df):,} graph features to: {output_path}")
            print(f"\nFeature statistics:")
            print(df.describe())
            
    finally:
        driver.close()


def main():
    # Configuration
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'graphguard_dev_2026')
    
    OUTPUT_FILE = 'data/graph_features.parquet'
    
    print("="*60)
    print("GraphGuard Graph Features Exporter")
    print("="*60)
    
    export_graph_features(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, OUTPUT_FILE)


if __name__ == '__main__':
    main()
