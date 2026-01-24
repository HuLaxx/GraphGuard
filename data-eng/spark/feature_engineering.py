"""
GraphGuard - Spark Feature Engineering
=======================================
File: data-eng/spark/feature_engineering.py
Reference: Specification.md Lines 959-1015

Goal: Compute 200+ features for ML training including:
- Temporal features (transaction velocity, amounts)
- Device features (age, user count)
- Merchant features (avg amount, fraud rate)
- Geospatial features (impossible travel)

Gotchas (from spec):
- Window functions with unbounded FOLLOWING cause shuffle - use PRECEDING only
- Broadcast small tables (<10MB) to avoid shuffle joins
"""

import os
from datetime import datetime
from typing import Optional

from pyspark.sql import SparkSession, Window, DataFrame
from pyspark.sql.functions import (
    col, count, sum, mean, stddev, min, max, lag,
    when, lit, approx_count_distinct,
    hour, dayofweek, to_date, udf, coalesce, from_unixtime
)
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType,
    LongType, BooleanType, DoubleType, TimestampType
)
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Spark Session Configuration
# ============================================

def get_spark_session(app_name: str = "FraudFeatureEngineering") -> SparkSession:
    """
    Create Spark session with Delta Lake support.
    Reference: Specification.md Lines 967-970
    """
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.executor.memory", "8g") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "20") \
        .getOrCreate()


# ============================================
# Transaction Schema
# ============================================

TRANSACTION_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("user_id", StringType(), False),
    StructField("merchant_id", StringType(), False),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), False),
    StructField("timestamp", LongType(), False),  # Unix timestamp in milliseconds
    StructField("device_id", StringType(), False),
    StructField("ip_address", StringType(), False),
    StructField("card_last4", StringType(), True),
    StructField("fraud", BooleanType(), True),  # Label (if available)
])


# ============================================
# Feature Engineering Functions
# ============================================

def add_temporal_features(df: DataFrame) -> DataFrame:
    """
    Add temporal features using window functions.
    Reference: Specification.md Lines 975-986
    
    Features:
    - txn_count_1h, txn_count_24h, txn_count_7d
    - amount_sum_1h, amount_sum_24h
    - amount_mean_7d, amount_std_7d
    - hour_of_day, day_of_week
    """
    # Define windows (timestamps in milliseconds)
    # Gotcha: Use PRECEDING only to avoid shuffle
    window_1h = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-3600 * 1000, 0)
    window_24h = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-86400 * 1000, 0)
    window_7d = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-604800 * 1000, 0)
    
    df = df.withColumn("txn_count_1h", count("*").over(window_1h))
    df = df.withColumn("txn_count_24h", count("*").over(window_24h))
    df = df.withColumn("txn_count_7d", count("*").over(window_7d))
    
    df = df.withColumn("amount_sum_1h", coalesce(sum("amount").over(window_1h), lit(0.0)))
    df = df.withColumn("amount_sum_24h", coalesce(sum("amount").over(window_24h), lit(0.0)))
    
    df = df.withColumn("amount_mean_7d", coalesce(mean("amount").over(window_7d), lit(0.0)))
    df = df.withColumn("amount_std_7d", coalesce(stddev("amount").over(window_7d), lit(0.0)))
    
    # Time-based features
    df = df.withColumn("hour_of_day", hour(from_unixtime(col("timestamp") / 1000)))
    df = df.withColumn("day_of_week", dayofweek(from_unixtime(col("timestamp") / 1000)))
    
    # Amount relative to user's history
    df = df.withColumn(
        "amount_zscore",
        when(col("amount_std_7d") > 0, 
             (col("amount") - col("amount_mean_7d")) / col("amount_std_7d")
        ).otherwise(0.0)
    )
    
    # Time since last transaction
    user_window = Window.partitionBy("user_id").orderBy("timestamp")
    df = df.withColumn("prev_timestamp", lag("timestamp").over(user_window))
    df = df.withColumn(
        "time_since_last_txn",
        when(col("prev_timestamp").isNotNull(),
             (col("timestamp") - col("prev_timestamp")) / 1000.0
        ).otherwise(lit(None))
    )
    
    logger.info("Added temporal features", count=10)
    return df


