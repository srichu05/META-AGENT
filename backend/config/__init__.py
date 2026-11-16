"""Draft 2 configuration package with legacy-compatible exports."""

from .settings import (
    AGENT_ROLES,
    API_CONFIG,
    API_INSTRUCTIONS,
    CACHE_CONFIG,
    EVALUATOR_CONFIG,
    INGESTION_CONFIG,
    PROBLEM_TYPES,
    RAG_CONFIG,
    SYSTEM_CONFIG,
    get_config_status,
    is_valid_api_key,
    print_config_status,
)
from .validator import (
    get_cors_origins,
    mask_database_url,
    validate_startup_config,
)

__all__ = [
    "AGENT_ROLES",
    "API_CONFIG",
    "API_INSTRUCTIONS",
    "CACHE_CONFIG",
    "EVALUATOR_CONFIG",
    "INGESTION_CONFIG",
    "PROBLEM_TYPES",
    "RAG_CONFIG",
    "SYSTEM_CONFIG",
    "get_config_status",
    "get_cors_origins",
    "is_valid_api_key",
    "mask_database_url",
    "print_config_status",
    "validate_startup_config",
]
