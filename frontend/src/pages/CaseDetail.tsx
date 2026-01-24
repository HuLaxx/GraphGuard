/**
 * GraphGuard - Case Detail Page
 * ===============================
 * File: frontend/src/pages/CaseDetail.tsx
 *
 * Detailed view of a fraud case with all evidence.
 */

import React, { useState } from 'react';
import { NetworkGraph, GraphNode, GraphLink } from '../components/NetworkGraph';
import { ShapChart, ShapFeature } from '../components/ShapChart';

// ============================================
// Types
// ============================================

interface CaseDetail {
    id: string;
    transactionId: string;
    fraudScore: number;
    status: 'PENDING' | 'IN_REVIEW' | 'RESOLVED_FRAUD' | 'RESOLVED_LEGITIMATE' | 'ESCALATED';
    priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    amount: number;
    currency: string;
    merchantName: string;
    merchantCategory: string;
    userId: string;
    userEmail: string;
    deviceId: string;
    ipAddress: string;
    country: string;
    createdAt: string;
    notes: CaseNote[];
}

interface CaseNote {
    id: string;
    author: string;
    content: string;
    createdAt: string;
}

// ============================================
// Mock Data
// ============================================

const mockCase: CaseDetail = {
    id: 'case_001',
    transactionId: 'txn_a1b2c3d4',
    fraudScore: 0.92,
    status: 'PENDING',
    priority: 'CRITICAL',
    amount: 4500.00,
    currency: 'USD',
    merchantName: 'Suspicious Electronics Store',
    merchantCategory: 'Electronics',
    userId: 'user_12345',
    userEmail: 'j***n@email.com',
    deviceId: 'device_xyz789',
    ipAddress: '185.123.***.**',
    country: 'United States',
    createdAt: new Date().toISOString(),
    notes: [
        {
            id: 'note_1',
            author: 'System',
            content: 'Case auto-created due to high fraud score (92%)',
            createdAt: new Date().toISOString()
        }
    ]
};

const mockShapFeatures: ShapFeature[] = [
    { name: 'txn_count_1h', value: 8, shapValue: 0.28, importance: 0.30, description: '8 transactions in last hour' },
    { name: 'amount', value: 4500, shapValue: 0.22, importance: 0.25, description: '$4,500 transaction' },
    { name: 'is_new_device', value: 1, shapValue: 0.18, importance: 0.20, description: 'New device' },
    { name: 'merchant_fraud_rate', value: 0.12, shapValue: 0.12, importance: 0.15, description: '12% fraud rate' },
    { name: 'pagerank', value: 0.025, shapValue: 0.08, importance: 0.10, description: 'High centrality' }
];

const mockGraphNodes: GraphNode[] = [
    { id: 'user_12345', type: 'USER', label: 'Target User', fraud: true, pagerank: 0.025, riskScore: 0.92 },
    { id: 'user_related_1', type: 'USER', label: 'Related User 1', fraud: true, pagerank: 0.018, riskScore: 0.78 },
    { id: 'user_related_2', type: 'USER', label: 'Related User 2', fraud: false, pagerank: 0.012, riskScore: 0.35 },
    { id: 'merchant_001', type: 'MERCHANT', label: 'Suspicious Electronics', fraud: false, pagerank: 0.045, riskScore: 0.65 },
    { id: 'device_001', type: 'DEVICE', label: 'Shared Device', fraud: false, pagerank: 0.008, riskScore: 0.55 }
];

const mockGraphLinks: GraphLink[] = [
    { source: 'user_12345', target: 'merchant_001', amount: 4500, type: 'TRANSACTED_WITH' },
    { source: 'user_related_1', target: 'merchant_001', amount: 3200, type: 'TRANSACTED_WITH' },
    { source: 'user_related_2', target: 'merchant_001', amount: 150, type: 'TRANSACTED_WITH' },
    { source: 'user_12345', target: 'device_001', amount: 0, type: 'USES_DEVICE' },
    { source: 'user_related_1', target: 'device_001', amount: 0, type: 'USES_DEVICE' }
];

// ============================================
// Component
// ============================================

