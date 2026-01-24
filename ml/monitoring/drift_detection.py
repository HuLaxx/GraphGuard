"""
GraphGuard - Evidently AI Drift Detection
===========================================
File: ml/monitoring/drift_detection.py
Reference: Specification.md Lines 2155-2250

Goal: Detect data drift and model performance degradation.

Drift Types:
1. Data Drift: Feature distributions changed
2. Concept Drift: Relationship between features and target changed
3. Prediction Drift: Model output distribution changed

Gotchas (from spec):
- Run drift detection on rolling window (e.g., last 7 days vs baseline)
- Set thresholds per-feature based on business impact
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Drift Detection Class
# ============================================

class DriftDetector:
    """
    Evidently AI-based drift detection.
    Reference: Specification.md Lines 2155-2250
    """
    
    # Feature importance thresholds
    CRITICAL_FEATURES = ['amount', 'txn_count_1h', 'pagerank']
    WARNING_THRESHOLD = 0.05  # 5% drift
    CRITICAL_THRESHOLD = 0.15  # 15% drift
    
    def __init__(
        self,
        numerical_features: List[str] = None,
        categorical_features: List[str] = None
    ):
        self.numerical_features = numerical_features or [
            'amount', 'txn_count_1h', 'txn_count_24h', 'pagerank',
            'betweenness', 'device_age_days', 'amount_zscore'
        ]
        self.categorical_features = categorical_features or [
            'currency', 'is_new_device', 'is_shared_device'
        ]
        
        self.reference_data: Optional[pd.DataFrame] = None
        self.drift_history: List[Dict[str, Any]] = []
    
    def set_reference_data(self, data: pd.DataFrame) -> None:
        """Set reference data for drift comparison."""
        self.reference_data = data.copy()
        logger.info("Reference data set", rows=len(data))
    
    def detect_drift(
        self,
        current_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Detect data drift between reference and current data.
        Reference: Specification.md Lines 2164-2200
        """
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")
        
        try:
            from evidently import ColumnMapping
            from evidently.report import Report
            from evidently.metric_preset import DataDriftPreset
            from evidently.metrics import (
                DataDriftTable,
                DatasetDriftMetric
            )
            
            has_evidently = True
        except ImportError:
            has_evidently = False
            logger.warning("Evidently not installed, using simplified drift detection")
        
        if has_evidently:
            return self._detect_drift_evidently(current_data)
        else:
            return self._detect_drift_simple(current_data)
    
    def _detect_drift_evidently(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """Full Evidently-based drift detection."""
        from evidently import ColumnMapping
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset
        
        # Column mapping
        column_mapping = ColumnMapping(
            target='fraud' if 'fraud' in current_data.columns else None,
            prediction='prediction' if 'prediction' in current_data.columns else None,
            numerical_features=[f for f in self.numerical_features if f in current_data.columns],
            categorical_features=[f for f in self.categorical_features if f in current_data.columns]
        )
        
        # Create report
        report = Report(metrics=[DataDriftPreset()])
        
        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=column_mapping
        )
        
        # Extract results
        report_dict = report.as_dict()
        
        drift_result = report_dict['metrics'][0]['result']
        
        result = {
            'dataset_drift': drift_result.get('dataset_drift', False),
            'drift_score': drift_result.get('drift_share', 0),
            'drifted_features': [],
            'feature_details': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Extract per-feature drift
        drift_by_columns = drift_result.get('drift_by_columns', {})
        for feature, details in drift_by_columns.items():
            if details.get('drift_detected', False):
                result['drifted_features'].append(feature)
            
            result['feature_details'][feature] = {
                'drift_detected': details.get('drift_detected', False),
                'drift_score': details.get('drift_score', 0),
                'stattest_name': details.get('stattest_name', ''),
                'threshold': details.get('stattest_threshold', 0)
            }
        
        self._log_drift(result)
        return result
    
    def _detect_drift_simple(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """Simplified drift detection without Evidently."""
        drifted_features = []
        feature_details = {}
        
        for col in self.numerical_features:
            if col not in current_data.columns or col not in self.reference_data.columns:
                continue
            
            ref_mean = self.reference_data[col].mean()
            cur_mean = current_data[col].mean()
            ref_std = self.reference_data[col].std()
            
            if ref_std > 0:
                drift_score = abs(cur_mean - ref_mean) / ref_std
            else:
                drift_score = 0
            
            drift_detected = drift_score > 2.0  # More than 2 std deviation
            
            if drift_detected:
                drifted_features.append(col)
            
            feature_details[col] = {
                'drift_detected': drift_detected,
                'drift_score': float(drift_score),
                'ref_mean': float(ref_mean),
                'cur_mean': float(cur_mean)
            }
        
        result = {
            'dataset_drift': len(drifted_features) > len(self.numerical_features) * 0.3,
            'drift_score': len(drifted_features) / len(self.numerical_features) if self.numerical_features else 0,
            'drifted_features': drifted_features,
            'feature_details': feature_details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self._log_drift(result)
        return result
    
    def _log_drift(self, result: Dict[str, Any]) -> None:
        """Log drift detection result."""
        self.drift_history.append(result)
        
        if result['dataset_drift']:
            logger.warning(
                "Data drift detected!",
                drift_score=result['drift_score'],
                drifted_features=result['drifted_features']
            )
        else:
            logger.info(
                "No significant drift",
                drift_score=result['drift_score']
            )
    
    def should_retrain(self, result: Dict[str, Any]) -> bool:
        """Determine if model retraining is needed."""
        # Critical feature drifted
        critical_drift = any(
            f in result['drifted_features'] for f in self.CRITICAL_FEATURES
        )
        
        # Overall drift too high
        high_drift = result['drift_score'] > self.CRITICAL_THRESHOLD
        
        return critical_drift or high_drift
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of drift history."""
        if not self.drift_history:
            return {'drift_events': 0, 'message': 'No drift checks performed'}
        
        total_checks = len(self.drift_history)
        drift_events = sum(1 for r in self.drift_history if r['dataset_drift'])
        
        return {
            'total_checks': total_checks,
            'drift_events': drift_events,
            'drift_rate': drift_events / total_checks,
            'last_check': self.drift_history[-1]['timestamp'],
            'last_drift_score': self.drift_history[-1]['drift_score']
        }


# ============================================
# Singleton for API Usage
# ============================================

_detector_instance: Optional[DriftDetector] = None


def get_drift_detector() -> DriftDetector:
    """Get or create drift detector singleton."""
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = DriftDetector()
    
    return _detector_instance
