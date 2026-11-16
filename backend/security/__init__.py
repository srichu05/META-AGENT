"""Security, authentication, authorization, and rate limiting module."""

from .auth import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    create_test_auth_headers,
    decode_jwt,
    encode_jwt,
    generate_token,
    get_current_user,
    is_auth_enabled,
    require_auth,
    validate_token,
)
from .authorization import (
    can_access_document,
    filter_chunks_for_user,
    filter_documents_for_user,
)
from .rate_limiter import (
    SlidingWindowRateLimiter,
    limiter,
    parse_rate_limit,
    rate_limit,
)

__all__ = [
    "AuthenticationError",
    "InvalidTokenError",
    "SlidingWindowRateLimiter",
    "TokenExpiredError",
    "can_access_document",
    "create_test_auth_headers",
    "decode_jwt",
    "encode_jwt",
    "filter_chunks_for_user",
    "filter_documents_for_user",
    "generate_token",
    "get_current_user",
    "is_auth_enabled",
    "limiter",
    "parse_rate_limit",
    "rate_limit",
    "require_auth",
    "validate_token",
]

