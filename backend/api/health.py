"""Dedicated health, readiness, and diagnostics API blueprint."""

from datetime import datetime
import os
import platform
import sys
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify

from config import (
    CACHE_CONFIG,
    INGESTION_CONFIG,
    SYSTEM_CONFIG,
    get_config_status,
)
from database import check_database_connectivity, check_migration_status
from ingestion.faiss_store import FAISSVectorStore
from ingestion.recovery import check_index_consistency
from security import require_auth
from utils.observability import get_correlation_id, redact_sensitive_dict

health_blueprint = Blueprint("health_api", __name__, url_prefix="/api/health")


@health_blueprint.route("/live", methods=["GET"])
def liveness():
    """
    Lightweight process liveness probe.
    Does not execute database queries, embedding generation, or LLM calls.
    Returns HTTP 200 as long as the Flask server process is responding.
    """
    cid = get_correlation_id()
    return jsonify({
        "status": "alive",
        "service": "meta-agent-math-debate",
        "correlation_id": cid,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }), 200


@health_blueprint.route("/ready", methods=["GET"])
def readiness():
    """
    Comprehensive readiness probe.
    Validates database connectivity, migration status, FAISS index integrity,
    semantic cache status, and configured LLM providers.
    Returns HTTP 200 if ready to serve traffic, or HTTP 503 if degraded/unhealthy.
    """
    cid = get_correlation_id()
    now_iso = datetime.utcnow().isoformat() + "Z"

    # 1. Database connectivity check
    db_status = check_database_connectivity()

    # 2. Database migration status
    mig_status = check_migration_status()

    # 3. FAISS index integrity check
    faiss_path = INGESTION_CONFIG.get("faiss_index_path")
    dimension = SYSTEM_CONFIG.get("embedding_dimension", 384)
    faiss_store = FAISSVectorStore(faiss_path, expected_dimension=dimension)
    faiss_status = faiss_store.verify_integrity()

    # 4. Semantic cache status
    cache_status = {
        "enabled": CACHE_CONFIG.get("enabled", True),
        "namespace": CACHE_CONFIG.get("namespace", "math_debate"),
        "similarity_threshold": CACHE_CONFIG.get("similarity_threshold", 0.92),
    }

    # 5. Providers configuration status
    providers_status = get_config_status()

    # Determine overall system health
    # System is ready if database is connected and FAISS index is structurally valid
    is_healthy = bool(db_status.get("connected")) and bool(faiss_status.get("valid"))

    payload = {
        "status": "ready" if is_healthy else "unready",
        "healthy": is_healthy,
        "correlation_id": cid,
        "database": db_status,
        "migrations": mig_status,
        "faiss_index": faiss_status,
        "cache": cache_status,
        "providers": {
            "configured_count": providers_status.get("configured_count", 0),
            "is_usable": providers_status.get("is_usable", False),
        },
        "timestamp": now_iso,
    }

    status_code = 200 if is_healthy else 503
    return jsonify(payload), status_code


@health_blueprint.route("/diagnostics", methods=["GET"])
@require_auth(roles=["admin"])
def diagnostics():
    """
    System diagnostics endpoint returning runtime metrics, index stats,
    pool configuration, and provider router metrics without exposing secrets.
    """
    cid = get_correlation_id()
    now_iso = datetime.utcnow().isoformat() + "Z"

    # Consistency reconciliation between DB chunks and FAISS
    consistency = check_index_consistency()

    # Cache metrics
    cache_metrics: Dict[str, Any] = {"active": False}
    try:
        graph = current_app.extensions.get("math_debate_graph")
        if graph and graph.cache_service:
            cache_metrics = {
                "active": True,
                "stats": graph.cache_service.get_stats(),
            }
    except Exception as e:
        cache_metrics = {"active": False, "error": str(e)}

    # Provider router metrics
    provider_metrics: Dict[str, Any] = {}
    try:
        from providers.router import ProviderRouter
        router = ProviderRouter()
        provider_metrics = router.get_metrics_summary()
    except Exception as e:
        provider_metrics = {"error": str(e)}

    # Redacted system configurations
    redacted_system_cfg = redact_sensitive_dict(dict(SYSTEM_CONFIG))
    # Never leak raw database password or secret key
    if "secret_key" in redacted_system_cfg:
        redacted_system_cfg["secret_key"] = "***[REDACTED]***"

    engine_pool_info: Dict[str, Any] = {}
    try:
        from database.extensions import db
        pool = db.engine.pool
        engine_pool_info = {
            "dialect": db.engine.dialect.name,
            "pool_class": pool.__class__.__name__,
            "pool_size": getattr(pool, "size", lambda: None)(),
            "checked_in": getattr(pool, "checkedin", lambda: None)(),
            "checked_out": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", lambda: None)(),
        }
    except Exception:
        engine_pool_info = {"status": "unavailable"}

    return jsonify({
        "service": "meta-agent-math-debate",
        "correlation_id": cid,
        "timestamp": now_iso,
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "environment": os.getenv("FLASK_ENV", "development"),
            "debug": os.getenv("DEBUG", "False").lower() in ("true", "1", "yes"),
        },
        "database_pool": engine_pool_info,
        "index_consistency": consistency,
        "cache": cache_metrics,
        "provider_telemetry": provider_metrics,
        "system_config": redacted_system_cfg,
    }), 200

