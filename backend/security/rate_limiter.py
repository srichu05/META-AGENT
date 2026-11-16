"""Thread-safe sliding-window rate limiter and resource abuse controls."""

from collections import defaultdict, deque
from functools import wraps
import logging
import os
import threading
import time
from typing import Callable, Dict, Optional, Tuple
from flask import g, jsonify, request

logger = logging.getLogger(__name__)


def parse_rate_limit(expr: str) -> Tuple[int, int]:
    """
    Parses rate limit expressions like '10/minute', '30/minute', '5/second', '100/hour'.
    Returns (limit_count, window_seconds).
    """
    if not expr or not isinstance(expr, str) or "/" not in expr:
        return 60, 60

    try:
        count_str, unit_str = expr.strip().split("/", 1)
        count = int(count_str.strip())
        unit = unit_str.strip().lower()

        unit_seconds = {
            "second": 1,
            "sec": 1,
            "s": 1,
            "minute": 60,
            "min": 60,
            "m": 60,
            "hour": 3600,
            "hr": 3600,
            "h": 3600,
            "day": 86400,
            "d": 86400,
        }
        window = unit_seconds.get(unit, 60)
        return max(1, count), max(1, window)
    except Exception:
        return 60, 60


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: Dict[str, deque] = defaultdict(deque)

    def is_enabled(self) -> bool:
        val = os.getenv("RATE_LIMIT_ENABLED", "true")
        return val.strip().lower() in ("1", "true", "yes")

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Records an access attempt and validates whether the key is within rate limits.
        Returns (is_allowed, remaining_quota, retry_after_seconds).
        """
        if not self.is_enabled():
            return True, limit, 0

        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            bucket = self._buckets[key]

            # Prune timestamps older than cutoff
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            current_count = len(bucket)
            if current_count >= limit:
                oldest = bucket[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, 0, retry_after

            bucket.append(now)
            remaining = max(0, limit - len(bucket))
            return True, remaining, 0

    def reset(self) -> None:
        """Clears all tracked access windows."""
        with self._lock:
            self._buckets.clear()


# Global rate limiter instance
limiter = SlidingWindowRateLimiter()


def rate_limit(limit_expr: Optional[str] = None, scope: Optional[str] = None) -> Callable:
    """
    Flask route decorator enforcing sliding-window rate limits per client IP or user.
    Returns HTTP 429 Too Many Requests when limits are breached.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not limiter.is_enabled():
                return fn(*args, **kwargs)

            # Determine limit configuration
            configured_expr = limit_expr
            if not configured_expr:
                if scope == "auth":
                    configured_expr = os.getenv("RATE_LIMIT_AUTH", "10/minute")
                elif scope == "debate":
                    configured_expr = os.getenv("RATE_LIMIT_DEBATE", "30/minute")
                elif scope == "upload":
                    configured_expr = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")
                else:
                    configured_expr = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")

            max_requests, window_secs = parse_rate_limit(configured_expr)

            # Determine client identity key (user_id if authenticated, otherwise remote IP)
            user_id = None
            if hasattr(g, "current_user") and g.current_user:
                user_id = g.current_user.get("user_id")

            client_identifier = f"user:{user_id}" if user_id else f"ip:{request.remote_addr or 'unknown'}"
            rate_key = f"{scope or fn.__name__}:{client_identifier}"

            allowed, remaining, retry_after = limiter.check_rate_limit(rate_key, max_requests, window_secs)

            if not allowed:
                logger.warning(f"🚫 Rate limit exceeded for {rate_key} ({configured_expr}). Retry in {retry_after}s.")
                response = jsonify({
                    "success": False,
                    "error": f"Rate limit exceeded. Allowed {max_requests} requests per {window_secs} seconds.",
                    "limit": configured_expr,
                    "retry_after_seconds": retry_after,
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                return response

            res = fn(*args, **kwargs)

            # If response is a Flask Response or tuple, attach headers
            if hasattr(res, "headers"):
                res.headers["X-RateLimit-Limit"] = str(max_requests)
                res.headers["X-RateLimit-Remaining"] = str(remaining)
            return res

        return wrapper
    return decorator

