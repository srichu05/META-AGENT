"""Provider metadata interface; provider request logic is intentionally deferred."""

from typing import Any, Dict


class ProviderAdapter:
    """Describes a configured cloud provider without making network calls."""

    provider_name = ""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.get("api_key"))
