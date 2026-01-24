"""
GraphGuard - Rate Limiting Middleware
======================================
File: ml/serving/rate_limiter.py

Production-grade rate limiting using Redis for distributed limiting.
Falls back to in-memory limiting if Redis unavailable.
"""

import os
import time
from typing import Optional, Dict, Tuple
from collections import defaultdict
import asyncio

import structlog

logger = structlog.get_logger(__name__)


# ============================================
# Configuration
# ============================================

RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '1000'))
RATE_LIMIT_BURST = int(os.getenv('RATE_LIMIT_BURST', '100'))
RATE_LIMIT_WINDOW_SECONDS = 60


# ============================================
# In-Memory Rate Limiter (Fallback)
# ============================================

class InMemoryRateLimiter:
    """
    Token bucket rate limiter using in-memory storage.
    For single-instance deployments or Redis fallback.
    """
    
    def __init__(
        self,
        requests_per_minute: int = RATE_LIMIT_REQUESTS,
        burst_size: int = RATE_LIMIT_BURST
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.tokens_per_second = requests_per_minute / 60.0
        
        # {client_key: (tokens, last_update_time)}
        self._buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (float(burst_size), time.time())
        )
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, client_key: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed for client.
        
        Returns:
            (allowed, headers) - whether request is allowed and rate limit headers
        """
        async with self._lock:
            now = time.time()
            tokens, last_update = self._buckets[client_key]
            
            # Refill tokens based on time elapsed
            elapsed = now - last_update
            tokens = min(
                self.burst_size,
                tokens + elapsed * self.tokens_per_second
            )
            
            # Check if request can be processed
            if tokens >= 1:
                tokens -= 1
                allowed = True
            else:
                allowed = False
            
            self._buckets[client_key] = (tokens, now)
            
            # Calculate reset time
            if tokens < 1:
                wait_seconds = (1 - tokens) / self.tokens_per_second
            else:
                wait_seconds = 0
            
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_minute),
                'X-RateLimit-Remaining': str(max(0, int(tokens))),
                'X-RateLimit-Reset': str(int(now + wait_seconds)),
            }
            
            return allowed, headers
    
    async def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """Remove stale client buckets to prevent memory growth."""
        async with self._lock:
            now = time.time()
            stale_keys = [
                key for key, (_, last_update) in self._buckets.items()
                if now - last_update > max_age_seconds
            ]
            for key in stale_keys:
                del self._buckets[key]
            
            if stale_keys:
                logger.info("Cleaned up stale rate limit buckets", count=len(stale_keys))


# ============================================
# Redis Rate Limiter (Production)
# ============================================

class RedisRateLimiter:
    """
    Sliding window rate limiter using Redis for distributed limiting.
    Recommended for multi-instance production deployments.
    """
    
    def __init__(
        self,
        redis_client,
        requests_per_minute: int = RATE_LIMIT_REQUESTS,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
        key_prefix: str = "ratelimit:"
    ):
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    async def is_allowed(self, client_key: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed using Redis sliding window.
        
        Uses MULTI/EXEC for atomic operations.
        """
        import anyio
        
        key = f"{self.key_prefix}{client_key}"
        now = time.time()
        window_start = now - self.window_seconds
        
        try:
            # Use pipeline for atomic operations
            def _check_rate_limit():
                pipe = self.redis.pipeline()
                
                # Remove old entries outside window
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(now): now})
                
                # Set expiry on key
                pipe.expire(key, self.window_seconds + 1)
                
                results = pipe.execute()
                return results[1]  # zcard result (count before adding)
            
            current_count = await anyio.to_thread.run_sync(_check_rate_limit)
            
            allowed = current_count < self.requests_per_minute
            remaining = max(0, self.requests_per_minute - current_count - 1)
            
            headers = {
                'X-RateLimit-Limit': str(self.requests_per_minute),
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Reset': str(int(now + self.window_seconds)),
            }
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded",
                    client_key=client_key[:16] + "...",
                    count=current_count
                )
            
            return allowed, headers
            
        except Exception as e:
            logger.error("Redis rate limit check failed", error=str(e))
            # Fail open - allow request if Redis is down
            return True, {}


# ============================================
# Factory Function
# ============================================

_rate_limiter = None


def get_rate_limiter(redis_client=None):
    """Get or create rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        if redis_client is not None:
            _rate_limiter = RedisRateLimiter(redis_client)
            logger.info("Using Redis rate limiter")
        else:
            _rate_limiter = InMemoryRateLimiter()
            logger.info("Using in-memory rate limiter")
    
    return _rate_limiter


# ============================================
# FastAPI Middleware
# ============================================

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    """
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.limiter = get_rate_limiter(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        # Extract client identifier
        client_key = self._get_client_key(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ['/health', '/metrics']:
            return await call_next(request)
        
        # Check rate limit
        allowed, headers = await self.limiter.is_allowed(client_key)
        
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded. Please retry later."}',
                status_code=429,
                media_type='application/json',
                headers=headers
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def _get_client_key(self, request: Request) -> str:
        """
        Extract client identifier for rate limiting.
        Priority: API Key > X-Forwarded-For > Client IP
        """
        # Use API key if present
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api:{api_key[:16]}"
        
        # Use forwarded IP (for load balancer)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        # Fall back to client IP
        client_ip = request.client.host if request.client else 'unknown'
        return f"ip:{client_ip}"
