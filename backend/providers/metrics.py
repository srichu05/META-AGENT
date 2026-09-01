"""Provider Metrics Collector - Records latency, token usage, cost, and failure metrics for LLM calls."""

import logging, time
from typing import Any, Dict, List

from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


class ProviderMetrics:
    """In-memory metrics collector tracking latency, token usage, costs, and failures per provider."""

    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._call_logs: List[Dict[str, Any]] = []

    def record_call(self, response: ProviderResponse, retries: int = 0) -> None:
        """Record a single provider call response."""
        provider = response.provider or "UNKNOWN"
        model = response.model or "UNKNOWN"
        key = f"{provider}:{model}"

        if key not in self._metrics:
            self._metrics[key] = {
                "provider": provider,
                "model": model,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "retries": 0,
                "total_latency_ms": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
            }

        m = self._metrics[key]
        m["total_calls"] += 1
        m["retries"] += retries
        m["total_latency_ms"] += response.latency_ms

        if response.success:
            m["successful_calls"] += 1
            tokens = response.token_usage or {}
            m["prompt_tokens"] += tokens.get("prompt_tokens", 0)
            m["completion_tokens"] += tokens.get("completion_tokens", 0)
            m["total_tokens"] += tokens.get("total_tokens", 0)
            m["estimated_cost"] += response.estimated_cost
        else:
            m["failed_calls"] += 1

        log_entry = {
            "timestamp": time.time(),
            "provider": provider,
            "model": model,
            "success": response.success,
            "latency_ms": response.latency_ms,
            "cost": response.estimated_cost,
            "error": response.error,
        }
        self._call_logs.append(log_entry)
        if len(self._call_logs) > 500:
            self._call_logs.pop(0)

    def get_summary(self) -> Dict[str, Any]:

        """Returns aggregated summary metrics for all providers."""
        summary = {}
        for key, m in self._metrics.items():
            total = m["total_calls"]
            avg_latency = m["total_latency_ms"] / total if total > 0 else 0.0
            success_rate = (m["successful_calls"] / total * 100) if total > 0 else 0.0

            summary[key] = {
                "provider": m["provider"],
                "model": m["model"],
                "total_calls": total,
                "success_rate": round(success_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "total_tokens": m["total_tokens"],
                "total_cost": round(m["estimated_cost"], 6),
                "failures": m["failed_calls"],
                "retries": m["retries"],
            }
        return summary
