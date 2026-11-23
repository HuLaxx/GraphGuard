/**
 * GraphGuard - Fraud Queue Component
 * =====================================
 * File: frontend/src/components/FraudQueue.tsx
 * Reference: Specification.md Lines 3100-3200
 *
 * Goal: Display paginated fraud cases for investigation.
 */

import React, { memo } from 'react';

// ============================================
// Types
// ============================================

export interface FraudCase {
    id: string;
    transactionId: string;
    fraudScore: number;
    status: 'PENDING' | 'IN_REVIEW' | 'RESOLVED_FRAUD' | 'RESOLVED_LEGITIMATE' | 'ESCALATED';
    priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    amount: number;
    currency: string;
    userId: string;
    merchantName: string;
    createdAt: string;
}

export interface FraudQueueProps {
    cases: FraudCase[];
    totalCount: number;
    onCaseClick: (caseId: string) => void;
    onPageChange: (page: number) => void;
    currentPage: number;
    pageSize: number;
    isLoading?: boolean;
}

// ============================================
// Helper Functions
// ============================================

const getStatusColor = (status: FraudCase['status']) => {
    switch (status) {
        case 'PENDING': return '#ff9800';
        case 'IN_REVIEW': return '#2196f3';
        case 'RESOLVED_FRAUD': return '#f44336';
        case 'RESOLVED_LEGITIMATE': return '#4caf50';
        case 'ESCALATED': return '#9c27b0';
        default: return '#999';
    }
};

const getPriorityColor = (priority: FraudCase['priority']) => {
    switch (priority) {
        case 'CRITICAL': return '#d32f2f';
        case 'HIGH': return '#f44336';
        case 'MEDIUM': return '#ff9800';
        case 'LOW': return '#4caf50';
        default: return '#999';
    }
};

const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

// ============================================
// Component
// ============================================

const FraudQueueComponent: React.FC<FraudQueueProps> = ({
    cases,
    totalCount,
    onCaseClick,
    onPageChange,
    currentPage,
    pageSize,
    isLoading = false
}) => {
    const totalPages = Math.ceil(totalCount / pageSize);

    return (
        <div className="fraud-queue">
            <div className="queue-header" style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '16px'
            }}>
                <h2 style={{ margin: 0 }}>Fraud Investigation Queue</h2>
                <span style={{ color: '#666' }}>{totalCount} cases total</span>
            </div>

            {isLoading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>
            ) : (
                <>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ backgroundColor: '#f5f5f5' }}>
                                <th style={thStyle}>Priority</th>
                                <th style={thStyle}>Score</th>
                                <th style={thStyle}>Amount</th>
                                <th style={thStyle}>Merchant</th>
                                <th style={thStyle}>Status</th>
                                <th style={thStyle}>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cases.map((fraudCase) => (
                                <tr
                                    key={fraudCase.id}
                                    onClick={() => onCaseClick(fraudCase.id)}
                                    style={{
                                        cursor: 'pointer',
                                        borderBottom: '1px solid #e0e0e0'
                                    }}
                                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                >
                                    <td style={tdStyle}>
                                        <span style={{
                                            padding: '2px 8px',
                                            borderRadius: '4px',
                                            backgroundColor: getPriorityColor(fraudCase.priority),
                                            color: 'white',
                                            fontSize: '12px',
                                            fontWeight: 'bold'
                                        }}>
                                            {fraudCase.priority}
                                        </span>
                                    </td>
                                    <td style={tdStyle}>
                                        <span style={{
                                            color: fraudCase.fraudScore > 0.7 ? '#f44336' : fraudCase.fraudScore > 0.5 ? '#ff9800' : '#4caf50',
                                            fontWeight: 'bold'
                                        }}>
                                            {(fraudCase.fraudScore * 100).toFixed(0)}%
                                        </span>
                                    </td>
                                    <td style={tdStyle}>
                                        {fraudCase.currency} {fraudCase.amount.toLocaleString()}
                                    </td>
                                    <td style={tdStyle}>{fraudCase.merchantName}</td>
                                    <td style={tdStyle}>
                                        <span style={{
                                            padding: '2px 8px',
                                            borderRadius: '4px',
                                            backgroundColor: getStatusColor(fraudCase.status) + '20',
                                            color: getStatusColor(fraudCase.status),
                                            fontSize: '12px'
                                        }}>
                                            {fraudCase.status.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td style={{ ...tdStyle, color: '#666', fontSize: '13px' }}>
                                        {formatDate(fraudCase.createdAt)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    <div className="pagination" style={{
                        display: 'flex',
                        justifyContent: 'center',
                        gap: '8px',
                        marginTop: '16px'
                    }}>
                        <button
                            onClick={() => onPageChange(currentPage - 1)}
                            disabled={currentPage <= 1}
                            style={btnStyle}
                        >
                            Previous
                        </button>
                        <span style={{ padding: '8px 16px' }}>
                            Page {currentPage} of {totalPages}
                        </span>
                        <button
                            onClick={() => onPageChange(currentPage + 1)}
                            disabled={currentPage >= totalPages}
                            style={btnStyle}
                        >
                            Next
                        </button>
                    </div>
                </>
            )}

            <style>{`
        .fraud-queue {
          padding: 16px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e0e0e0;
        }
      `}</style>
        </div>
    );
};

const thStyle: React.CSSProperties = {
    padding: '12px 8px',
    textAlign: 'left',
    fontWeight: 600,
    fontSize: '13px',
    color: '#333'
};

const tdStyle: React.CSSProperties = {
    padding: '12px 8px',
    fontSize: '14px'
};

const btnStyle: React.CSSProperties = {
    padding: '8px 16px',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer'
};

export const FraudQueue = memo(FraudQueueComponent);
