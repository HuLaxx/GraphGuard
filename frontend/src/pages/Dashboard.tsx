/**
 * GraphGuard - Main Dashboard Page
 * ==================================
 * File: frontend/src/pages/Dashboard.tsx
 *
 * Main investigation dashboard with fraud queue, metrics, and visualization.
 */

import React, { useState, useEffect } from 'react';
import { FraudQueue, FraudCase } from '../components/FraudQueue';
import { NetworkGraph, GraphNode, GraphLink } from '../components/NetworkGraph';
import { ShapChart, ShapFeature } from '../components/ShapChart';

// ============================================
// Types
// ============================================

interface DashboardMetrics {
    totalTransactions: number;
    fraudRate: number;
    pendingReview: number;
    autoApproved: number;
    autoDeclined: number;
    avgLatencyMs: number;
}

// ============================================
// Mock Data (Replace with GraphQL in production)
// ============================================

const mockMetrics: DashboardMetrics = {
    totalTransactions: 125847,
    fraudRate: 0.023,
    pendingReview: 342,
    autoApproved: 118234,
    autoDeclined: 1456,
    avgLatencyMs: 45
};

const mockCases: FraudCase[] = [
    {
        id: 'case_001',
        transactionId: 'txn_a1b2c3',
        fraudScore: 0.92,
        status: 'PENDING',
        priority: 'CRITICAL',
        amount: 4500.00,
        currency: 'USD',
        userId: 'user_12345',
        merchantName: 'Suspicious Electronics',
        createdAt: new Date().toISOString()
    },
    {
        id: 'case_002',
        transactionId: 'txn_d4e5f6',
        fraudScore: 0.85,
        status: 'PENDING',
        priority: 'HIGH',
        amount: 1250.00,
        currency: 'USD',
        userId: 'user_67890',
        merchantName: 'Online Marketplace',
        createdAt: new Date(Date.now() - 3600000).toISOString()
    },
    {
        id: 'case_003',
        transactionId: 'txn_g7h8i9',
        fraudScore: 0.78,
        status: 'IN_REVIEW',
        priority: 'MEDIUM',
        amount: 890.00,
        currency: 'EUR',
        userId: 'user_11111',
        merchantName: 'Digital Services',
        createdAt: new Date(Date.now() - 7200000).toISOString()
    },
    {
        id: 'case_004',
        transactionId: 'txn_j0k1l2',
        fraudScore: 0.71,
        status: 'PENDING',
        priority: 'MEDIUM',
        amount: 550.00,
        currency: 'USD',
        userId: 'user_22222',
        merchantName: 'Gaming Platform',
        createdAt: new Date(Date.now() - 10800000).toISOString()
    }
];

const mockGraphNodes: GraphNode[] = [
    { id: 'user_12345', type: 'USER', label: 'Target User', fraud: true, pagerank: 0.025, riskScore: 0.92 },
    { id: 'user_related_1', type: 'USER', label: 'Connected User', fraud: true, pagerank: 0.018, riskScore: 0.78 },
    { id: 'user_related_2', type: 'USER', label: 'Connected User', fraud: false, pagerank: 0.012, riskScore: 0.35 },
    { id: 'merchant_001', type: 'MERCHANT', label: 'Suspicious Electronics', fraud: false, pagerank: 0.045, riskScore: 0.65 },
    { id: 'device_001', type: 'DEVICE', label: 'New Device', fraud: false, pagerank: 0.008, riskScore: 0.55 }
];

const mockGraphLinks: GraphLink[] = [
    { source: 'user_12345', target: 'merchant_001', amount: 4500, type: 'TRANSACTED_WITH' },
    { source: 'user_related_1', target: 'merchant_001', amount: 3200, type: 'TRANSACTED_WITH' },
    { source: 'user_related_2', target: 'merchant_001', amount: 150, type: 'TRANSACTED_WITH' },
    { source: 'user_12345', target: 'device_001', amount: 0, type: 'USES_DEVICE' },
    { source: 'user_related_1', target: 'device_001', amount: 0, type: 'USES_DEVICE' }
];

const mockShapFeatures: ShapFeature[] = [
    { name: 'txn_count_1h', value: 8, shapValue: 0.28, importance: 0.30, description: '8 transactions in last hour' },
    { name: 'amount', value: 4500, shapValue: 0.22, importance: 0.25, description: '$4,500 transaction amount' },
    { name: 'is_new_device', value: 1, shapValue: 0.18, importance: 0.20, description: 'Transaction from new device' },
    { name: 'merchant_fraud_rate', value: 0.12, shapValue: 0.12, importance: 0.15, description: '12% merchant fraud rate' },
    { name: 'pagerank', value: 0.025, shapValue: 0.08, importance: 0.10, description: 'High network centrality' },
    { name: 'device_age_days', value: 0, shapValue: 0.06, importance: 0.08, description: 'Device age: 0 days' },
    { name: 'user_avg_amount', value: 150, shapValue: -0.04, importance: 0.05, description: 'User avg: $150' }
];

// ============================================
// Dashboard Component
// ============================================

