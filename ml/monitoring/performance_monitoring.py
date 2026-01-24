"""
GraphGuard - Prometheus Performance Monitoring
================================================
File: ml/monitoring/performance_monitoring.py
Reference: Specification.md Lines 2234-2296

Goal: Real-time model performance monitoring with Prometheus metrics.

Key Metrics:
- fraud_predictions_total: Counter of predictions by model/decision
- fraud_prediction_latency_seconds: Histogram for latency percentiles
- fraud_rate: Current fraud rate gauge
- feature_cache_hit_rate: Cache efficiency gauge

Gotchas (from spec):
- Use histograms for latency (not averages) - need percentiles (p50, p95, p99)
- Set up alerts: P99 latency > 200ms, fraud rate > 5%
"""

import os
import time
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime

from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Prometheus Metrics (Spec Lines 2240-2244)
# ============================================

# Total predictions counter
prediction_counter = Counter(
    'fraud_predictions_total',
    'Total predictions made',
    ['model_version', 'decision']
)

# Prediction latency histogram (for percentiles)
prediction_latency = Histogram(
    'fraud_prediction_latency_seconds',
    'Prediction latency in seconds',
    ['model_version'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
)

# Current fraud rate gauge
fraud_rate_gauge = Gauge(
    'fraud_rate',
    'Current fraud rate (rolling window)'
)

# Cache hit rate gauge
cache_hit_rate_gauge = Gauge(
    'feature_cache_hit_rate',
    'Feature cache hit rate'
)

# Model version info
model_info = Gauge(
    'fraud_model_info',
    'Model information',
    ['model_version', 'model_type']
)

# Decision distribution
decision_distribution = Gauge(
    'fraud_decision_distribution',
    'Distribution of decisions',
    ['decision']
)

# Active requests
active_requests = Gauge(
    'fraud_active_requests',
    'Currently processing requests'
)


# ============================================
# Performance Monitor Class (Spec Lines 2246-2274)
# ============================================

class PerformanceMonitor:
    """
    Real-time model performance monitoring.
    Reference: Specification.md Lines 2246-2274
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.predictions: deque = deque(maxlen=window_size)
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Decision counts for distribution
        self.decision_counts = {
            'AUTO_APPROVE': 0,
            'REVIEW': 0,
            'AUTO_DECLINE': 0
        }
        
        # Latency tracking
        self.latencies: deque = deque(maxlen=window_size)
        
        logger.info("Performance monitor initialized", window_size=window_size)
    
    def record_prediction(
        self,
        model_version: str,
        decision: str,
        latency: float,
        fraud_score: float
    ) -> None:
        """
        Record a prediction for monitoring.
        Reference: Specification.md Lines 2253-2264
        
        Args:
            model_version: Model version string
            decision: AUTO_APPROVE, REVIEW, or AUTO_DECLINE
            latency: Prediction latency in seconds
            fraud_score: Fraud probability (0-1)
        """
        # Prometheus metrics
        prediction_counter.labels(
            model_version=model_version,
            decision=decision
        ).inc()
        
        prediction_latency.labels(
            model_version=model_version
        ).observe(latency)
        
        # Track fraud rate
        self.predictions.append(fraud_score)
        fraud_count = sum(1 for p in self.predictions if p > 0.5)
        current_fraud_rate = fraud_count / len(self.predictions) if self.predictions else 0
        fraud_rate_gauge.set(current_fraud_rate)
        
        # Track decision distribution
        if decision in self.decision_counts:
            self.decision_counts[decision] += 1
        
        total_decisions = sum(self.decision_counts.values())
        for dec, count in self.decision_counts.items():
            decision_distribution.labels(decision=dec).set(
                count / total_decisions if total_decisions > 0 else 0
            )
        
        # Track latency for stats
        self.latencies.append(latency)
    
    def record_cache_event(self, hit: bool) -> None:
        """
        Record cache hit/miss.
        Reference: Specification.md Lines 2266-2273
        """
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        total = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total if total > 0 else 0
        cache_hit_rate_gauge.set(hit_rate)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        latencies = list(self.latencies)
        
        if latencies:
            latencies_sorted = sorted(latencies)
            p50 = latencies_sorted[int(len(latencies_sorted) * 0.5)]
            p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
            p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        else:
            p50 = p95 = p99 = 0
        
        total_cache = self.cache_hits + self.cache_misses
        
        return {
            'predictions_count': len(self.predictions),
            'fraud_rate': sum(1 for p in self.predictions if p > 0.5) / len(self.predictions) if self.predictions else 0,
            'latency_p50_ms': p50 * 1000,
            'latency_p95_ms': p95 * 1000,
            'latency_p99_ms': p99 * 1000,
            'cache_hit_rate': self.cache_hits / total_cache if total_cache > 0 else 0,
            'decision_distribution': self.decision_counts.copy()
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions.
        Gotcha: Set up alerts for P99 latency > 200ms, fraud rate > 5%
        """
        alerts = []
        stats = self.get_stats()
        
        # P99 latency > 200ms
        if stats['latency_p99_ms'] > 200:
            alerts.append({
                'severity': 'warning',
                'metric': 'latency_p99',
                'value': stats['latency_p99_ms'],
                'threshold': 200,
                'message': f"P99 latency ({stats['latency_p99_ms']:.1f}ms) exceeds threshold (200ms)"
            })
        
        # Fraud rate > 5%
        if stats['fraud_rate'] > 0.05:
            alerts.append({
                'severity': 'critical',
                'metric': 'fraud_rate',
                'value': stats['fraud_rate'],
                'threshold': 0.05,
                'message': f"Fraud rate ({stats['fraud_rate']:.2%}) exceeds threshold (5%)"
            })
        
        # Cache hit rate < 70%
        if stats['cache_hit_rate'] < 0.7 and (self.cache_hits + self.cache_misses) > 100:
            alerts.append({
                'severity': 'info',
                'metric': 'cache_hit_rate',
                'value': stats['cache_hit_rate'],
                'threshold': 0.7,
                'message': f"Cache hit rate ({stats['cache_hit_rate']:.2%}) is low"
            })
        
        return alerts


# ============================================
# Request Tracking Context Manager
# ============================================

class RequestTracker:
    """Context manager for tracking request latency."""
    
    def __init__(self, monitor: PerformanceMonitor, model_version: str):
        self.monitor = monitor
        self.model_version = model_version
        self.start_time = None
        self.fraud_score = 0.5
        self.decision = "REVIEW"
    
    def __enter__(self):
        self.start_time = time.time()
        active_requests.inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        active_requests.dec()
        latency = time.time() - self.start_time
        self.monitor.record_prediction(
            self.model_version,
            self.decision,
            latency,
            self.fraud_score
        )
        return False
    
    def set_result(self, fraud_score: float, decision: str):
        self.fraud_score = fraud_score
        self.decision = decision


# ============================================
# Singleton for API Usage
# ============================================

_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create performance monitor singleton."""
    global _monitor_instance
    
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    
    return _monitor_instance


def get_prometheus_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_prometheus_content_type() -> str:
    """Get Prometheus metrics content type."""
    return CONTENT_TYPE_LATEST
