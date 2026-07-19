"""Minimal Draft 2 persistence model used to validate database wiring."""

from database.extensions import db


class SystemSetting(db.Model):
    """Example metadata record; domain models are deferred to later phases."""

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), nullable=False, unique=True, index=True)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )
