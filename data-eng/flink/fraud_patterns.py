"""
GraphGuard - Flink CEP Fraud Pattern Detection
================================================
File: data-eng/flink/fraud_patterns.py
Reference: Specification.md Lines 777-840

Goal: Detect complex fraud patterns in real-time using PyFlink.

Patterns Detected:
1. Rapid-fire transactions (5+ in 60 seconds)
2. High-value transaction from new device
3. Velocity anomaly (sudden spending increase)
4. Geographic impossibility (transactions from distant locations)

Gotchas (from spec):
- Flink state grows unbounded - set TTL
- Flink checkpoints to S3 for failure recovery
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Pattern Types
# ============================================

@dataclass
class PatternAlert:
    """Alert generated when a fraud pattern is detected."""
    pattern_type: str
    user_id: str
    risk_score: float
    timestamp: datetime
    details: Dict[str, Any]


# ============================================
# Pattern Detectors (Flink-compatible)
# ============================================

class RapidFireDetector:
    """
    Detect rapid-fire transactions (5+ in 60 seconds).
    Reference: Specification.md Lines 790-809
    """
    
    THRESHOLD_COUNT = 5
    WINDOW_MS = 60_000  # 60 seconds
    
    def __init__(self):
        # State: {user_id: [timestamp1, timestamp2, ...]}
        self.transactions: Dict[str, List[int]] = {}
    
    def process_element(
        self,
        value: Dict[str, Any],
        current_time_ms: int
    ) -> Optional[PatternAlert]:
        """
        Process a transaction event.
        
        Args:
            value: Transaction event dict
            current_time_ms: Current timestamp in milliseconds
        
        Returns:
            PatternAlert if pattern detected, None otherwise
        """
        user_id = value.get('user_id', '')
        
        # Initialize state for user
        if user_id not in self.transactions:
            self.transactions[user_id] = []
        
        # Remove old transactions (>60s ago)
        cutoff = current_time_ms - self.WINDOW_MS
        self.transactions[user_id] = [
            t for t in self.transactions[user_id] 
            if t > cutoff
        ]
        
        # Add current transaction
        self.transactions[user_id].append(current_time_ms)
        
        # Check threshold
        count = len(self.transactions[user_id])
        
        if count >= self.THRESHOLD_COUNT:
            logger.warning(
                "Rapid-fire pattern detected",
                user_id=user_id,
                count=count
            )
            
            return PatternAlert(
                pattern_type='RAPID_FIRE',
                user_id=user_id,
                risk_score=min(0.9 + (count - 5) * 0.02, 1.0),
                timestamp=datetime.now(),
                details={
                    'transaction_count': count,
                    'window_seconds': self.WINDOW_MS / 1000,
                    'transaction_id': value.get('transaction_id', '')
                }
            )
        
        return None


class NewDeviceHighValueDetector:
    """
    Detect high-value transactions from new devices.
    Reference: Specification.md Lines 812-824
    """
    
    HIGH_VALUE_THRESHOLD = 1000.0
    
    def __init__(self, redis_client=None):
        # State: known device IDs
        self.known_devices: set = set()
        self.redis_client = redis_client
    
    def is_new_device(self, device_id: str) -> bool:
        """Check if device is new (not seen before)."""
        if self.redis_client:
            # Check Redis for device
            return not self.redis_client.exists(f"device:{device_id}")
        else:
            # Use local state
            return device_id not in self.known_devices
    
    def mark_device_seen(self, device_id: str) -> None:
        """Mark device as seen."""
        if self.redis_client:
            self.redis_client.setex(f"device:{device_id}", 86400 * 30, "1")  # 30 days TTL
        else:
            self.known_devices.add(device_id)
    
    def process_element(
        self,
        value: Dict[str, Any]
    ) -> Optional[PatternAlert]:
        """
        Process a transaction event.
        
        Args:
            value: Transaction event dict
        
        Returns:
            PatternAlert if pattern detected, None otherwise
        """
        device_id = value.get('device_id', '')
        amount = value.get('amount', 0.0)
        user_id = value.get('user_id', '')
        
        is_new = self.is_new_device(device_id)
        is_high_value = amount > self.HIGH_VALUE_THRESHOLD
        
        # Mark device as seen
        self.mark_device_seen(device_id)
        
        if is_new and is_high_value:
            logger.warning(
                "New device high-value pattern detected",
                user_id=user_id,
                device_id=device_id[:8] + "...",
                amount=amount
            )
            
            return PatternAlert(
                pattern_type='NEW_DEVICE_HIGH_VALUE',
                user_id=user_id,
                risk_score=0.85,
                timestamp=datetime.now(),
                details={
                    'device_id': device_id,
                    'amount': amount,
                    'is_new_device': True,
                    'transaction_id': value.get('transaction_id', '')
                }
            )
        
        return None


class VelocityAnomalyDetector:
    """
    Detect sudden spending increases.
    """
    
    ANOMALY_MULTIPLIER = 3.0  # 3x normal spending
    STATE_TTL_MS = 7 * 24 * 60 * 60 * 1000  # 7 days
    
    def __init__(self):
        # State: {user_id: {'daily_avg': float, 'today_total': float}}
        self.user_spending: Dict[str, Dict[str, float]] = {}
        self.last_seen: Dict[str, int] = {}
    
    def process_element(
        self,
        value: Dict[str, Any],
        current_time_ms: Optional[int] = None
    ) -> Optional[PatternAlert]:
        """Process transaction for velocity anomaly."""
        if current_time_ms is None:
            current_time_ms = int(datetime.now().timestamp() * 1000)
        user_id = value.get('user_id', '')
        amount = value.get('amount', 0.0)
        current_day = datetime.utcfromtimestamp(current_time_ms / 1000).date()
        
        # Initialize state
        if user_id not in self.user_spending:
            self.user_spending[user_id] = {
                'daily_avg': 100.0,  # Default avg
                'today_total': 0.0,
                'day': current_day
            }
        
        state = self.user_spending[user_id]
        if state.get('day') != current_day:
            prev_total = state.get('today_total', 0.0)
            if prev_total > 0:
                state['daily_avg'] = 0.8 * state['daily_avg'] + 0.2 * prev_total
            state['today_total'] = 0.0
            state['day'] = current_day

        state['today_total'] += amount
        self.last_seen[user_id] = current_time_ms
        self._evict_old(current_time_ms)
        
        # Check for anomaly
        threshold = state['daily_avg'] * self.ANOMALY_MULTIPLIER
        
        if state['today_total'] > threshold:
            return PatternAlert(
                pattern_type='VELOCITY_ANOMALY',
                user_id=user_id,
                risk_score=0.75,
                timestamp=datetime.now(),
                details={
                    'today_total': state['today_total'],
                    'daily_average': state['daily_avg'],
                    'multiplier': state['today_total'] / state['daily_avg'],
                    'transaction_id': value.get('transaction_id', '')
                }
            )
        
        return None

    def _evict_old(self, current_time_ms: int) -> None:
        """Evict stale user state to avoid unbounded growth."""
        cutoff = current_time_ms - self.STATE_TTL_MS
        stale_users = [uid for uid, ts in self.last_seen.items() if ts < cutoff]
        for uid in stale_users:
            self.last_seen.pop(uid, None)
            self.user_spending.pop(uid, None)


class GeoImpossibilityDetector:
    """
    Detect geographically impossible transactions.
    """
    
    MAX_SPEED_KMH = 900  # Max realistic travel speed (plane)
    STATE_TTL_MS = 7 * 24 * 60 * 60 * 1000  # 7 days
    
    def __init__(self):
        # State: {user_id: {'lat': float, 'lon': float, 'timestamp': int}}
        self.last_location: Dict[str, Dict[str, Any]] = {}
    
    def calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in km using Haversine formula."""
        import math
        
        R = 6371  # Earth radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def process_element(
        self,
        value: Dict[str, Any],
        current_time_ms: int
    ) -> Optional[PatternAlert]:
        """Process transaction for geographic impossibility."""
        user_id = value.get('user_id', '')
        lat = value.get('latitude')
        lon = value.get('longitude')
        
        if lat is None or lon is None:
            return None
        
        if user_id in self.last_location:
            last = self.last_location[user_id]
            
            # Calculate distance and time
            distance_km = self.calculate_distance(
                last['lat'], last['lon'], lat, lon
            )
            time_hours = (current_time_ms - last['timestamp']) / 3_600_000
            
            if time_hours > 0:
                speed_kmh = distance_km / time_hours
                
                if speed_kmh > self.MAX_SPEED_KMH:
                    logger.warning(
                        "Geographic impossibility detected",
                        user_id=user_id,
                        speed_kmh=speed_kmh
                    )
                    
                    return PatternAlert(
                        pattern_type='GEO_IMPOSSIBILITY',
                        user_id=user_id,
                        risk_score=0.95,
                        timestamp=datetime.now(),
                        details={
                            'distance_km': distance_km,
                            'time_hours': time_hours,
                            'implied_speed_kmh': speed_kmh,
                            'transaction_id': value.get('transaction_id', '')
                        }
                    )
        
        # Update last location
        self.last_location[user_id] = {
            'lat': lat,
            'lon': lon,
            'timestamp': current_time_ms
        }
        self._evict_old(current_time_ms)
        
        return None

    def _evict_old(self, current_time_ms: int) -> None:
        """Evict stale location state to avoid unbounded growth."""
        cutoff = current_time_ms - self.STATE_TTL_MS
        stale_users = [uid for uid, loc in self.last_location.items() if loc.get('timestamp', 0) < cutoff]
        for uid in stale_users:
            self.last_location.pop(uid, None)


