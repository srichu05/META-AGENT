"""Database connectivity and migration status diagnostics for deployment readiness."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .extensions import db


def check_database_connectivity(timeout_seconds: int = 3) -> Dict[str, Any]:
    """
    Performs a lightweight connectivity check ('SELECT 1') against the configured database.
    Captures execution latency in milliseconds without leaking credentials.
    """
    start_time = time.time()
    try:
        # Execute query within engine execution options if timeout is supported
        result = db.session.execute(text("SELECT 1")).scalar()
        elapsed_ms = (time.time() - start_time) * 1000.0

        dialect_name = "unknown"
        try:
            dialect_name = db.engine.dialect.name
        except Exception:
            pass

        return {
            "connected": True,
            "latency_ms": round(elapsed_ms, 2),
            "dialect": dialect_name,
            "query_result": result,
            "error": None,
        }
    except Exception as error:
        elapsed_ms = (time.time() - start_time) * 1000.0
        return {
            "connected": False,
            "latency_ms": round(elapsed_ms, 2),
            "dialect": "unknown",
            "query_result": None,
            "error": str(error),
        }


def check_migration_status(migrations_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Inspects Alembic migration heads vs current database revision.
    Determines if the database schema is up-to-date, pending, or unversioned.
    """
    if migrations_dir is None:
        backend_dir = Path(__file__).resolve().parents[1]
        migrations_dir = str(backend_dir / "migrations")

    heads: List[str] = []
    try:
        from alembic.script import ScriptDirectory

        script_dir = ScriptDirectory(migrations_dir)
        heads = script_dir.get_heads()
    except Exception as err:
        return {
            "status": "error",
            "is_up_to_date": False,
            "current_revision": None,
            "head_revision": None,
            "error": f"Failed to load Alembic script directory: {err}",
        }

    head_revision = heads[0] if heads else None

    # Query current revision from alembic_version table
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        current_revision = result[0] if result else None
    except Exception:
        # Table might not exist yet (unversioned database)
        current_revision = None

    if not heads:
        return {
            "status": "no_migrations",
            "is_up_to_date": True,
            "current_revision": current_revision,
            "head_revision": None,
        }

    if current_revision is None:
        return {
            "status": "unversioned",
            "is_up_to_date": False,
            "current_revision": None,
            "head_revision": head_revision,
        }

    if current_revision in heads:
        return {
            "status": "up_to_date",
            "is_up_to_date": True,
            "current_revision": current_revision,
            "head_revision": head_revision,
        }

    return {
        "status": "pending",
        "is_up_to_date": False,
        "current_revision": current_revision,
        "head_revision": head_revision,
    }

