"""Standardized Provider Response types for normalized LLM output across all cloud adapters."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProviderResponse:
    """Normalized response object returned by all cloud provider adapters."""

    success: bool
    answer: str = ""
    reasoning: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    provider: str = "UNKNOWN"
    model: str = "UNKNOWN"
    latency_ms: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    estimated_cost: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    intended_provider: Optional[str] = None
    actual_provider: str = "UNKNOWN"
    actual_model: str = "UNKNOWN"
    fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    attempts: int = 1
    error_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert ProviderResponse to standard dictionary for serialization."""
        return {
            "success": self.success,
            "answer": self.answer,
            "reasoning": self.reasoning,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "intended_provider": self.intended_provider or self.provider,
            "actual_provider": self.actual_provider if self.actual_provider != "UNKNOWN" else self.provider,
            "actual_model": self.actual_model if self.actual_model != "UNKNOWN" else self.model,
            "fallback_occurred": self.fallback_occurred,
            "fallback_reason": self.fallback_reason,
            "attempts": self.attempts,
            "error_category": self.error_category,
            "latency_ms": round(self.latency_ms, 2),
            "token_usage": self.token_usage,
            "estimated_cost": round(self.estimated_cost, 6),
            "error": self.error,
            "metadata": self.metadata,
        }