def add_device_features(df: DataFrame) -> DataFrame:
    """
    Add device-based features.
    Reference: Specification.md Lines 988-991
    
    Features:
    - device_first_seen, device_age_days
    - device_user_count (shared device indicator)
    - is_new_device
    """
    device_window = (
        Window.partitionBy("device_id")
        .orderBy("timestamp")
        .rangeBetween(Window.unboundedPreceding, 0)
    )
    
    df = df.withColumn("device_first_seen", min("timestamp").over(device_window))
    df = df.withColumn(
        "device_age_days",
        (col("timestamp") - col("device_first_seen")) / (86400.0 * 1000)
    )
    df = df.withColumn(
        "device_user_count",
        approx_count_distinct("user_id").over(device_window)
    )
    
    # Flag new devices (less than 1 day old)
    df = df.withColumn("is_new_device", col("device_age_days") < 1)
    
    # Flag shared devices (multiple users)
    df = df.withColumn("is_shared_device", col("device_user_count") > 1)
    
    logger.info("Added device features", count=5)
    return df


def add_merchant_features(df: DataFrame) -> DataFrame:
    """
    Add merchant-based features.
    Reference: Specification.md Lines 993-999
    
    Features:
    - merchant_avg_amount, merchant_std_amount
    - merchant_fraud_rate (if labels available)
    - merchant_txn_count
    """
    merchant_window = (
        Window.partitionBy("merchant_id")
        .orderBy("timestamp")
        .rangeBetween(Window.unboundedPreceding, 0)
    )

    df = df.withColumn("merchant_avg_amount", mean("amount").over(merchant_window))
    df = df.withColumn("merchant_std_amount", stddev("amount").over(merchant_window))
    df = df.withColumn("merchant_txn_count", count("*").over(merchant_window))

    if "fraud" in df.columns:
        fraud_count = sum(when(col("fraud") == True, 1).otherwise(0)).over(merchant_window)
        df = df.withColumn(
            "merchant_fraud_rate",
            when(col("merchant_txn_count") > 0, fraud_count / col("merchant_txn_count")).otherwise(0.0)
        )
    else:
        df = df.withColumn("merchant_fraud_rate", lit(0.0))
    
    # Amount relative to merchant average
    df = df.withColumn(
        "amount_vs_merchant_avg",
        when(col("merchant_avg_amount") > 0,
             col("amount") / col("merchant_avg_amount")
        ).otherwise(1.0)
    )
    
    logger.info("Added merchant features", count=5)
    return df


def add_user_features(df: DataFrame) -> DataFrame:
    """
    Add user-based aggregate features.
    
    Features:
    - user_total_txn_count
    - user_avg_amount
    - user_unique_merchants
    - user_unique_devices
    """
    user_window = (
        Window.partitionBy("user_id")
        .orderBy("timestamp")
        .rangeBetween(Window.unboundedPreceding, 0)
    )
    
    # Running counts
    df = df.withColumn("user_total_txn_count", count("*").over(user_window))
    df = df.withColumn("user_avg_amount", mean("amount").over(user_window))
    df = df.withColumn("user_unique_merchants", approx_count_distinct("merchant_id").over(user_window))
    df = df.withColumn("user_unique_devices", approx_count_distinct("device_id").over(user_window))
    
    logger.info("Added user features", count=4)
    return df


def add_velocity_features(df: DataFrame) -> DataFrame:
    """
    Add velocity and anomaly features.
    
    Features:
    - rapid_fire_flag (5+ txns in 1h)
    - high_value_flag (amount > 3 std from user mean)
    """
    df = df.withColumn(
        "rapid_fire_flag",
        col("txn_count_1h") >= 5
    )
    
    df = df.withColumn(
        "high_value_flag",
        col("amount_zscore") > 3
    )
    
    # Amount relative to daily sum
    df = df.withColumn(
        "amount_pct_of_daily",
        when(col("amount_sum_24h") > 0,
             col("amount") / col("amount_sum_24h")
        ).otherwise(1.0)
    )
    
    logger.info("Added velocity features", count=3)
    return df


