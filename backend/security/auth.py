"""Production authentication service using standard RFC 7519 HS256 JWT tokens."""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from flask import current_app, g, jsonify, request

from config import SYSTEM_CONFIG

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication failures."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has passed its exp expiration timestamp."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT signature is invalid or payload is malformed."""
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def get_jwt_secret() -> str:
    """Retrieves configured JWT secret key or falls back to system secret key."""
    return os.getenv("JWT_SECRET_KEY") or SYSTEM_CONFIG.get("secret_key", "dev-fallback-secret-key-change-in-production")


def is_auth_enabled() -> bool:
    """Checks whether token authentication is mandatory."""
    flask_env = os.getenv("FLASK_ENV", "development").lower()
    if flask_env in ("production", "prod"):
        return True
    auth_val = os.getenv("AUTH_ENABLED", "true")
    return auth_val.strip().lower() in ("1", "true", "yes")


def encode_jwt(payload: Dict[str, Any], secret_key: Optional[str] = None) -> str:
    """Encodes a payload dictionary into an RFC 7519 HS256 JSON Web Token."""
    key = secret_key or get_jwt_secret()
    header = {"alg": "HS256", "typ": "JWT"}

    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt(token: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Decodes and validates an RFC 7519 HS256 JWT.
    Enforces signature verification and expiration checks using constant-time comparison.
    """
    if not token or not isinstance(token, str):
        raise InvalidTokenError("Token must be a non-empty string.")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Malformed token: expected 3 dot-separated segments.")

    header_b64, payload_b64, sig_b64 = parts
    key = secret_key or get_jwt_secret()

    # 1. Verify header
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256":
            raise InvalidTokenError(f"Unsupported algorithm '{header.get('alg')}'. Expected HS256.")
    except Exception as err:
        raise InvalidTokenError(f"Malformed token header: {err}") from err

    # 2. Verify signature (constant-time check against timing attacks)
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception as err:
        raise InvalidTokenError("Invalid base64url signature encoding.") from err

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise InvalidTokenError("Signature verification failed: invalid token signature.")

    # 3. Decode payload
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as err:
        raise InvalidTokenError(f"Malformed token payload: {err}") from err

    # 4. Check expiration
    now = int(time.time())
    if "exp" in payload:
        try:
            exp_time = int(payload["exp"])
            if now > exp_time:
                raise TokenExpiredError(f"Token expired at timestamp {exp_time} (current time {now}).")
        except (ValueError, TypeError) as err:
            raise InvalidTokenError(f"Malformed 'exp' claim in token: {err}") from err

    return payload


def generate_token(
    user_id: str,
    role: str = "user",
    expires_in: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates a signed HS256 JWT token for an authenticated user."""
    now = int(time.time())
    ttl = expires_in if expires_in is not None else int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))

    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + ttl,
    }
    if extra_claims:
        payload.update(extra_claims)

    return encode_jwt(payload)


def validate_token(token: str) -> Dict[str, Any]:
    """Validates an incoming bearer token and extracts user metadata."""
    payload = decode_jwt(token)
    if "sub" not in payload:
        raise InvalidTokenError("Token missing mandatory subject ('sub') claim.")
    return payload


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieves authenticated user from Flask request context (g.current_user)."""
    try:
        return getattr(g, "current_user", None)
    except Exception:
        return None


def require_auth(roles: Optional[List[str]] = None) -> Callable:
    """
    Decorator for Flask route endpoints enforcing standard Bearer token authentication.
    Validates token presence, format, signature, expiration, and authorized roles.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            auth_enabled = is_auth_enabled()

            if not auth_header:
                if not auth_enabled:
                    # In test/dev mode without mandatory auth, assign default admin user
                    g.current_user = {"user_id": "system_user", "role": "admin"}
                    return fn(*args, **kwargs)
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Missing Bearer token in Authorization header.",
                }), 401

            parts = auth_header.strip().split(" ")
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify({
                    "success": False,
                    "error": "Invalid Authorization header format. Expected 'Bearer <token>'.",
                }), 401

            token = parts[1].strip()
            try:
                claims = validate_token(token)
                g.current_user = {
                    "user_id": claims.get("sub"),
                    "role": claims.get("role", "user"),
                    "claims": claims,
                }
            except TokenExpiredError:
                return jsonify({
                    "success": False,
                    "error": "Authentication failed: token has expired.",
                }), 401
            except InvalidTokenError as err:
                return jsonify({
                    "success": False,
                    "error": f"Authentication failed: {str(err)}",
                }), 401
            except Exception as err:
                logger.error(f"Unexpected error during token authentication: {err}")
                return jsonify({
                    "success": False,
                    "error": "Authentication failed: invalid token.",
                }), 401

            # Role-based access control check
            if roles:
                user_role = g.current_user.get("role", "user")
                if user_role not in roles and user_role != "admin":
                    return jsonify({
                        "success": False,
                        "error": f"Access denied: role '{user_role}' lacks required permissions {roles}.",
                    }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def create_test_auth_headers(user_id: str = "test_admin", role: str = "admin") -> Dict[str, str]:
    """Helper for test suites and scripts to generate valid Authorization headers."""
    token = generate_token(user_id=user_id, role=role, expires_in=3600)
    return {"Authorization": f"Bearer {token}"}

