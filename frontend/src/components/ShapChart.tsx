/**
 * GraphGuard - SHAP Explanation Chart
 * =====================================
 * File: frontend/src/components/ShapChart.tsx
 * Reference: Specification.md Lines 3433-3510
 *
 * Goal: Visualize SHAP feature contributions to fraud predictions.
 */

import React, { memo } from 'react';

// ============================================
// Types
// ============================================

export interface ShapFeature {
    name: string;
    value: number;
    shapValue: number;
    importance: number;
    description?: string;
}

export interface ShapChartProps {
    features: ShapFeature[];
    baseValue: number;
    predictionValue: number;
    plainEnglish?: string;
}

// ============================================
// Component
// ============================================

const ShapChartComponent: React.FC<ShapChartProps> = ({
    features,
    baseValue,
    predictionValue,
    plainEnglish
}) => {
    // Sort by absolute importance
    const sortedFeatures = [...features]
        .sort((a, b) => Math.abs(b.shapValue) - Math.abs(a.shapValue))
        .slice(0, 10);

    const maxAbsValue = Math.max(...sortedFeatures.map(f => Math.abs(f.shapValue)), 0.01);

    return (
        <div className="shap-chart">
            <h3 style={{ marginBottom: '8px' }}>SHAP Explanation</h3>

            <div className="summary-row" style={{ marginBottom: '16px', fontSize: '14px' }}>
                <span>Base value: <strong>{baseValue.toFixed(3)}</strong></span>
                <span style={{ marginLeft: '20px' }}>
                    Prediction: <strong style={{ color: predictionValue > 0.5 ? '#f44336' : '#4caf50' }}>
                        {(predictionValue * 100).toFixed(1)}%
                    </strong>
                </span>
            </div>

            {plainEnglish && (
                <div className="plain-english" style={{
                    padding: '12px',
                    backgroundColor: '#fff3e0',
                    borderRadius: '4px',
                    marginBottom: '16px',
                    fontSize: '14px'
                }}>
                    {plainEnglish}
                </div>
            )}

            <div className="feature-bars">
                {sortedFeatures.map((feature, index) => {
                    const isPositive = feature.shapValue > 0;
                    const barWidth = (Math.abs(feature.shapValue) / maxAbsValue) * 100;

                    return (
                        <div key={index} className="feature-row" style={{
                            display: 'flex',
                            alignItems: 'center',
                            marginBottom: '8px',
                            gap: '8px'
                        }}>
                            <div className="feature-name" style={{
                                width: '140px',
                                fontSize: '12px',
                                textAlign: 'right',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                            }}>
                                {feature.name}
                            </div>

                            <div className="bar-container" style={{
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                position: 'relative',
                                height: '20px'
                            }}>
                                <div className="center-line" style={{
                                    position: 'absolute',
                                    left: '50%',
                                    height: '100%',
                                    width: '1px',
                                    backgroundColor: '#999'
                                }}></div>

                                <div style={{
                                    position: 'absolute',
                                    left: isPositive ? '50%' : `${50 - barWidth / 2}%`,
                                    width: `${barWidth / 2}%`,
                                    height: '16px',
                                    backgroundColor: isPositive ? '#f44336' : '#4caf50',
                                    borderRadius: '2px'
                                }}></div>
                            </div>

                            <div className="feature-value" style={{
                                width: '80px',
                                fontSize: '11px',
                                color: '#666'
                            }}>
                                {feature.shapValue > 0 ? '+' : ''}{feature.shapValue.toFixed(3)}
                            </div>

                            <div className="actual-value" style={{
                                width: '60px',
                                fontSize: '11px',
                                color: '#999'
                            }}>
                                ({typeof feature.value === 'number' ? feature.value.toFixed(2) : feature.value})
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="legend" style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '40px',
                marginTop: '16px',
                fontSize: '12px'
            }}>
                <span style={{ color: '#f44336' }}>
                    → Increases fraud risk
                </span>
                <span style={{ color: '#4caf50' }}>
                    ← Decreases fraud risk
                </span>
            </div>

            <style>{`
        .shap-chart {
          padding: 16px;
          background: white;
          border-radius: 8px;
          border: 1px solid #e0e0e0;
        }
        .feature-row:hover {
          background-color: #f5f5f5;
        }
      `}</style>
        </div>
    );
};

export const ShapChart = memo(ShapChartComponent);
