"""Provider selection metadata for the future Draft 2 router."""

from typing import Dict, Iterable, Optional

from config import API_CONFIG

from .base import ProviderAdapter
from .cohere import CohereProvider
from .gemini import GeminiProvider
from .groq import GroqProvider


class ProviderRouter:
    """Exposes Draft 2 provider availability without invoking providers."""

    provider_order = ("GEMINI", "GROQ", "COHERE")
    provider_types = {
        "GEMINI": GeminiProvider,
        "GROQ": GroqProvider,
        "COHERE": CohereProvider,
    }

    def __init__(self) -> None:
        self.providers: Dict[str, ProviderAdapter] = {
            name: provider_type(API_CONFIG[name])
            for name, provider_type in self.provider_types.items()
        }

    def configured_providers(self) -> Iterable[ProviderAdapter]:
        return (self.providers[name] for name in self.provider_order if self.providers[name].is_configured)

    def get_provider(self, name: str) -> Optional[ProviderAdapter]:
        return self.providers.get(name.upper())
