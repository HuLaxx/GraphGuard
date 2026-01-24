"""
GraphGuard - Input Validation for Flink Pattern Detection
===========================================================
File: data-eng/flink/validators.py

Provides input validation for transaction events before pattern processing.
"""

import re
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Validation Configuration
# ============================================

# Regex patterns for validation
USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
DEVICE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
TRANSACTION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
IP_ADDRESS_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

# Limits
MAX_AMOUNT = 10_000_000.0  # $10M
MIN_AMOUNT = 0.01
MAX_LATITUDE = 90.0
MIN_LATITUDE = -90.0
MAX_LONGITUDE = 180.0
MIN_LONGITUDE = -180.0


# ============================================
# Validation Result
# ============================================

@dataclass
class ValidationResult:
    """Result of transaction validation."""
    is_valid: bool
    errors: list
    sanitized_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success(cls, data: Dict[str, Any]) -> 'ValidationResult':
        return cls(is_valid=True, errors=[], sanitized_data=data)
    
    @classmethod
    def failure(cls, errors: list) -> 'ValidationResult':
        return cls(is_valid=False, errors=errors, sanitized_data=None)


# ============================================
# Validators
# ============================================

class TransactionValidator:
    """Validates and sanitizes transaction events."""
    
    @staticmethod
    def validate_user_id(user_id: Any) -> Tuple[bool, str, Optional[str]]:
        """Validate user_id format."""
        if user_id is None:
            return False, "user_id is required", None
        
        user_id_str = str(user_id).strip()
        
        if not user_id_str:
            return False, "user_id cannot be empty", None
        
        if not USER_ID_PATTERN.match(user_id_str):
            return False, f"user_id has invalid format: {user_id_str[:20]}", None
        
        return True, "", user_id_str
    
    @staticmethod
    def validate_device_id(device_id: Any) -> Tuple[bool, str, Optional[str]]:
        """Validate device_id format."""
        if device_id is None:
            return True, "", None  # device_id is optional
        
        device_id_str = str(device_id).strip()
        
        if not DEVICE_ID_PATTERN.match(device_id_str):
            return False, f"device_id has invalid format", None
        
        return True, "", device_id_str
    
    @staticmethod
    def validate_transaction_id(txn_id: Any) -> Tuple[bool, str, Optional[str]]:
        """Validate transaction_id format."""
        if txn_id is None:
            return False, "transaction_id is required", None
        
        txn_id_str = str(txn_id).strip()
        
        if not txn_id_str:
            return False, "transaction_id cannot be empty", None
        
        if not TRANSACTION_ID_PATTERN.match(txn_id_str):
            return False, f"transaction_id has invalid format", None
        
        return True, "", txn_id_str
    
    @staticmethod
    def validate_amount(amount: Any) -> Tuple[bool, str, Optional[float]]:
        """Validate transaction amount."""
        if amount is None:
            return False, "amount is required", None
        
        try:
            amount_float = float(amount)
        except (TypeError, ValueError):
            return False, f"amount must be numeric: {amount}", None
        
        if amount_float < MIN_AMOUNT:
            return False, f"amount must be >= {MIN_AMOUNT}", None
        
        if amount_float > MAX_AMOUNT:
            return False, f"amount must be <= {MAX_AMOUNT}", None
        
        return True, "", amount_float
    
    @staticmethod
    def validate_ip_address(ip: Any) -> Tuple[bool, str, Optional[str]]:
        """Validate IP address format."""
        if ip is None:
            return True, "", None  # IP is optional
        
        ip_str = str(ip).strip()
        
        if not IP_ADDRESS_PATTERN.match(ip_str):
            return False, f"ip_address has invalid format: {ip_str[:20]}", None
        
        return True, "", ip_str
    
    @staticmethod
    def validate_coordinates(lat: Any, lon: Any) -> Tuple[bool, str, Optional[Tuple[float, float]]]:
        """Validate latitude and longitude."""
        if lat is None and lon is None:
            return True, "", None  # Coordinates are optional
        
        if (lat is None) != (lon is None):
            return False, "Both latitude and longitude must be provided", None
        
        try:
            lat_float = float(lat)
            lon_float = float(lon)
        except (TypeError, ValueError):
            return False, "Coordinates must be numeric", None
        
        if not (MIN_LATITUDE <= lat_float <= MAX_LATITUDE):
            return False, f"latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}", None
        
        if not (MIN_LONGITUDE <= lon_float <= MAX_LONGITUDE):
            return False, f"longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}", None
        
        return True, "", (lat_float, lon_float)
    
    def validate(self, transaction: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete transaction event.
        
        Args:
            transaction: Raw transaction event dict
            
        Returns:
            ValidationResult with sanitized data or errors
        """
        errors = []
        sanitized = {}
        
        # Required fields
        valid, error, user_id = self.validate_user_id(transaction.get('user_id'))
        if not valid:
            errors.append(error)
        else:
            sanitized['user_id'] = user_id
        
        valid, error, txn_id = self.validate_transaction_id(transaction.get('transaction_id'))
        if not valid:
            errors.append(error)
        else:
            sanitized['transaction_id'] = txn_id
        
        valid, error, amount = self.validate_amount(transaction.get('amount'))
        if not valid:
            errors.append(error)
        else:
            sanitized['amount'] = amount
        
        # Optional fields
        valid, error, device_id = self.validate_device_id(transaction.get('device_id'))
        if not valid:
            errors.append(error)
        elif device_id:
            sanitized['device_id'] = device_id
        
        valid, error, ip = self.validate_ip_address(transaction.get('ip_address'))
        if not valid:
            errors.append(error)
        elif ip:
            sanitized['ip_address'] = ip
        
        valid, error, coords = self.validate_coordinates(
            transaction.get('latitude'),
            transaction.get('longitude')
        )
        if not valid:
            errors.append(error)
        elif coords:
            sanitized['latitude'] = coords[0]
            sanitized['longitude'] = coords[1]
        
        if errors:
            logger.warning("Transaction validation failed", errors=errors)
            return ValidationResult.failure(errors)
        
        # Copy through any additional fields
        for key in ['currency', 'merchant_id', 'timestamp']:
            if key in transaction:
                sanitized[key] = transaction[key]
        
        return ValidationResult.success(sanitized)


# Singleton instance
_validator = TransactionValidator()


def validate_transaction(transaction: Dict[str, Any]) -> ValidationResult:
    """Convenience function to validate a transaction."""
    return _validator.validate(transaction)
