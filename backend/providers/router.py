"""Centralized Provider Router gateway with automatic fallback, response normalization, and metrics."""

import logging
from typing import Any, Dict, List, Optional

from config import API_CONFIG
from providers.adapters.base import BaseProviderAdapter
from providers.adapters.cohere_adapter import CohereAdapter
from providers.adapters.gemini_adapter import GeminiAdapter
from providers.adapters.groq_adapter import GroqAdapter
from providers.adapters.openrouter_adapter import OpenRouterAdapter
from providers.metrics import ProviderMetrics
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Central gateway dispatching LLM requests with automatic provider fallback and metrics collection."""

    default_fallback_order = ["GEMINI", "GROQ", "OPENROUTER"]

    def __init__(self, api_config: Optional[Dict[str, Dict[str, Any]]] = None):
        self.config = api_config or API_CONFIG
        self.metrics = ProviderMetrics()
        self.adapters: Dict[str, BaseProviderAdapter] = {}
        self._initialize_adapters()

    def _initialize_adapters(self) -> None:
        """Initialize adapter instances for all configured cloud providers."""
        self.adapters["GEMINI"] = GeminiAdapter(self.config.get("GEMINI", {}))
        self.adapters["GROQ"] = GroqAdapter(self.config.get("GROQ", {}))
        self.adapters["OPENROUTER"] = OpenRouterAdapter(self.config.get("OPENROUTER", {}))
        self.adapters["COHERE"] = CohereAdapter(self.config.get("COHERE", {}))

        configured = [name for name, adapter in self.adapters.items() if adapter.is_configured]
        logger.info(f"🌐 ProviderRouter initialized with active providers: {configured}")

    def validate_providers(self) -> Dict[str, bool]:
        """Validate which provider API keys are configured and ready."""
        status = {name: adapter.is_configured for name, adapter in self.adapters.items()}
        logger.info(f"🔑 Provider validation status: {status}")
        return status

    def get_adapter(self, provider_name: str) -> Optional[BaseProviderAdapter]:
        """Returns the adapter instance for the specified provider."""
        return self.adapters.get(provider_name.upper())

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        target_provider: Optional[str] = None,
        fallback_order: Optional[List[str]] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ProviderResponse:
        """
        Dispatches generation request to target provider with automatic fallback order.
        Fallback sequence: target_provider -> GEMINI -> GROQ -> OPENROUTER.
        """
        order: List[str] = []
        if target_provider and target_provider.upper() in self.adapters:
            order.append(target_provider.upper())

        fallback_seq = fallback_order or self.default_fallback_order
        for p in fallback_seq:
            p_upper = p.upper()
            if p_upper not in order and p_upper != "COHERE":
                order.append(p_upper)

        last_response: Optional[ProviderResponse] = None
        retries = 0

        for provider_name in order:
            adapter = self.adapters.get(provider_name)
            if not adapter or not adapter.is_configured:
                continue

            logger.info(f"📡 ProviderRouter: Dispatching call to '{provider_name}'...")
            res = adapter.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                model=model if provider_name.upper() == target_provider else None,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            self.metrics.record_call(res, retries=retries)

            if res.success:
                logger.info(f"✅ ProviderRouter: Success from '{provider_name}' ({res.latency_ms:.1f}ms).")
                return res

            logger.warning(f"⚠️ ProviderRouter: '{provider_name}' failed ({res.error}). Trying fallback...")
            last_response = res
            retries += 1

        # All configured providers failed
        error_msg = f"All cloud providers in order {order} failed." if last_response else "No configured cloud providers available."
        logger.error(f"❌ ProviderRouter: {error_msg}")

        failed_response = ProviderResponse(
            success=False,
            provider="ROUTER_FALLBACK",
            model="NONE",
            error=error_msg,
        )
        self.metrics.record_call(failed_response, retries=retries)
        return failed_response

    def rerank(self, query: str, documents: List[str], top_n: int = 5) -> Dict[str, Any]:
        """Routes document reranking requests exclusively to the Cohere Rerank adapter."""
        cohere = self.adapters.get("COHERE")
        if isinstance(cohere, CohereAdapter):
            return cohere.rerank(query, documents, top_n=top_n)
        return {"success": False, "results": [], "error": "Cohere adapter not available."}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Returns collected benchmarking metrics for all provider calls."""
        return self.metrics.get_summary()
