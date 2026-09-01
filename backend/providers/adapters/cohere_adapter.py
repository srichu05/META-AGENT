"""Cohere Provider Adapter - Dedicated to Retrieval Quality and Reranking ONLY."""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from providers.adapters.base import BaseProviderAdapter
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


class CohereAdapter(BaseProviderAdapter):
    """Adapter for Cohere API (rerank-v3.5). RESTRICTED to retrieval reranking."""

    provider_name = "COHERE"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_model = self.config.get("models", {}).get("default", "rerank-v3.5")
        self.base_url = "https://api.cohere.com/v2/rerank"

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ProviderResponse:
        """Cohere is not an LLM solver. Reject generation calls explicitly."""
        return ProviderResponse(
            success=False,
            provider=self.provider_name,
            model=self.default_model,
            error="Cohere API is restricted to document reranking and cannot be used as an LLM solver.",
        )

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 5,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes Cohere Rerank API call."""
        target_model = model or self.default_model
        start_time = time.time()

        if not self.is_configured or not documents:
            return {"success": False, "results": [], "error": "Cohere unconfigured or empty documents."}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": target_model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
        }

        try:
            resp = requests.post(self.base_url, headers=headers, json=payload, timeout=20)
            latency_ms = (time.time() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                return {
                    "success": True,
                    "results": results,
                    "latency_ms": latency_ms,
                    "model": target_model,
                }
            else:
                return {
                    "success": False,
                    "results": [],
                    "latency_ms": latency_ms,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as error:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"CohereAdapter Rerank Exception: {error}", exc_info=True)
            return {"success": False, "results": [], "latency_ms": latency_ms, "error": str(error)}
