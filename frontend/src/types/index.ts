// Fraud Case Types
export interface FraudCase {
    id: string;
    transactionId: string;
    fraudScore: number;
    status: FraudStatus;
    priority: Priority;
    amount: number;
    currency: string;
    userId: string;
    merchantName: string;
    merchantCategory?: string;
    createdAt: string;
    updatedAt?: string;
    assignedTo?: Investigator;
    notes?: CaseNote[];
}

export type FraudStatus =
    | "PENDING"
    | "IN_REVIEW"
    | "RESOLVED_FRAUD"
    | "RESOLVED_LEGITIMATE"
    | "ESCALATED";

export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type FraudLabel = "FRAUD" | "LEGITIMATE" | "NEEDS_MORE_INFO";

// Transaction Types
export interface Transaction {
    id: string;
    userId: string;
    merchantId: string;
    amount: number;
    currency: string;
    timestamp: string;
    fraudScore: number;
    decision: Decision;
    deviceId: string;
    ipAddress: string;
    modelVersion: string;
}

export type Decision = "AUTO_APPROVE" | "REVIEW" | "AUTO_DECLINE";

// User Types
export interface User {
    id: string;
    email?: string;
    createdAt: string;
    riskScore: number;
    pagerank: number;
    communityId: number;
    isBlocked: boolean;
    transactionCount: number;
    totalAmount: number;
}

export interface Investigator {
    id: string;
    name: string;
    email: string;
    activeCases: number;
    resolvedCases: number;
}

export interface CaseNote {
    id: string;
    content: string;
    authorId: string;
    authorName: string;
    createdAt: string;
}

// Graph Types
export interface GraphNode {
    id: string;
    type: "USER" | "MERCHANT" | "DEVICE" | "IP_ADDRESS";
    label: string;
    fraud: boolean;
    pagerank: number;
    riskScore: number;
}

export interface GraphLink {
    source: string;
    target: string;
    type: string;
    amount?: number;
}

export interface TransactionGraph {
    nodes: GraphNode[];
    edges: GraphLink[];
    nodeCount: number;
    edgeCount: number;
}

// SHAP Types
export interface ShapFeature {
    name: string;
    value: number;
    shapValue: number;
    importance: number;
    impact: "INCREASES" | "DECREASES" | "NEUTRAL";
    description?: string;
}

export interface ShapExplanation {
    transactionId: string;
    baseValue: number;
    predictionValue: number;
    features: ShapFeature[];
    plainEnglish: string;
}

// Dashboard Types
export interface DashboardMetrics {
    totalTransactions: number;
    fraudRate: number;
    pendingReview: number;
    autoApproved: number;
    autoDeclined: number;
    avgLatencyMs: number;
    p99LatencyMs: number;
    modelAccuracy: number;
}

// API Response Types
export interface PaginatedResponse<T> {
    items: T[];
    totalCount: number;
    hasNextPage: boolean;
    hasPreviousPage: boolean;
}
