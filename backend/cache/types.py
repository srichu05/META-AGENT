"""Data transfer and representation types for the semantic caching layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np

from graph.state import DebateGraphState


@dataclass
class CacheEntry:
    """In-memory representation of a persisted semantic cache record."""

    id: str
    query: str
    normalized_query: str
    query_hash: str
    scope_hash: str
    context_hash: Optional[str]
    embedding: Optional[np.ndarray]
    final_answer: str
    response_payload: Dict[str, Any]
    provider: str
    model: str
    prompt_version: str = "v1.0"
    schema_version: str = "1.0"
    number_signature: Optional[str] = None
    operator_signature: Optional[str] = None
    unit_signature: Optional[str] = None
    hit_count: int = 0
    execution_time_ms: float = 0.0
    created_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
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


@dataclass
class CacheResult:
    """Outcome of a cache query containing matching details and state reconstruction."""

    hit: bool
    hit_type: Optional[str] = None  # "exact" or "semantic"
    similarity: float = 0.0
    entry: Optional[CacheEntry] = None
    reason: Optional[str] = None

    def to_graph_state(self, current_query: str) -> DebateGraphState:
        """
        Reconstructs a valid DebateGraphState from the cached payload.
        Ensures provenance is preserved while explicitly recording cache origin.
        """
        if not self.entry:
            raise ValueError("Cannot construct graph state from an empty cache result.")

        payload = self.entry.response_payload or {}
        now_iso = datetime.utcnow().isoformat()

        # Build clean history preserving past debate history plus explicit cache record
        debate_history = list(payload.get("debate_history") or [])
        cache_log_record = {
            "node": "SemanticCache",
            "timestamp": now_iso,
            "details": {
                "cache_hit": True,
                "hit_type": self.hit_type,
                "similarity_score": round(self.similarity, 4),
                "original_query": self.entry.query,
                "latency_saved_ms": self.entry.execution_time_ms,
                "cached_at": self.entry.created_at.isoformat() if self.entry.created_at else None,
                "original_provider": self.entry.provider,
                "original_model": self.entry.model,
                "prompt_version": self.entry.prompt_version,
            },
        }
        debate_history.append(cache_log_record)

        state: DebateGraphState = {
            "query": current_query,
            "planner_output": payload.get("planner_output", {}),
            "retrieved_context": payload.get("retrieved_context", {}),
            "managed_context": payload.get("managed_context", {}),
            "solver_outputs": payload.get("solver_outputs", {}),
            "reflection_output": payload.get("reflection_output", {}),
            "judge_output": payload.get("judge_output", {}),
            "citations": payload.get("citations", []),
            "final_answer": self.entry.final_answer or payload.get("final_answer", ""),
            "debate_history": debate_history,
            "current_node": "SemanticCache",
            "error": None,
            "execution_mode": "semantic_cache",
            "partial_execution": False,
            "failed_node": None,
        }

        # Cache-specific metadata fields
        state["is_cached"] = True
        state["cache_hit_type"] = self.hit_type
        state["cache_similarity"] = float(round(self.similarity, 4))
        state["cached_at"] = self.entry.created_at.isoformat() if self.entry.created_at else now_iso
        state["cached_query"] = self.entry.query
        state["latency_saved_ms"] = float(self.entry.execution_time_ms)
        state["cache_id"] = self.entry.id

        return state


@dataclass
class CacheStats:
    """Observable metrics and operational counters for semantic caching."""

    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    rejected_semantic_matches: int = 0
    evictions: int = 0
    cache_errors: int = 0
    latency_saved_ms_total: float = 0.0

    def to_dict(self, active_entries: int = 0) -> Dict[str, Any]:
        total_hits = self.exact_hits + self.semantic_hits
        total_lookups = total_hits + self.misses
        hit_rate = round(total_hits / total_lookups, 4) if total_lookups > 0 else 0.0

        return {
            "enabled": True,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "total_hits": total_hits,
            "misses": self.misses,
            "rejected_semantic_matches": self.rejected_semantic_matches,
            "evictions": self.evictions,
            "cache_errors": self.cache_errors,
            "total_lookups": total_lookups,
            "hit_rate": hit_rate,
            "latency_saved_ms_total": round(self.latency_saved_ms_total, 2),
            "latency_saved_sec": round(self.latency_saved_ms_total / 1000.0, 3),
            "active_entries_count": active_entries,
        }

