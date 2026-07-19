"""Database initialization for the Draft 2 backend foundation."""

from flask import Flask

from .extensions import db, migrate


def init_database(app: Flask) -> None:
    """Bind SQLAlchemy and Flask-Migrate without opening a database connection."""
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models after extension setup so Flask-Migrate can discover metadata.
    from models.system_setting import SystemSetting  # noqa: F401


__all__ = ["db", "init_database", "migrate"]
