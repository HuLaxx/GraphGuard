// GraphGuard - Graph Algorithms
// ===============================
// File: data-eng/neo4j/graph_algorithms.cypher
// Phase: 1.2 - Compute Graph Features
//
// This script runs graph algorithms using Neo4j GDS (Graph Data Science) library
// to compute features for fraud detection:
// - PageRank: Identifies influential nodes in the transaction network
// - Louvain: Detects communities (potential fraud rings)
// - Degree Centrality: Measures node connectivity

// ============================================
// 1. Create Graph Projection
// ============================================

// Drop existing projection if it exists
CALL gds.graph.drop('transactions-graph', false) YIELD graphName;

// Create named graph projection with User and Merchant nodes, TRANSACTED_WITH relationships
CALL gds.graph.project(
    'transactions-graph',
    ['User', 'Merchant', 'Device'],
    {
        TRANSACTED_WITH: {
            orientation: 'NATURAL',
            properties: ['amount', 'is_fraud']
        },
        USED_DEVICE: {
            orientation: 'NATURAL'
        }
    }
) YIELD graphName, nodeCount, relationshipCount;

// ============================================
// 2. PageRank Algorithm
// ============================================
// Identifies influential users/merchants in the network
// High PageRank = central to many transactions

CALL gds.pageRank.write(
    'transactions-graph',
    {
        writeProperty: 'pagerank',
        maxIterations: 20,
        dampingFactor: 0.85
    }
) YIELD ranIterations, didConverge, nodePropertiesWritten;

// ============================================
// 3. Louvain Community Detection
// ============================================
// Detects tightly-connected groups (potential fraud rings)

CALL gds.louvain.write(
    'transactions-graph',
    {
        writeProperty: 'community_id',
        maxLevels: 10,
        includeIntermediateCommunities: false
    }
) YIELD communityCount, modularity, ranLevels;

// ============================================
// 4. Degree Centrality
// ============================================
// Measures how connected each node is

CALL gds.degree.write(
    'transactions-graph',
    {
        writeProperty: 'degree'
    }
) YIELD centralityDistribution, nodePropertiesWritten;

// ============================================
// 5. Betweenness Centrality (sampled for performance)
// ============================================
// Identifies nodes that act as bridges in the network

CALL gds.betweenness.write(
    'transactions-graph',
    {
        writeProperty: 'betweenness',
        samplingSize: 1000,  // Sample for performance
        samplingSeed: 42
    }
) YIELD centralityDistribution, nodePropertiesWritten;

// ============================================
// 6. Compute Additional Graph Features
// ============================================

// Calculate in-degree and out-degree for each user
MATCH (u:User)
WITH u, size((u)-[:TRANSACTED_WITH]->()) as out_degree,
        size((u)<-[:TRANSACTED_WITH]-()) as in_degree
SET u.out_degree = out_degree,
    u.in_degree = in_degree;

// ============================================
// 7. Statistics and Verification
// ============================================

// Show PageRank distribution
MATCH (u:User)
RETURN 
    min(u.pagerank) as min_pagerank,
    max(u.pagerank) as max_pagerank,
    avg(u.pagerank) as avg_pagerank,
    percentileCont(u.pagerank, 0.95) as p95_pagerank;

// Show community distribution
MATCH (n)
WHERE n.community_id IS NOT NULL
RETURN n.community_id as community, count(*) as members
ORDER BY members DESC
LIMIT 20;

// Show high-risk nodes (high PageRank + part of fraud community)
MATCH (u:User)
WHERE u.pagerank > 0.001
OPTIONAL MATCH (u)-[r:TRANSACTED_WITH]->(m:Merchant)
WHERE r.is_fraud = 1
WITH u, count(r) as fraud_txns
WHERE fraud_txns > 0
RETURN u.user_id, u.pagerank, u.community_id, fraud_txns
ORDER BY u.pagerank DESC
LIMIT 10;

// ============================================
// 8. Export Features (Optional)
// ============================================

// This query can be used to export graph features to CSV
// Run this in Neo4j Browser and save results
/*
MATCH (u:User)
RETURN 
    u.user_id as user_id,
    u.pagerank as pagerank,
    u.community_id as community_id,
    u.degree as degree,
    u.out_degree as out_degree,
    u.in_degree as in_degree,
    u.betweenness as betweenness
ORDER BY u.user_id;
*/
