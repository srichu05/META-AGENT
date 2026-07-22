"""Draft 2 configuration package with legacy-compatible exports."""

from .settings import (
    AGENT_ROLES,
    API_CONFIG,
    API_INSTRUCTIONS,
    INGESTION_CONFIG,
    PROBLEM_TYPES,
    RAG_CONFIG,
    SYSTEM_CONFIG,
    get_config_status,
    is_valid_api_key,
    print_config_status,
)

__all__ = [
    "AGENT_ROLES",
    "API_CONFIG",
    "API_INSTRUCTIONS",
    "INGESTION_CONFIG",
    "PROBLEM_TYPES",
    "RAG_CONFIG",
    "SYSTEM_CONFIG",
    "get_config_status",
    "is_valid_api_key",
    "print_config_status",
]
