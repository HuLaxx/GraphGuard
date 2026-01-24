"""
GraphGuard - Run Graph Algorithms
==================================
File: data-eng/neo4j/run_graph_algorithms.py
Phase: 1.2 - Compute Graph Features

Goal: Run Neo4j GDS graph algorithms programmatically.
"""

import os
from neo4j import GraphDatabase


def run_algorithms(uri: str, user: str, password: str):
    """Run graph algorithms on transaction network."""
    
    print(f"Connecting to Neo4j: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            print("\n1. Creating graph projection...")
            # Drop existing projection
            try:
                session.run("CALL gds.graph.drop('transactions-graph')")
                print("   Dropped existing projection")
            except:
                print("   No existing projection to drop")
            
            # Create new projection
            result = session.run("""
                CALL gds.graph.project(
                    'transactions-graph',
                    ['User', 'Merchant', 'Device'],
                    'TRANSACTED_WITH'
                )
            """)
            record = result.single()
            print(f"   ✓ Created projection: {record['nodeCount']} nodes, {record['relationshipCount']} relationships")
            
            print("\n2. Running PageRank...")
            result = session.run("""
                CALL gds.pageRank.write(
                    'transactions-graph',
                    {
                        writeProperty: 'pagerank',
                        maxIterations: 20
                    }
                )
            """)
            record = result.single()
            print(f"   ✓ PageRank complete: {record['nodePropertiesWritten']} nodes updated")
            
            print("\n3. Running Louvain community detection...")
            result = session.run("""
                CALL gds.louvain.write(
                    'transactions-graph',
                    {
                        writeProperty: 'community_id',
                        maxLevels: 10
                    }
                )
            """)
            record = result.single()
            print(f"   ✓ Louvain complete: {record['communityCount']} communities found")
            
            print("\n4. Running Degree Centrality...")
            result = session.run("""
                CALL gds.degree.write(
                    'transactions-graph',
                    {
                        writeProperty: 'degree'
                    }
                )
            """)
            record = result.single()
            print(f"   ✓ Degree centrality complete")
            
            print("\n5. Computing in/out degree...")
            session.run("""
                MATCH (u:User)
                WITH u, size((u)-[:TRANSACTED_WITH]->()) as out_degree,
                        size((u)<-[:TRANSACTED_WITH]-()) as in_degree
                SET u.out_degree = out_degree,
                    u.in_degree = in_degree
            """)
            print("   ✓ In/out degree computed")
            
            print("\n6. Verification - PageRank statistics:")
            result = session.run("""
                MATCH (u:User)
                RETURN 
                    min(u.pagerank) as min_pr,
                    max(u.pagerank) as max_pr,
                    avg(u.pagerank) as avg_pr
            """)
            record = result.single()
            print(f"   Min: {record['min_pr']:.6f}")
            print(f"   Max: {record['max_pr']:.6f}")
            print(f"   Avg: {record['avg_pr']:.6f}")
            
            print("\n7. Top communities by size:")
            result = session.run("""
                MATCH (n)
                WHERE n.community_id IS NOT NULL
                RETURN n.community_id as community, count(*) as members
                ORDER BY members DESC
                LIMIT 10
            """)
            for i, record in enumerate(result, 1):
                print(f"   {i}. Community {record['community']}: {record['members']} members")
            
            print("\n✅ All graph algorithms completed successfully!")
            
    finally:
        driver.close()


def main():
    # Configuration
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'graphguard_dev_2026')
    
    print("="*60)
    print("GraphGuard Graph Algorithms")
    print("="*60)
    
    run_algorithms(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


if __name__ == '__main__':
    main()
