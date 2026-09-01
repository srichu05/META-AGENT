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
            "latency_ms": round(self.latency_ms, 2),
            "token_usage": self.token_usage,
            "estimated_cost": round(self.estimated_cost, 6),
            "error": self.error,
            "metadata": self.metadata,
        }
