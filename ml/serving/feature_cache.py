"""
GraphGuard - Feature Caching Strategy
=======================================
File: ml/serving/feature_cache.py
Reference: Specification.md Lines 2025-2087

Goal: Multi-tier caching for low-latency feature retrieval.

Cache Tiers:
1. L1: Redis (TTL: 15 min) - Hot features
2. L2: Feast Online Store - Warm features
3. L3: Feast Offline Store - Cold features

Gotchas (from spec):
- Cache key includes feature_names hash to avoid stale data
- Implement cache warming for high-value users (VIPs)
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Any

import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Feature Cache Class (Spec Lines 2033-2073)
# ============================================

class FeatureCache:
    """
    Multi-tier feature cache with Redis + Feast.
    Reference: Specification.md Lines 2033-2073
    """
    
    def __init__(
        self,
        redis_client=None,
        feast_store=None,
        ttl: int = 900  # 15 minutes
    ):
        self.redis = redis_client
        self.feast = feast_store
        self.ttl = ttl
        
        # Metrics
        self.hits = 0
        self.misses = 0
    
    def _cache_key(self, user_id: str, feature_names: List[str]) -> str:
        """
        Generate deterministic cache key.
        Gotcha: Include feature_names hash to avoid stale data when feature set changes.
        """
        feature_str = ",".join(sorted(feature_names))
        feature_hash = hashlib.md5(feature_str.encode()).hexdigest()[:8]
        return f"features:{user_id}:{feature_hash}"

    def _normalize_feature_key(self, key: str) -> str:
        """Normalize Feast feature keys to plain feature names."""
        return key.split(":")[-1]

    def _normalize_feature_dict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize feature keys and coerce nulls to 0."""
        normalized = {}
        for key, value in features.items():
            name = self._normalize_feature_key(key)
            if name == "user_id":
                continue
            if value is None:
                normalized[name] = 0
            else:
                try:
                    normalized[name] = float(value)
                except (TypeError, ValueError):
                    normalized[name] = value
        return normalized
    
    def get_features(
        self,
        user_id: str,
        feature_names: List[str],
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Get features with cache lookup.
        Reference: Specification.md Lines 2038-2058
        
        Args:
            user_id: User to fetch features for
            feature_names: List of feature names to fetch
            skip_cache: If True, bypass cache and fetch from source
        
        Returns:
            Dictionary mapping feature names to values
        """
        # 1. Try Redis cache
        if not skip_cache and self.redis:
            cache_key = self._cache_key(user_id, feature_names)
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    self.hits += 1
                    logger.debug("Cache hit", user_id=user_id, key=cache_key)
                    return json.loads(cached)
            except Exception as e:
                logger.warning("Cache read failed", error=str(e))
        
        self.misses += 1
        
        # 2. Fetch from Feast
        features = self._fetch_from_feast(user_id, feature_names)
        
        # 3. Store in cache
        if self.redis and features:
            cache_key = self._cache_key(user_id, feature_names)
            try:
                self.redis.setex(cache_key, self.ttl, json.dumps(features))
                logger.debug("Cached features", user_id=user_id, key=cache_key)
            except Exception as e:
                logger.warning("Cache write failed", error=str(e))
        
        return features
    
    def _fetch_from_feast(
        self,
        user_id: str,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """Fetch features from Feast online store."""
        if not self.feast:
            # Return defaults if Feast not available
            return {self._normalize_feature_key(name): 0 for name in feature_names}
        
        try:
            result = self.feast.get_online_features(
                entity_rows=[{"user_id": user_id}],
                features=feature_names
            ).to_dict()
            
            # Flatten result (Feast returns lists)
            flattened = {k: v[0] if v else None for k, v in result.items()}
            return self._normalize_feature_dict(flattened)
            
        except Exception as e:
            logger.error("Feast fetch failed", error=str(e), user_id=user_id)
            return {}
    
    def invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all cached features for a user.
        Reference: Specification.md Lines 2066-2072
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        pattern = f"features:{user_id}:*"
        try:
            keys = list(self.redis.scan_iter(pattern))
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info("Cache invalidated", user_id=user_id, keys_deleted=deleted)
                return deleted
        except Exception as e:
            logger.error("Cache invalidation failed", error=str(e))
        
        return 0
    
    def warm_cache(self, user_ids: List[str], feature_names: List[str]) -> int:
        """
        Pre-warm cache for list of users.
        Gotcha: Use for VIP users with high transaction volume.
        """
        warmed = 0
        for user_id in user_ids:
            features = self.get_features(user_id, feature_names, skip_cache=True)
            if features:
                warmed += 1
        
        logger.info("Cache warm complete", users_warmed=warmed, total=len(user_ids))
        return warmed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'ttl': self.ttl
        }


# ============================================
# Singleton for API Usage
# ============================================

_cache_instance: Optional[FeatureCache] = None


def get_feature_cache() -> FeatureCache:
    """Get or create feature cache singleton."""
    global _cache_instance
    
    if _cache_instance is None:
        import redis
        
        redis_client = None
        try:
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True
            )
            redis_client.ping()
        except Exception as e:
            logger.warning("Redis not available for cache", error=str(e))
        
        _cache_instance = FeatureCache(redis_client=redis_client)
    
    return _cache_instance
