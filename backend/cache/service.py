"""Production-grade Semantic Cache Service with exact and vector similarity lookups."""

from datetime import datetime, timedelta
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import CACHE_CONFIG, SYSTEM_CONFIG
from database.extensions import db
from graph.state import DebateGraphState
from ingestion.embeddings import BGEEmbeddingService
from models.semantic_cache import SemanticCacheEntry

from .eligibility import CacheEligibilityPolicy
from .normalization import (
    compute_context_hash,
    compute_query_hash,
    compute_scope_hash,
    normalize_query,
)
from .safeguards import (
    MathEquivalenceValidator,
    extract_numbers,
    extract_operators,
    extract_units,
)
from .types import CacheEntry, CacheResult, CacheStats

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    Two-tier (Memory + PostgreSQL) semantic cache for math debate workflows.
    Ensures zero false-positive math hits via conservative invariant checks.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        embedding_service: Optional[BGEEmbeddingService] = None,
    ):
        self.config = config or dict(CACHE_CONFIG)
        self.stats = CacheStats()

        self._embedding_service = embedding_service
        self._memory_entries: Dict[str, CacheEntry] = {}
        self._memory_vectors: Dict[str, np.ndarray] = {}
        self._initialized_from_db = False

        logger.info(
            f"🧠 SemanticCacheService initialized: enabled={self.is_enabled()}, "
            f"threshold={self.config.get('similarity_threshold', 0.92)}, "
            f"max_entries={self.config.get('max_entries', 1000)}"
        )

    def is_enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    @property
    def embedding_service(self) -> BGEEmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = BGEEmbeddingService(
                model_name=SYSTEM_CONFIG.get("embedding_model", "BAAI/bge-small-en-v1.5"),
                batch_size=1,
                expected_dimension=SYSTEM_CONFIG.get("embedding_dimension", 384),
            )
        return self._embedding_service

    def _sync_from_db_if_needed(self) -> None:
        """Loads non-expired records from PostgreSQL into hot memory index."""
        if self._initialized_from_db:
            return

        try:
            now = datetime.utcnow()
            active_records = db.session.query(SemanticCacheEntry).filter(
                SemanticCacheEntry.is_valid.is_(True),
                (SemanticCacheEntry.expires_at.is_(None)) | (SemanticCacheEntry.expires_at > now),
            ).all()

            for rec in active_records:
                vec = None
                if rec.embedding:
                    vec = np.frombuffer(rec.embedding, dtype=np.float32)

                entry = CacheEntry(
                    id=rec.id,
                    query=rec.query,
                    normalized_query=rec.normalized_query,
                    query_hash=rec.query_hash,
                    scope_hash=rec.scope_hash,
                    context_hash=rec.context_hash,
                    embedding=vec,
                    final_answer=rec.final_answer,
                    response_payload=rec.response_payload or {},
                    provider=rec.provider,
                    model=rec.model,
                    prompt_version=rec.prompt_version,
                    schema_version=rec.schema_version,
                    number_signature=rec.number_signature,
                    operator_signature=rec.operator_signature,
                    unit_signature=rec.unit_signature,
                    hit_count=rec.hit_count,
                    execution_time_ms=rec.execution_time_ms,
                    created_at=rec.created_at,
                    last_accessed_at=rec.last_accessed_at,
                    expires_at=rec.expires_at,
                    is_valid=rec.is_valid,
                )
                self._memory_entries[rec.id] = entry
                if vec is not None and vec.shape[0] == SYSTEM_CONFIG.get("embedding_dimension", 384):
                    self._memory_vectors[rec.id] = vec

            self._initialized_from_db = True
            logger.info(f"💾 Synced {len(self._memory_entries)} cached records from PostgreSQL.")
        except Exception as error:
            # Running outside Flask request context or DB not ready
            logger.debug(f"Cache DB sync bypassed ({error}). Operating in local mode.")
            self._initialized_from_db = True

    def get(self, query: str, context: Optional[Any] = None, user_id: Optional[str] = None) -> Optional[CacheResult]:
        """
        Retrieves a cached debate result using exact or semantic match.
        Returns CacheResult if valid hit, or None if miss / rejected.
        """
        if not self.is_enabled() or not query or not query.strip():
            return None

        self._sync_from_db_if_needed()

        normalized = normalize_query(query)
        scope_hash = compute_scope_hash(
            namespace=self.config.get("namespace", "math_debate"),
            schema_version=self.config.get("schema_version", "v1.0"),
            user_id=user_id,
        )
        query_hash = compute_query_hash(normalized, scope_hash)
        context_hash = compute_context_hash(context)
        now = datetime.utcnow()

        # 1. Tier 1: Exact Match Lookup (O(1) Hash Match)
        if self.config.get("exact_match_enabled", True):
            for entry_id, entry in list(self._memory_entries.items()):
                if entry.query_hash == query_hash and entry.scope_hash == scope_hash and entry.is_valid:
                    if entry.expires_at and entry.expires_at < now:
                        self._evict_entry(entry_id)
                        continue

                    # Context consistency check
                    if entry.context_hash and entry.context_hash != context_hash:
                        continue

                    # Exact Hit!
                    self.stats.exact_hits += 1
                    self.stats.latency_saved_ms_total += entry.execution_time_ms
                    entry.hit_count += 1
                    entry.last_accessed_at = now
                    self._update_db_access(entry.id, entry.hit_count, now)

                    logger.info(
                        f"⚡ [Cache EXACT HIT] Query: '{query[:50]}...' -> "
                        f"Saved {entry.execution_time_ms:.1f}ms (hit #{entry.hit_count})"
                    )
                    return CacheResult(
                        hit=True,
                        hit_type="exact",
                        similarity=1.0,
                        entry=entry,
                    )

        # 2. Tier 2: Semantic Similarity Lookup (Cosine Similarity + Math Invariants)
        similarity_threshold = float(self.config.get("similarity_threshold", 0.92))
        if self._memory_vectors:
            try:
                query_vec = self.embedding_service.generate([normalized])[0]
                norm_q = np.linalg.norm(query_vec)
                if norm_q > 0:
                    query_vec = query_vec / norm_q

                best_sim = -1.0
                best_entry_id = None

                for candidate_id, cand_vec in self._memory_vectors.items():
                    entry = self._memory_entries.get(candidate_id)
                    if not entry or not entry.is_valid:
                        continue
                    if entry.scope_hash != scope_hash:
                        continue
                    if entry.expires_at and entry.expires_at < now:
                        continue

                    # Inner product (both are L2 normalized)
                    sim = float(np.dot(query_vec, cand_vec))
                    if sim > best_sim:
                        best_sim = sim
                        best_entry_id = candidate_id

                if best_entry_id and best_sim >= similarity_threshold:
                    candidate = self._memory_entries[best_entry_id]

                    # Enforce strict mathematical equivalence safeguards
                    is_equiv, reject_reason = MathEquivalenceValidator.validate_semantic_equivalence(
                        normalized,
                        candidate.normalized_query,
                        context_hash_a=context_hash,
                        context_hash_b=candidate.context_hash,
                    )

                    if is_equiv:
                        self.stats.semantic_hits += 1
                        self.stats.latency_saved_ms_total += candidate.execution_time_ms
                        candidate.hit_count += 1
                        candidate.last_accessed_at = now
                        self._update_db_access(candidate.id, candidate.hit_count, now)

                        logger.info(
                            f"🎯 [Cache SEMANTIC HIT (sim={best_sim:.4f})] "
                            f"Matched: '{candidate.query[:40]}...' -> "
                            f"Saved {candidate.execution_time_ms:.1f}ms"
                        )
                        return CacheResult(
                            hit=True,
                            hit_type="semantic",
                            similarity=best_sim,
                            entry=candidate,
                        )
                    else:
                        self.stats.rejected_semantic_matches += 1
                        logger.info(
                            f"🛡️ [Cache Safeguard Rejection] Similarity was {best_sim:.4f} "
                            f"but rejected: {reject_reason}"
                        )
            except Exception as error:
                self.stats.cache_errors += 1
                logger.warning(f"Semantic cache similarity search error: {error}")

        # 3. Cache Miss
        self.stats.misses += 1
        return None

    def set(
        self,
        query: str,
        state: DebateGraphState,
        context: Optional[Any] = None,
        execution_time_ms: float = 0.0,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Stores an eligible, validated debate execution into memory and PostgreSQL.
        Returns True if cached, False if rejected or disabled.
        """
        if not self.is_enabled() or not query or not query.strip():
            return False

        # Enforce eligibility policy
        is_eligible, reason = CacheEligibilityPolicy.is_eligible(
            state,
            require_grounded_citations=self.config.get("require_grounded_citations", True),
        )
        if not is_eligible:
            logger.info(f"🚫 [Cache Store Ineligible]: {reason}")
            return False

        try:
            self._sync_from_db_if_needed()

            effective_user_id = user_id or state.get("user_id")
            normalized = normalize_query(query)
            scope_hash = compute_scope_hash(
                namespace=self.config.get("namespace", "math_debate"),
                schema_version=self.config.get("schema_version", "v1.0"),
                user_id=effective_user_id,
            )
            query_hash = compute_query_hash(normalized, scope_hash)
            context_hash = compute_context_hash(context or state.get("retrieved_context"))

            # Extract provider & model provenance
            judge_out = state.get("judge_output") or {}
            best_agent = judge_out.get("best_agent", "solver_1")
            solvers = state.get("solver_outputs") or {}
            winning_solver = solvers.get(best_agent, {})

            provider = winning_solver.get("actual_provider") or "GEMINI"
            model = winning_solver.get("actual_model") or "gemini-2.5-flash"
            final_answer = state.get("final_answer") or judge_out.get("best_solution", "")

            # Generate BGE embedding vector
            vec = self.embedding_service.generate([normalized])[0]
            norm_v = np.linalg.norm(vec)
            if norm_v > 0:
                vec = vec / norm_v

            entry_id = str(uuid.uuid4())
            now = datetime.utcnow()
            ttl_sec = int(self.config.get("ttl_seconds", 604800))
            expires_at = now + timedelta(seconds=ttl_sec) if ttl_sec > 0 else None

            # Structural signatures
            num_sig = ",".join(str(n) for n in extract_numbers(normalized))
            op_sig = ",".join(extract_operators(normalized))
            unit_sig = ",".join(extract_units(normalized))

            # In-memory entry
            entry = CacheEntry(
                id=entry_id,
                query=query,
                normalized_query=normalized,
                query_hash=query_hash,
                scope_hash=scope_hash,
                context_hash=context_hash,
                embedding=vec,
                final_answer=final_answer,
                response_payload=dict(state),
                provider=provider,
                model=model,
                prompt_version=self.config.get("schema_version", "v1.0"),
                schema_version=self.config.get("schema_version", "1.0"),
                number_signature=num_sig,
                operator_signature=op_sig,
                unit_signature=unit_sig,
                hit_count=0,
                execution_time_ms=execution_time_ms,
                created_at=now,
                last_accessed_at=now,
                expires_at=expires_at,
                is_valid=True,
            )

            # Persist to PostgreSQL if in active DB context
            try:
                db_record = SemanticCacheEntry(
                    id=entry_id,
                    query=query,
                    normalized_query=normalized,
                    query_hash=query_hash,
                    scope_hash=scope_hash,
                    context_hash=context_hash,
                    embedding=vec.astype(np.float32).tobytes(),
                    final_answer=final_answer,
                    response_payload=dict(state),
                    provider=provider,
                    model=model,
                    prompt_version=entry.prompt_version,
                    schema_version=entry.schema_version,
                    number_signature=num_sig,
                    operator_signature=op_sig,
                    unit_signature=unit_sig,
                    hit_count=0,
                    execution_time_ms=execution_time_ms,
                    created_at=now,
                    last_accessed_at=now,
                    expires_at=expires_at,
                    is_valid=True,
                )
                db.session.add(db_record)
                db.session.commit()
            except Exception as db_err:
                logger.debug(f"DB persistence bypassed for cache entry: {db_err}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

            self._memory_entries[entry_id] = entry
            self._memory_vectors[entry_id] = vec

            self._evict_if_needed()

            logger.info(f"💾 [Cache Stored] Query: '{query[:50]}...' -> Entry ID: {entry_id[:8]}")
            return True

        except Exception as error:
            self.stats.cache_errors += 1
            logger.warning(f"Failed to store entry in semantic cache: {error}")
            return False

    def invalidate(self, query_or_key: str) -> bool:
        """Invalidates a cache entry by ID or query text."""
        normalized = normalize_query(query_or_key)
        found = False

        for entry_id, entry in list(self._memory_entries.items()):
            if entry_id == query_or_key or entry.normalized_query == normalized or entry.query == query_or_key:
                entry.is_valid = False
                self._evict_entry(entry_id)
                found = True

        try:
            records = db.session.query(SemanticCacheEntry).filter(
                (SemanticCacheEntry.id == query_or_key)
                | (SemanticCacheEntry.normalized_query == normalized)
                | (SemanticCacheEntry.query == query_or_key)
            ).all()
            for r in records:
                r.is_valid = False
            db.session.commit()
            found = True
        except Exception:
            pass

        return found

    def clear(self) -> int:
        """Clears all entries from both memory and PostgreSQL."""
        count = len(self._memory_entries)
        self._memory_entries.clear()
        self._memory_vectors.clear()

        try:
            deleted = db.session.query(SemanticCacheEntry).delete()
            db.session.commit()
            count = max(count, deleted)
        except Exception as db_err:
            logger.debug(f"DB cache clear error ({db_err})")

        logger.info(f"🧹 Semantic cache cleared ({count} entries removed).")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Returns observable counters, hit rates, and latency savings."""
        return self.stats.to_dict(active_entries=len(self._memory_entries))

    def _evict_entry(self, entry_id: str) -> None:
        self._memory_entries.pop(entry_id, None)
        self._memory_vectors.pop(entry_id, None)

    def _evict_if_needed(self) -> None:
        """Evicts oldest / least recently accessed entries if capacity exceeded."""
        max_entries = int(self.config.get("max_entries", 1000))
        if len(self._memory_entries) <= max_entries:
            return

        excess = len(self._memory_entries) - max_entries
        # Sort by last_accessed_at ascending
        sorted_entries = sorted(
            self._memory_entries.items(),
            key=lambda item: item[1].last_accessed_at or datetime.min,
        )

        for i in range(excess):
            evict_id, _ = sorted_entries[i]
            self._evict_entry(evict_id)
            self.stats.evictions += 1

            try:
                rec = db.session.get(SemanticCacheEntry, evict_id)
                if rec:
                    db.session.delete(rec)
                    db.session.commit()
            except Exception:
                pass

        logger.info(f"🗑️ Evicted {excess} oldest cache entries to maintain max capacity ({max_entries}).")

    def _update_db_access(self, entry_id: str, hit_count: int, accessed_at: datetime) -> None:
        try:
            rec = db.session.get(SemanticCacheEntry, entry_id)
            if rec:
                rec.hit_count = hit_count
                rec.last_accessed_at = accessed_at
                db.session.commit()
        except Exception:
            pass
