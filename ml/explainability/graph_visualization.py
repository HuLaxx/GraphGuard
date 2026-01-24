"""
GraphGuard - Graph Visualization for Investigators
====================================================
File: ml/explainability/graph_visualization.py
Reference: Specification.md Lines 1813-1879

Goal: Generate D3.js-compatible JSON for suspicious subgraphs.

Gotchas (from spec):
- Large subgraphs (>100 nodes) crash D3.js - limit query results
- Include edge directionality for better visualization
"""

import os
from typing import Optional, Dict, Any, List

from neo4j import GraphDatabase
import json
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Configuration
# ============================================

def get_neo4j_config() -> dict:
    """Neo4j connection configuration."""
    return {
        'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD', 'graphguard_dev')
    }


# ============================================
# Graph Visualization Class
# ============================================

class GraphVisualizer:
    """
    Generate D3.js-compatible graph visualizations.
    Reference: Specification.md Lines 1813-1879
    """
    
    MAX_NODES = 100  # Gotcha: Limit to prevent D3.js crashes
    
    def __init__(self, neo4j_config: Optional[dict] = None):
        self.neo4j_config = neo4j_config or get_neo4j_config()
        
        self.driver = GraphDatabase.driver(
            self.neo4j_config['uri'],
            auth=(self.neo4j_config['user'], self.neo4j_config['password'])
        )
        
        self.driver.verify_connectivity()
        logger.info("Connected to Neo4j for visualization")
    
    def extract_user_subgraph(
        self,
        user_id: str,
        hops: int = 2,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Extract subgraph around a user.
        
        Args:
            user_id: Central user ID
            hops: Number of hops to explore
            limit: Max number of connected users
        
        Returns:
            D3.js-compatible graph data
        """
        query = """
        MATCH (u:User {id: $user_id})
        MATCH path = (u)-[:TRANSACTED_WITH*1..$hops]-(connected)
        WHERE connected:User OR connected:Merchant
        WITH u, connected, relationships(path) AS rels
        LIMIT $limit
        RETURN 
            u.id AS source_id,
            u.pagerank AS source_pagerank,
            u.fraud AS source_fraud,
            connected.id AS target_id,
            labels(connected)[0] AS target_type,
            connected.pagerank AS target_pagerank,
            connected.fraud AS target_fraud,
            [r IN rels | {
                amount: r.amount,
                timestamp: r.timestamp,
                type: type(r)
            }] AS edge_data
        """
        
        nodes = {}
        edges = []
        
        with self.driver.session() as session:
            # Parameterized query for hops
            full_query = query.replace("$hops", str(hops))
            result = session.run(full_query, user_id=user_id, limit=limit)
            
            for record in result:
                # Add source node
                source_id = record['source_id']
                if source_id not in nodes:
                    nodes[source_id] = {
                        'id': source_id,
                        'type': 'User',
                        'fraud': record['source_fraud'] or False,
                        'pagerank': record['source_pagerank'] or 0,
                        'is_target': source_id == user_id
                    }
                
                # Add connected node
                target_id = record['target_id']
                if target_id and target_id not in nodes:
                    nodes[target_id] = {
                        'id': target_id,
                        'type': record['target_type'] or 'User',
                        'fraud': record['target_fraud'] or False,
                        'pagerank': record['target_pagerank'] or 0,
                        'is_target': False
                    }
                
                # Add edges
                for edge in record['edge_data'] or []:
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'amount': edge.get('amount', 0),
                        'timestamp': edge.get('timestamp'),
                        'type': edge.get('type', 'TRANSACTED_WITH')
                    })
        
        graph_data = {
            'nodes': list(nodes.values()),
            'edges': edges,
            'center_user': user_id,
            'metadata': {
                'node_count': len(nodes),
                'edge_count': len(edges),
                'hops': hops
            }
        }
        
        logger.info(
            "Subgraph extracted",
            user_id=user_id,
            nodes=len(nodes),
            edges=len(edges)
        )
        
        return graph_data
    
    def extract_suspicious_subgraph(
        self,
        user_id: str,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Extract subgraph of suspicious users in same community.
        Reference: Specification.md Lines 1821-1870
        
        Args:
            user_id: Central user ID
            threshold: Fraud score threshold
        
        Returns:
            D3.js-compatible graph data
        """
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:IN_COMMUNITY]->(c:Community)
        OPTIONAL MATCH (c)<-[:IN_COMMUNITY]-(other:User)
        WHERE other.fraud = true OR other.predicted_fraud_score > $threshold
        
        WITH u, COLLECT(DISTINCT other) AS suspicious_users
        UNWIND suspicious_users AS sus
        MATCH path = (u)-[:TRANSACTED_WITH*1..2]-(sus)
        RETURN 
            u AS source,
            sus AS target,
            relationships(path) AS edges
        LIMIT 50
        """
        
        nodes = {}
        edges = []
        
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id, threshold=threshold)
            
            for record in result:
                source = record['source']
                target = record['target']
                
                if source:
                    uid = source['id']
                    if uid not in nodes:
                        nodes[uid] = {
                            'id': uid,
                            'type': 'User',
                            'fraud': source.get('fraud', False),
                            'predicted_score': source.get('predicted_fraud_score', 0),
                            'pagerank': source.get('pagerank', 0),
                            'is_target': uid == user_id
                        }
                
                if target:
                    tid = target['id']
                    if tid not in nodes:
                        nodes[tid] = {
                            'id': tid,
                            'type': 'User',
                            'fraud': target.get('fraud', False),
                            'predicted_score': target.get('predicted_fraud_score', 0),
                            'pagerank': target.get('pagerank', 0),
                            'is_target': False
                        }
                
                for edge in record['edges'] or []:
                    edges.append({
                        'source': edge.start_node.get('id', str(edge.start_node.id)),
                        'target': edge.end_node.get('id', str(edge.end_node.id)),
                        'amount': edge.get('amount', 0),
                        'timestamp': edge.get('timestamp')
                    })
        
        return {
            'nodes': list(nodes.values()),
            'edges': edges,
            'center_user': user_id,
            'threshold': threshold
        }
    
    def get_community_overview(
        self,
        community_id: int,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get overview of a suspicious community."""
        query = """
        MATCH (u:User {community_id: $community_id})
        OPTIONAL MATCH (u)-[r:TRANSACTED_WITH]-(other:User {community_id: $community_id})
        RETURN 
            u.id AS user_id,
            u.fraud AS fraud,
            u.pagerank AS pagerank,
            u.betweenness AS betweenness,
            COLLECT(DISTINCT {
                id: other.id,
                amount: r.amount
            })[..10] AS connections
        ORDER BY u.pagerank DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, community_id=community_id, limit=limit)
            
            nodes = []
            edges = []
            
            for record in result:
                nodes.append({
                    'id': record['user_id'],
                    'fraud': record['fraud'] or False,
                    'pagerank': record['pagerank'] or 0,
                    'betweenness': record['betweenness'] or 0
                })
                
                for conn in record['connections'] or []:
                    if conn.get('id'):
                        edges.append({
                            'source': record['user_id'],
                            'target': conn['id'],
                            'amount': conn.get('amount', 0)
                        })
        
        return {
            'community_id': community_id,
            'nodes': nodes,
            'edges': edges
        }
    
    def to_json(self, graph_data: Dict[str, Any], path: str) -> None:
        """Save graph data to JSON file."""
        with open(path, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
        logger.info("Graph saved", path=path)
    
    def close(self) -> None:
        """Close Neo4j connection."""
        self.driver.close()


# ============================================
# ML Explainability Module Init
# ============================================

# Add __init__.py content
__all__ = ['GraphVisualizer']


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract suspicious subgraphs")
    parser.add_argument("--user", required=True, help="User ID to analyze")
    parser.add_argument("--hops", type=int, default=2, help="Number of hops")
    parser.add_argument("--output", default="./subgraph.json", help="Output JSON path")
    parser.add_argument("--neo4j", default="bolt://localhost:7687", help="Neo4j URI")
    args = parser.parse_args()
    
    os.environ['NEO4J_URI'] = args.neo4j
    
    visualizer = GraphVisualizer()
    
    try:
        graph = visualizer.extract_user_subgraph(args.user, hops=args.hops)
        visualizer.to_json(graph, args.output)
        print(f"Graph extracted: {graph['metadata']['node_count']} nodes, {graph['metadata']['edge_count']} edges")
        print(f"Saved to {args.output}")
    finally:
        visualizer.close()
