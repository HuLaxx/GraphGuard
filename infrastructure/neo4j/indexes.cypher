// Neo4j Performance Indexes for GraphGuard Production
// ======================================================
// Run these commands in Neo4j Browser or via cypher-shell
// Reference: https://neo4j.com/docs/cypher-manual/current/indexes/

// ============================================
// 1. UNIQUE CONSTRAINTS (also create indexes)
// ============================================

// Users - unique user ID
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

// Transactions - unique transaction ID
CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.id IS UNIQUE;

// Merchants - unique merchant ID
CREATE CONSTRAINT merchant_id_unique IF NOT EXISTS
FOR (m:Merchant) REQUIRE m.id IS UNIQUE;

// Devices - unique device ID
CREATE CONSTRAINT device_id_unique IF NOT EXISTS
FOR (d:Device) REQUIRE d.id IS UNIQUE;

// ============================================
// 2. COMPOSITE INDEXES (for common queries)
// ============================================

// User + Timestamp (fraud queue queries)
CREATE INDEX user_timestamp IF NOT EXISTS
FOR (u:User) ON (u.id, u.created_at);

// Transaction + Fraud Score (high-risk transaction queries)
CREATE INDEX transaction_fraud_score IF NOT EXISTS
FOR (t:Transaction) ON (t.fraud_score);

// Transaction + Timestamp (time-range queries)
CREATE INDEX transaction_timestamp IF NOT EXISTS
FOR (t:Transaction) ON (t.timestamp);

// Transaction + Status (case management)
CREATE INDEX transaction_status IF NOT EXISTS
FOR (t:Transaction) ON (t.status);

// ============================================
// 3. FULL-TEXT INDEXES (for search)
// ============================================

// User search by email
CREATE FULLTEXT INDEX user_email_search IF NOT EXISTS
FOR (u:User) ON EACH [u.email];

// Merchant search by name
CREATE FULLTEXT INDEX merchant_name_search IF NOT EXISTS
FOR (m:Merchant) ON EACH [m.name];

// ============================================
// 4. RELATIONSHIP INDEXES (Neo4j 5.0+)
// ============================================

// TRANSACTED_WITH relationship properties
CREATE INDEX rel_transacted_amount IF NOT EXISTS
FOR ()-[r:TRANSACTED_WITH]-() ON (r.amount);

CREATE INDEX rel_transacted_timestamp IF NOT EXISTS
FOR ()-[r:TRANSACTED_WITH]-() ON (r.timestamp);

// ============================================
// 5. GRAPH DATA SCIENCE INDEXES
// ============================================

// PageRank results (pre-computed)
CREATE INDEX user_pagerank IF NOT EXISTS
FOR (u:User) ON (u.pagerank);

// Community ID (Louvain algorithm results)
CREATE INDEX user_community IF NOT EXISTS
FOR (u:User) ON (u.community_id);

// Betweenness centrality
CREATE INDEX user_betweenness IF NOT EXISTS
FOR (u:User) ON (u.betweenness);

// ============================================
// 6. VERIFY INDEXES
// ============================================

// List all indexes
// SHOW INDEXES;

// Check index usage
// EXPLAIN MATCH (t:Transaction) WHERE t.fraud_score > 0.7 RETURN t;

// ============================================
// 7. DROP UNUSED INDEXES (if needed)
// ============================================

// DROP INDEX index_name;
