"""
GraphGuard - GraphQL Schema Definition
========================================
File: backend/graphql/schema.graphql
Reference: Specification.md Lines 2730-2885

Goal: Define GraphQL schema for fraud investigation dashboard.

Key Types:
- Query: fraudQueue, fraudCase, transaction, suspiciousSubgraph, shapExplanation
- Mutation: labelCase, escalateCase, blockUser, whitelistMerchant
- Subscription: fraudQueueUpdated
"""

# GraphQL Schema for GraphGuard Fraud Detection Platform
# This is the SDL (Schema Definition Language) representation
# Actual implementation uses Strawberry Python types in resolvers.py

SCHEMA_SDL = '''
type Query {
  """Get paginated fraud cases for investigation queue"""
  fraudQueue(
    status: FraudStatus
    limit: Int = 50
    offset: Int = 0
    sortOrder: SortOrder = DESC
  ): FraudQueueConnection!

  """Get specific fraud case by ID"""
  fraudCase(id: ID!): FraudCase

  """Get transaction details"""
  transaction(id: ID!): Transaction

  """Get suspicious subgraph around a user"""
  suspiciousSubgraph(userId: ID!, hops: Int = 2): TransactionGraph!

  """Get SHAP explanation for a prediction"""
  shapExplanation(transactionId: ID!): ShapExplanation!

  """Get dashboard metrics"""
  dashboardMetrics: DashboardMetrics!
}

type Mutation {
  """Label a fraud case"""
  labelCase(id: ID!, label: FraudLabel!, notes: String): FraudCase!

  """Escalate a case"""
  escalateCase(id: ID!, reason: String!): FraudCase!

  """Block a user"""
  blockUser(userId: ID!, reason: String!): User!

  """Assign case to investigator"""
  assignCase(caseId: ID!, investigatorId: ID!): FraudCase!
}

# ============================================
# Core Types
# ============================================

type FraudCase {
  id: ID!
  transaction: Transaction!
  fraudScore: Float!
  status: FraudStatus!
  assignedTo: Investigator
  createdAt: DateTime!
  updatedAt: DateTime!
  notes: [CaseNote!]!
  evidence: Evidence!
  priority: Priority!
}

type FraudQueueConnection {
  items: [FraudCase!]!
  totalCount: Int!
  pageInfo: PageInfo!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type Transaction {
  id: ID!
  user: User!
  merchant: Merchant!
  amount: Float!
  currency: String!
  timestamp: DateTime!
  fraudScore: Float!
  decision: Decision!
  ipAddress: String!
  modelVersion: String!
}

type User {
  id: ID!
  email: String
  createdAt: DateTime!
  transactionCount: Int!
  totalAmount: Float!
  fraudCases: [FraudCase!]!
  riskScore: Float!
  pagerank: Float!
  communityId: Int!
  isBlocked: Boolean!
}

type Merchant {
  id: ID!
  name: String!
  category: String!
  fraudRate: Float!
  transactionCount: Int!
  isWhitelisted: Boolean!
}

type Device {
  id: ID!
  fingerprint: String!
  userAgent: String
  firstSeen: DateTime!
  lastSeen: DateTime!
  userCount: Int!
  isShared: Boolean!
}

type Investigator {
  id: ID!
  name: String!
  email: String!
  activeCases: Int!
  resolvedCases: Int!
  averageResolutionTime: Float!
}

# ============================================
# Graph Visualization Types
# ============================================

type TransactionGraph {
  nodes: [GraphNode!]!
  edges: [GraphEdge!]!
  nodeCount: Int!
  edgeCount: Int!
}

type GraphNode {
  id: ID!
  type: String!
  label: String!
  riskScore: Float!
  isFlagged: Boolean!
}

type GraphEdge {
  source: ID!
  target: ID!
  type: String!
  amount: Float
}

# ============================================
# Explainability Types
# ============================================

type ShapExplanation {
  transactionId: ID!
  baseValue: Float!
  predictionValue: Float!
  features: [ShapFeature!]!
  plainEnglish: String!
}

type ShapFeature {
  name: String!
  value: Float!
  shapValue: Float!
  importance: Float!
  impact: String!
  description: String!
}

type Evidence {
  suspiciousPatterns: [String!]!
  connectedFraudsters: Int!
  sharedDevices: Int!
  communityRiskScore: Float!
}

# ============================================
# Dashboard Types
# ============================================

type DashboardMetrics {
  totalTransactions: Int!
  fraudRate: Float!
  autoApproved: Int!
  autoDeclined: Int!
  pendingReview: Int!
  avgLatencyMs: Float!
  p99LatencyMs: Float!
  modelAccuracy: Float!
}

type CaseNote {
  id: ID!
  author: Investigator!
  content: String!
  createdAt: DateTime!
}

# ============================================
# Enums
# ============================================

enum FraudStatus {
  PENDING
  IN_REVIEW
  RESOLVED_FRAUD
  RESOLVED_LEGITIMATE
  ESCALATED
}

enum FraudLabel {
  FRAUD
  LEGITIMATE
  NEEDS_MORE_INFO
}

enum Decision {
  AUTO_APPROVE
  REVIEW
  AUTO_DECLINE
}

enum Priority {
  LOW
  MEDIUM
  HIGH
  CRITICAL
}

enum SortOrder {
  ASC
  DESC
}

scalar DateTime
'''

# Export for use in Python
def get_schema_sdl() -> str:
    """Get the GraphQL SDL schema."""
    return SCHEMA_SDL
