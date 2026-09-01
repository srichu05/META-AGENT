"""Base Abstract Provider Adapter interface declaring unified generate contract."""

import abc
from typing import Any, Dict, Optional

from providers.types import ProviderResponse


class BaseProviderAdapter(abc.ABC):
    """Abstract interface exposing unified generation logic for cloud LLM providers."""

    provider_name: str = "BASE"

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.api_key: str = self.config.get("api_key") or ""
        self.base_url: str = self.config.get("base_url") or ""
        self.default_model: str = (
            self.config.get("models", {}).get("default") or "default"
        )

    @property
    def is_configured(self) -> bool:
        """Returns True if the provider API key is present."""
        return bool(self.api_key and self.api_key.strip())

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ProviderResponse:
        """
        Executes generation request against cloud LLM and returns normalized ProviderResponse.
        """
        pass
