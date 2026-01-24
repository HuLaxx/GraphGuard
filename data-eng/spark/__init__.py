# Data Engineering - Spark Module
"""
PySpark feature engineering jobs.
Reference: Specification.md Lines 959-1015
"""

from .feature_engineering import FeatureEngineer, get_spark_session

__all__ = [
    "FeatureEngineer",
    "get_spark_session"
]