export const Dashboard: React.FC = () => {
    const [cases, setCases] = useState<FraudCase[]>(mockCases);
    const [selectedCase, setSelectedCase] = useState<FraudCase | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(false);

    const handleCaseClick = (caseId: string) => {
        const found = cases.find(c => c.id === caseId);
        setSelectedCase(found || null);
    };

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        // Fetch new page data
    };

    return (
        <div style={{
            minHeight: '100vh',
            backgroundColor: '#f5f5f5',
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
        }}>
            {/* Header */}
            <header style={{
                backgroundColor: '#1a1a2e',
                color: 'white',
                padding: '16px 32px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '24px' }}>Shield</span>
                    <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>GraphGuard</h1>
                </div>
                <nav style={{ display: 'flex', gap: '24px' }}>
                    <a href="#" style={{ color: 'white', textDecoration: 'none', fontWeight: 500 }}>Dashboard</a>
                    <a href="#" style={{ color: '#aaa', textDecoration: 'none' }}>Cases</a>
                    <a href="#" style={{ color: '#aaa', textDecoration: 'none' }}>Analytics</a>
                    <a href="#" style={{ color: '#aaa', textDecoration: 'none' }}>Settings</a>
                </nav>
            </header>

            <main style={{ padding: '24px 32px' }}>
                {/* Metrics Row */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(6, 1fr)',
                    gap: '16px',
                    marginBottom: '24px'
                }}>
                    <MetricCard
                        label="Total Transactions"
                        value={mockMetrics.totalTransactions.toLocaleString()}
                        color="#2196f3"
                    />
                    <MetricCard
                        label="Fraud Rate"
                        value={`${(mockMetrics.fraudRate * 100).toFixed(2)}%`}
                        color="#f44336"
                    />
                    <MetricCard
                        label="Pending Review"
                        value={mockMetrics.pendingReview.toString()}
                        color="#ff9800"
                    />
                    <MetricCard
                        label="Auto Approved"
                        value={mockMetrics.autoApproved.toLocaleString()}
                        color="#4caf50"
                    />
                    <MetricCard
                        label="Auto Declined"
                        value={mockMetrics.autoDeclined.toLocaleString()}
                        color="#9c27b0"
                    />
                    <MetricCard
                        label="Avg Latency"
                        value={`${mockMetrics.avgLatencyMs}ms`}
                        color="#00bcd4"
                    />
                </div>

                {/* Main Content */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: selectedCase ? '1fr 1fr' : '1fr',
                    gap: '24px'
                }}>
                    {/* Fraud Queue */}
                    <div>
                        <FraudQueue
                            cases={cases}
                            totalCount={mockMetrics.pendingReview}
                            onCaseClick={handleCaseClick}
                            onPageChange={handlePageChange}
                            currentPage={currentPage}
                            pageSize={10}
                            isLoading={isLoading}
                        />
                    </div>

                    {/* Case Detail Panel */}
                    {selectedCase && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            {/* Case Header */}
                            <div style={{
                                backgroundColor: 'white',
                                padding: '16px',
                                borderRadius: '8px',
                                border: '1px solid #e0e0e0'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <h2 style={{ margin: 0, fontSize: '18px' }}>
                                        Case #{selectedCase.id.slice(-6)}
                                    </h2>
                                    <span style={{
                                        padding: '4px 12px',
                                        borderRadius: '20px',
                                        backgroundColor: selectedCase.fraudScore > 0.8 ? '#ffebee' : '#fff3e0',
                                        color: selectedCase.fraudScore > 0.8 ? '#c62828' : '#e65100',
                                        fontWeight: 600
                                    }}>
                                        {(selectedCase.fraudScore * 100).toFixed(0)}% Risk
                                    </span>
                                </div>
                                <p style={{ margin: '8px 0 0', color: '#666' }}>
                                    {selectedCase.currency} {selectedCase.amount.toLocaleString()} * {selectedCase.merchantName}
                                </p>

                                <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
                                    <button style={actionButtonStyle('#4caf50')}>
                                        ok Mark Legitimate
                                    </button>
                                    <button style={actionButtonStyle('#f44336')}>
                                        x Confirm Fraud
                                    </button>
                                    <button style={actionButtonStyle('#9c27b0')}>
                                        up Escalate
                                    </button>
                                </div>
                            </div>

                            {/* SHAP Explanation */}
                            <ShapChart
                                features={mockShapFeatures}
                                baseValue={0.15}
                                predictionValue={selectedCase.fraudScore}
                                plainEnglish="High velocity (8 txns/hour) + new device + high amount -> 92% fraud probability"
                            />

                            {/* Network Graph */}
                            <NetworkGraph
                                nodes={mockGraphNodes}
                                links={mockGraphLinks}
                                width={500}
                                height={350}
                                onNodeClick={(node) => console.log('Node clicked:', node)}
                            />
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

// ============================================
// Sub-components
// ============================================

interface MetricCardProps {
    label: string;
    value: string;
    color: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, color }) => (
    <div style={{
        backgroundColor: 'white',
        padding: '16px',
        borderRadius: '8px',
        border: '1px solid #e0e0e0',
        borderLeft: `4px solid ${color}`
    }}>
        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>{label}</div>
        <div style={{ fontSize: '24px', fontWeight: 600, color: '#333' }}>{value}</div>
    </div>
);

const actionButtonStyle = (color: string): React.CSSProperties => ({
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: color,
    color: 'white',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '13px'
});

export default Dashboard;