# ============================================
# Pattern Engine
# ============================================

class FraudPatternEngine:
    """
    Main pattern detection engine combining all detectors.
    """
    
    def __init__(self, redis_client=None):
        self.rapid_fire = RapidFireDetector()
        self.new_device = NewDeviceHighValueDetector(redis_client)


# ============================================
# Pattern Engine
# ============================================

class FraudPatternEngine:
    """
    Main pattern detection engine combining all detectors.
    """
    
    def __init__(self, redis_client=None):
        self.rapid_fire = RapidFireDetector()
        self.new_device = NewDeviceHighValueDetector(redis_client)
        self.velocity = VelocityAnomalyDetector()
        self.geo = GeoImpossibilityDetector()
        
        self.alert_count = 0
    
    def process_transaction(
        self,
        transaction: Dict[str, Any],
        timestamp_ms: Optional[int] = None,
        validate: bool = True
    ) -> List[PatternAlert]:
        """
        Process a transaction through all pattern detectors.
        
        Args:
            transaction: Transaction event dict
            timestamp_ms: Transaction timestamp in milliseconds
            validate: Whether to validate input (default: True)
        
        Returns:
            List of detected pattern alerts
        """
        # Validate input if enabled
        if validate:
            try:
                from data_eng.flink.validators import validate_transaction
                result = validate_transaction(transaction)
                if not result.is_valid:
                    logger.warning("Skipping invalid transaction", errors=result.errors)
                    return []
                transaction = result.sanitized_data
            except ImportError:
                pass  # Validation module not available
        
        if timestamp_ms is None:
            timestamp_ms = int(datetime.now().timestamp() * 1000)
        
        alerts = []
        
        # Check all patterns
        alert = self.rapid_fire.process_element(transaction, timestamp_ms)
        if alert:
            alerts.append(alert)
        
        alert = self.new_device.process_element(transaction)
        if alert:
            alerts.append(alert)
        
        alert = self.velocity.process_element(transaction, timestamp_ms)
        if alert:
            alerts.append(alert)
        
        alert = self.geo.process_element(transaction, timestamp_ms)
        if alert:
            alerts.append(alert)
        
        self.alert_count += len(alerts)
        
        return alerts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pattern detection statistics."""
        return {
            'total_alerts': self.alert_count,
            'known_devices': len(self.new_device.known_devices),
            'tracked_users_rapid_fire': len(self.rapid_fire.transactions),
            'tracked_users_velocity': len(self.velocity.user_spending)
        }


# ============================================
# Flink Job Definition (for reference)
# ============================================

def create_flink_job():
    """
    Create PyFlink streaming job.
    Reference: Specification.md Lines 826-836
    
    This is a reference implementation - actual Flink job would run
    in a Flink cluster with Kafka sources/sinks.
    """
    flink_job_template = '''
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.common.serialization import SimpleStringSchema

# Create execution environment
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(4)

# Enable checkpointing (every 60 seconds)
env.enable_checkpointing(60000)

# Kafka source
kafka_consumer = FlinkKafkaConsumer(
    topics='transactions.raw',
    deserialization_schema=SimpleStringSchema(),
    properties={
        'bootstrap.servers': 'kafka:9092',
        'group.id': 'flink-pattern-detector'
    }
)

# Create stream
transactions = env.add_source(kafka_consumer)

# Apply pattern detection
patterns = transactions \\
    .map(lambda x: json.loads(x)) \\
    .key_by(lambda x: x['user_id']) \\
    .process(PatternDetectorFunction())

# Kafka sink
kafka_producer = FlinkKafkaProducer(
    topic='fraud.patterns',
    serialization_schema=SimpleStringSchema(),
    producer_config={
        'bootstrap.servers': 'kafka:9092'
    }
)

patterns.add_sink(kafka_producer)

# Execute job
env.execute("GraphGuard Fraud Pattern Detection")
'''
    return flink_job_template


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test fraud pattern detection")
    parser.add_argument("--simulate", action="store_true", help="Run simulation")
    args = parser.parse_args()
    
    if args.simulate:
        print("Running pattern detection simulation...")
        
        engine = FraudPatternEngine()
        
        # Simulate rapid-fire attack
        user_id = "attacker_001"
        for i in range(7):
            txn = {
                'transaction_id': f'txn_{i}',
                'user_id': user_id,
                'amount': 50.0,
                'device_id': 'device_xyz'
            }
            alerts = engine.process_transaction(txn, timestamp_ms=i * 10000)
            
            if alerts:
                for alert in alerts:
                    print(f"ALERT: {alert.pattern_type} - User: {alert.user_id} - Risk: {alert.risk_score}")
        
        # Simulate new device high value
        txn = {
            'transaction_id': 'txn_new_device',
            'user_id': 'user_002',
            'amount': 2500.0,
            'device_id': 'new_device_123'
        }
        alerts = engine.process_transaction(txn)
        
        if alerts:
            for alert in alerts:
                print(f"ALERT: {alert.pattern_type} - User: {alert.user_id} - Risk: {alert.risk_score}")
        
        print(f"\nStats: {engine.get_stats()}")
