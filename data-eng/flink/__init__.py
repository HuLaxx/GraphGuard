# Flink Pattern Detection Module
"""
PyFlink-based real-time fraud pattern detection.
Reference: Specification.md Lines 777-840
"""

from .fraud_patterns import (
    FraudPatternEngine,
    RapidFireDetector,
    NewDeviceHighValueDetector,
    VelocityAnomalyDetector,
    GeoImpossibilityDetector,
    PatternAlert
)

__all__ = [
    "FraudPatternEngine",
    "RapidFireDetector",
    "NewDeviceHighValueDetector",
    "VelocityAnomalyDetector",
    "GeoImpossibilityDetector",
    "PatternAlert"
]
