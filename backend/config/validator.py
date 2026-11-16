"""Startup configuration validation and security checks for deployment readiness."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .settings import API_CONFIG, INGESTION_CONFIG, SYSTEM_CONFIG, is_valid_api_key


INSECURE_SECRET_DEFAULTS = {
    "dev-fallback-key-change-in-production",
    "secret",
    "secret_key",
    "changeme",
    "change-me",
    "default",
    "123456",
    "password",
}


def mask_database_url(url: Optional[str]) -> str:
    """Masks credentials in database connection URLs for safe logging and diagnostics."""
    if not url:
        return "not-configured"
    try:
        # Regex replacement for password in URI schemes: scheme://user:pass@host:port/db
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)
    except Exception:
        return "[MASKED_URL]"


def get_cors_origins() -> List[str]:
    """
    Parses ALLOWED_ORIGINS into a clean list of origins for Flask-CORS.
    Supports wildcard '*', comma-separated lists, and sane development defaults.
    """
    origins_cfg = os.getenv("ALLOWED_ORIGINS") or SYSTEM_CONFIG.get("ALLOWED_ORIGINS", "*")
    if isinstance(origins_cfg, list):
        return [str(o).strip() for o in origins_cfg if str(o).strip()]

    origins_str = str(origins_cfg).strip()
    if origins_str == "*":
        return ["*"]

    parsed = [o.strip() for o in origins_str.split(",") if o.strip()]
    if parsed:
        return parsed

    # Default fallback for local testing
    return [
        "http://127.0.0.1:5501",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def validate_startup_config() -> Dict[str, Any]:
    """
    Validates startup configuration and environment settings.
    Ensures safe defaults, validates database URI, verifies path accessibility,
    and forbids insecure configurations in production mode.
    """
    flask_env = os.getenv("FLASK_ENV", "development").lower()
    is_production = flask_env in ("production", "prod")
    debug_val = os.getenv("DEBUG", "False" if is_production else "True")
    debug_mode = debug_val.strip().lower() in ("1", "true", "yes")

    errors: List[str] = []
    warnings: List[str] = []

    # 1. Database URL validation
    db_url = os.getenv("DATABASE_URL") or SYSTEM_CONFIG.get("database_url")
    db_valid = False
    if not db_url:
        errors.append("DATABASE_URL is not configured.")
    else:
        try:
            parsed_url = urlparse(db_url)
            scheme = parsed_url.scheme.lower()
            if scheme.startswith("postgresql") or scheme.startswith("sqlite") or scheme.startswith("mysql"):
                db_valid = True
            else:
                errors.append(f"DATABASE_URL scheme '{scheme}' is unsupported. Expected PostgreSQL or SQLite.")
        except Exception as e:
            errors.append(f"Invalid DATABASE_URL format: {e}")

    # 2. Production Secret Key & Debug Mode Enforcement
    secret_key = os.getenv("SECRET_KEY") or SYSTEM_CONFIG.get("secret_key", "")
    secret_key_valid = True

    if is_production:
        if debug_mode:
            errors.append("DEBUG mode must not be enabled when FLASK_ENV=production.")

        if not secret_key or secret_key.strip() in INSECURE_SECRET_DEFAULTS or len(secret_key.strip()) < 16:
            secret_key_valid = False
            errors.append(
                "SECRET_KEY is insecure or unset for production. Provide a strong secret (at least 16 characters)."
            )
    else:
        if secret_key in INSECURE_SECRET_DEFAULTS:
            warnings.append("Using default development SECRET_KEY. Change this before deploying to production.")

    # 3. Path Accessibility Checks
    upload_folder = Path(SYSTEM_CONFIG.get("upload_folder", "./uploads"))
    try:
        upload_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        warnings.append(f"Could not verify or create upload folder '{upload_folder}': {e}")

    faiss_path = Path(INGESTION_CONFIG.get("faiss_index_path", "./database/document_vectors.faiss"))
    try:
        faiss_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        warnings.append(f"Could not verify or create FAISS directory '{faiss_path.parent}': {e}")

    # 4. Provider Readiness Audit (non-leaking)
    active_providers = []
    for provider, pconfig in API_CONFIG.items():
        if is_valid_api_key(pconfig.get("api_key")):
            active_providers.append(provider)

    if not active_providers:
        warnings.append("No cloud LLM providers configured with valid API keys. Falling back to local/mock adapters.")

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "environment": flask_env,
        "is_production": is_production,
        "debug_mode": debug_mode,
        "database_valid": db_valid,
        "database_url_redacted": mask_database_url(db_url),
        "secret_key_valid": secret_key_valid,
        "active_providers": active_providers,
        "active_provider_count": len(active_providers),
        "cors_origins": get_cors_origins(),
        "warnings": warnings,
        "errors": errors,
    }