# ============================================
# Main Feature Engineering Pipeline
# ============================================

class FeatureEngineer:
    """
    PySpark feature engineering pipeline for fraud detection.
    """
    
    def __init__(self, spark: Optional[SparkSession] = None):
        self.spark = spark or get_spark_session()
    
    def compute_features(
        self,
        input_path: str,
        output_path: str,
        process_date: Optional[str] = None
    ) -> DataFrame:
        """
        Run the full feature engineering pipeline.
        
        Args:
            input_path: Path to input transactions (Delta/Parquet)
            output_path: Path to output features (Delta)
        
        Returns:
            DataFrame with computed features
        """
        logger.info("Starting feature engineering", input=input_path)
        
        # Read input data
        if input_path.endswith(".parquet"):
            df = self.spark.read.parquet(input_path)
        else:
            df = self.spark.read.format("delta").load(input_path)
        
        initial_count = df.count()
        logger.info("Loaded transactions", count=initial_count)
        
        # Apply feature engineering
        df = add_temporal_features(df)
        df = add_device_features(df)
        df = add_merchant_features(df)
        df = add_user_features(df)
        df = add_velocity_features(df)
        
        # Add date column for partitioning
        df = df.withColumn("date", to_date(from_unixtime(col("timestamp") / 1000)))
        df = df.withColumn("event_timestamp", from_unixtime(col("timestamp") / 1000).cast("timestamp"))
        
        # Select final feature columns
        feature_columns = [
            # IDs
            "transaction_id", "user_id", "merchant_id", "device_id",
            # Original
            "amount", "currency", "timestamp", "date", "event_timestamp",
            # Temporal
            "txn_count_1h", "txn_count_24h", "txn_count_7d",
            "amount_sum_1h", "amount_sum_24h",
            "amount_mean_7d", "amount_std_7d",
            "hour_of_day", "day_of_week",
            "amount_zscore", "time_since_last_txn",
            # Device
            "device_age_days", "device_user_count",
            "is_new_device", "is_shared_device",
            # Merchant
            "merchant_avg_amount", "merchant_std_amount",
            "merchant_txn_count", "merchant_fraud_rate",
            "amount_vs_merchant_avg",
            # User
            "user_total_txn_count", "user_avg_amount",
            "user_unique_merchants", "user_unique_devices",
            # Velocity
            "rapid_fire_flag", "high_value_flag", "amount_pct_of_daily",
            # Label (if present)
            "fraud"
        ]
        
        # Only select columns that exist
        existing_cols = [c for c in feature_columns if c in df.columns]
        df = df.select(existing_cols)

        output_df = df
        if process_date:
            output_df = df.filter(col("date") == process_date)

        # Write output (limit overwrite scope when processing a single date)
        writer = output_df.write.format("delta").mode("overwrite").partitionBy("date")
        if process_date:
            writer = writer.option("replaceWhere", f"date = '{process_date}'")
        writer.save(output_path)
        
        logger.info(
            "Feature engineering complete",
            input_count=initial_count,
            output_path=output_path,
            feature_count=len(existing_cols),
            output_date=process_date or "all"
        )

        return output_df
    
    def stop(self):
        """Stop Spark session."""
        self.spark.stop()


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Spark Feature Engineering")
    parser.add_argument("--input", required=True, help="Input path (Delta/Parquet)")
    parser.add_argument("--output", required=True, help="Output path (Delta)")
    parser.add_argument("--date", help="Process specific date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    engineer = FeatureEngineer()
    
    try:
        df = engineer.compute_features(args.input, args.output, process_date=args.date)
        print(f"Features computed: {df.count()} rows, {len(df.columns)} columns")
    finally:
        engineer.stop()
