"""Relational persistent storage model for semantic cache entries."""

from database.extensions import db


class SemanticCacheEntry(db.Model):
    """Stores exact and semantic cache records for math debate workflow executions."""

    __tablename__ = "semantic_cache"

    id = db.Column(db.String(64), primary_key=True)
    query = db.Column(db.Text, nullable=False)
    normalized_query = db.Column(db.Text, nullable=False)
    query_hash = db.Column(db.String(64), nullable=False, index=True)
    scope_hash = db.Column(db.String(64), nullable=False, index=True)
    context_hash = db.Column(db.String(64), nullable=True, index=True)

    embedding = db.Column(db.LargeBinary, nullable=True)

    final_answer = db.Column(db.Text, nullable=False)
    response_payload = db.Column(db.JSON, nullable=False)

    provider = db.Column(db.String(64), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    prompt_version = db.Column(db.String(32), nullable=False, default="v1.0")
    schema_version = db.Column(db.String(16), nullable=False, default="1.0")

    number_signature = db.Column(db.Text, nullable=True)
    operator_signature = db.Column(db.Text, nullable=True)
    unit_signature = db.Column(db.Text, nullable=True)

    hit_count = db.Column(db.Integer, nullable=False, default=0)
    execution_time_ms = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)
    last_accessed_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    is_valid = db.Column(db.Boolean, nullable=False, default=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "normalized_query": self.normalized_query,
            "query_hash": self.query_hash,
            "scope_hash": self.scope_hash,
            "context_hash": self.context_hash,
            "final_answer": self.final_answer,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "schema_version": self.schema_version,
            "number_signature": self.number_signature,
            "operator_signature": self.operator_signature,
            "unit_signature": self.unit_signature,
            "hit_count": self.hit_count,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid,
        }

