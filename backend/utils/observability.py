"""Observability, correlation ID tracking, telemetry, and sensitive data redaction."""

import copy
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from flask import Flask, g, request


# Regex patterns matching API keys, tokens, and credentials
REDACTION_PATTERNS = [
    # General sk- and gsk- API keys
    (re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE), "sk-***[REDACTED]***"),
    (re.compile(r"gsk_[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "gsk_***[REDACTED]***"),
    # Google AI API keys
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "AIza***[REDACTED]***"),
    # Bearer authorization tokens
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{10,}", re.IGNORECASE), "Bearer [REDACTED]"),
    # Passwords in connection URLs (postgresql://user:password@host...)
    (re.compile(r"://([^:]+):([^@]+)@"), r"://\1:***@"),
    # Key-value secret assignments in text or logs
    (
        re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|password|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]?([^\s'\"]{4,})['\"]?"),
        r'\1="***[REDACTED]***"',
    ),
]

SENSITIVE_KEY_NAMES = {
    "api_key",
    "apikey",
    "secret_key",
    "secret",
    "password",
    "token",
    "access_token",
    "authorization",
    "gemini_api_key",
    "groq_api_key",
    "openrouter_api_key",
    "cohere_api_key",
    "openai_api_key",
}


def redact_sensitive_text(text: str) -> str:
    """Masks secret tokens, credentials, and passwords within arbitrary text."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern, replacement in REDACTION_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_sensitive_dict(data: Any) -> Any:
    """Recursively masks sensitive dictionary values and strings."""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(s in str(key).lower() for s in SENSITIVE_KEY_NAMES):
                sanitized[key] = "***[REDACTED]***"
            else:
                sanitized[key] = redact_sensitive_dict(value)
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]
    elif isinstance(data, str):
        return redact_sensitive_text(data)
    return data


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts API keys, credentials, and connection strings from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_text(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def get_correlation_id() -> str:
    """Returns the current request correlation ID from Flask g, or generates a new one."""
    try:
        if hasattr(g, "correlation_id") and g.correlation_id:
            return g.correlation_id
    except Exception:
        pass
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Sets the correlation ID on Flask g."""
    try:
        g.correlation_id = correlation_id
    except Exception:
        pass


class ExecutionTelemetry:
    """Structured execution telemetry captured during debate and workflow invocations."""

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        workflow_duration_ms: float = 0.0,
        retrieval_duration_ms: float = 0.0,
        chunks_retrieved_count: int = 0,
        provider_requested: Optional[str] = None,
        provider_used: Optional[str] = None,
        model_used: Optional[str] = None,
        fallback_events: Optional[List[Dict[str, Any]]] = None,
        cache_hit: bool = False,
        cache_hit_type: Optional[str] = None,
        error_category: Optional[str] = None,
        status: str = "completed",
    ):
        self.correlation_id = correlation_id or get_correlation_id()
        self.workflow_duration_ms = round(workflow_duration_ms, 2)
        self.retrieval_duration_ms = round(retrieval_duration_ms, 2)
        self.chunks_retrieved_count = chunks_retrieved_count
        self.provider_requested = provider_requested
        self.provider_used = provider_used
        self.model_used = model_used
        self.fallback_events = fallback_events or []
        self.cache_hit = cache_hit
        self.cache_hit_type = cache_hit_type
        self.error_category = error_category
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "workflow_duration_ms": self.workflow_duration_ms,
            "retrieval_duration_ms": self.retrieval_duration_ms,
            "chunks_retrieved_count": self.chunks_retrieved_count,
            "provider_requested": self.provider_requested,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "fallback_events": self.fallback_events,
            "cache_hit": self.cache_hit,
            "cache_hit_type": self.cache_hit_type,
            "error_category": self.error_category,
            "status": self.status,
        }


def init_observability(app: Flask) -> None:
    """Initializes correlation ID middleware and log redaction on the Flask application."""
    filter_instance = SensitiveDataFilter()
    app.logger.addFilter(filter_instance)
    logging.getLogger().addFilter(filter_instance)

    @app.before_request
    def before_request_observability():
        incoming_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        if incoming_id and re.match(r"^[a-zA-Z0-9_\-]{4,64}$", incoming_id):
            g.correlation_id = incoming_id
        else:
            g.correlation_id = str(uuid.uuid4())
        g.request_start_time = time.time()

    @app.after_request
    def after_request_observability(response):
        correlation_id = getattr(g, "correlation_id", None)
        if correlation_id:
            response.headers["X-Correlation-ID"] = correlation_id

        # Calculate request latency
        start_time = getattr(g, "request_start_time", None)
        if start_time:
            latency_ms = (time.time() - start_time) * 1000.0
            app.logger.info(
                f"[{correlation_id}] {request.method} {request.path} {response.status_code} ({latency_ms:.1f}ms)"
            )
        return response