export const CaseDetail: React.FC = () => {
    const [caseData] = useState<CaseDetail>(mockCase);
    const [newNote, setNewNote] = useState('');
    const [activeTab, setActiveTab] = useState<'evidence' | 'network' | 'history'>('evidence');

    const handleAddNote = () => {
        if (newNote.trim()) {
            console.log('Adding note:', newNote);
            setNewNote('');
        }
    };

    const handleAction = (action: 'approve' | 'fraud' | 'escalate') => {
        console.log('Action:', action);
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'CRITICAL': return '#d32f2f';
            case 'HIGH': return '#f44336';
            case 'MEDIUM': return '#ff9800';
            case 'LOW': return '#4caf50';
            default: return '#999';
        }
    };

    return (
        <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <h1 style={{ margin: 0, fontSize: '24px' }}>Case #{caseData.id.slice(-6)}</h1>
                        <span style={{
                            padding: '4px 12px',
                            borderRadius: '4px',
                            backgroundColor: getPriorityColor(caseData.priority),
                            color: 'white',
                            fontSize: '12px',
                            fontWeight: 600
                        }}>
                            {caseData.priority}
                        </span>
                    </div>
                    <p style={{ margin: '8px 0 0', color: '#666' }}>
                        Transaction: {caseData.transactionId} • Created: {new Date(caseData.createdAt).toLocaleString()}
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => handleAction('approve')} style={buttonStyle('#4caf50')}>
                        ✓ Mark Legitimate
                    </button>
                    <button onClick={() => handleAction('fraud')} style={buttonStyle('#f44336')}>
                        ✗ Confirm Fraud
                    </button>
                    <button onClick={() => handleAction('escalate')} style={buttonStyle('#9c27b0')}>
                        ↑ Escalate
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '24px' }}>
                {/* Left Sidebar - Transaction Details */}
                <div>
                    <div style={cardStyle}>
                        <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>Transaction Details</h3>

                        <div style={{ marginBottom: '20px' }}>
                            <div style={{ fontSize: '32px', fontWeight: 700, color: caseData.fraudScore > 0.8 ? '#d32f2f' : '#ff9800' }}>
                                {(caseData.fraudScore * 100).toFixed(0)}%
                            </div>
                            <div style={{ fontSize: '14px', color: '#666' }}>Fraud Probability</div>
                        </div>

                        <DetailRow label="Amount" value={`${caseData.currency} ${caseData.amount.toLocaleString()}`} />
                        <DetailRow label="Merchant" value={caseData.merchantName} />
                        <DetailRow label="Category" value={caseData.merchantCategory} />
                        <DetailRow label="User Email" value={caseData.userEmail} />
                        <DetailRow label="Device ID" value={caseData.deviceId.slice(0, 12) + '...'} />
                        <DetailRow label="IP Address" value={caseData.ipAddress} />
                        <DetailRow label="Country" value={caseData.country} />
                    </div>

                    {/* Notes */}
                    <div style={{ ...cardStyle, marginTop: '16px' }}>
                        <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>Case Notes</h3>

                        {caseData.notes.map(note => (
                            <div key={note.id} style={{
                                padding: '12px',
                                backgroundColor: '#f5f5f5',
                                borderRadius: '4px',
                                marginBottom: '8px',
                                fontSize: '14px'
                            }}>
                                <div style={{ fontWeight: 500, marginBottom: '4px' }}>{note.author}</div>
                                <div>{note.content}</div>
                                <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
                                    {new Date(note.createdAt).toLocaleString()}
                                </div>
                            </div>
                        ))}

                        <textarea
                            value={newNote}
                            onChange={(e) => setNewNote(e.target.value)}
                            placeholder="Add a note..."
                            style={{
                                width: '100%',
                                padding: '12px',
                                border: '1px solid #e0e0e0',
                                borderRadius: '4px',
                                resize: 'vertical',
                                minHeight: '80px',
                                fontSize: '14px'
                            }}
                        />
                        <button onClick={handleAddNote} style={{ ...buttonStyle('#2196f3'), marginTop: '8px' }}>
                            Add Note
                        </button>
                    </div>
                </div>

                {/* Right Content - Tabs */}
                <div>
                    {/* Tab Navigation */}
                    <div style={{ display: 'flex', borderBottom: '1px solid #e0e0e0', marginBottom: '16px' }}>
                        {['evidence', 'network', 'history'].map(tab => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab as any)}
                                style={{
                                    padding: '12px 24px',
                                    border: 'none',
                                    background: 'none',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    color: activeTab === tab ? '#2196f3' : '#666',
                                    borderBottom: activeTab === tab ? '2px solid #2196f3' : '2px solid transparent'
                                }}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Tab Content */}
                    {activeTab === 'evidence' && (
                        <div>
                            <ShapChart
                                features={mockShapFeatures}
                                baseValue={0.15}
                                predictionValue={caseData.fraudScore}
                                plainEnglish="This transaction shows multiple high-risk indicators: unusual velocity (8 txns in 1 hour), large amount ($4,500), and transaction from a brand new device."
                            />
                        </div>
                    )}

                    {activeTab === 'network' && (
                        <div style={cardStyle}>
                            <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>Transaction Network</h3>
                            <NetworkGraph
                                nodes={mockGraphNodes}
                                links={mockGraphLinks}
                                width={700}
                                height={500}
                                onNodeClick={(node) => console.log('Clicked:', node)}
                            />
                        </div>
                    )}

                    {activeTab === 'history' && (
                        <div style={cardStyle}>
                            <h3 style={{ margin: '0 0 16px', fontSize: '16px' }}>User Transaction History</h3>
                            <p style={{ color: '#666' }}>Recent transactions for this user would appear here.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// ============================================
// Sub-components
// ============================================

const DetailRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
        <span style={{ color: '#666', fontSize: '14px' }}>{label}</span>
        <span style={{ fontWeight: 500, fontSize: '14px' }}>{value}</span>
    </div>
);

const cardStyle: React.CSSProperties = {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    border: '1px solid #e0e0e0'
};

const buttonStyle = (color: string): React.CSSProperties => ({
    padding: '10px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: color,
    color: 'white',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '14px'
});

export default CaseDetail;
