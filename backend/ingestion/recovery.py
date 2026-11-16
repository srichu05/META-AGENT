"""FAISS vector store integrity, consistency reconciliation, and disaster recovery."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from config import INGESTION_CONFIG, SYSTEM_CONFIG
from database.extensions import db
from models.document import DocumentChunk

from .embeddings import BGEEmbeddingService
from .exceptions import VectorStorageError
from .faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def check_index_consistency(vector_store: Optional[FAISSVectorStore] = None) -> Dict[str, Any]:
    """
    Reconciles the number of vectors in FAISS against the number of DocumentChunk records in PostgreSQL.
    Returns consistency status and discrepancy metrics.
    """
    if vector_store is None:
        index_path = INGESTION_CONFIG.get("faiss_index_path")
        dimension = SYSTEM_CONFIG.get("embedding_dimension", 384)
        vector_store = FAISSVectorStore(index_path, expected_dimension=dimension)

    try:
        db_chunks = db.session.query(db.func.count(DocumentChunk.id)).scalar() or 0
    except Exception as db_err:
        logger.error(f"Failed to query DocumentChunk count for index reconciliation: {db_err}")
        return {
            "consistent": False,
            "status": "database_error",
            "faiss_vectors": None,
            "db_chunks": None,
            "error": str(db_err),
        }

    integrity = vector_store.verify_integrity()
    if not integrity["valid"]:
        return {
            "consistent": False,
            "status": "faiss_invalid",
            "faiss_vectors": 0,
            "db_chunks": db_chunks,
            "error": integrity.get("error"),
        }

    faiss_vectors = integrity["vector_count"]
    is_consistent = (faiss_vectors == db_chunks)

    return {
        "consistent": is_consistent,
        "status": "synchronized" if is_consistent else "out_of_sync",
        "faiss_vectors": faiss_vectors,
        "db_chunks": db_chunks,
        "difference": abs(faiss_vectors - db_chunks),
        "dimension": integrity.get("dimension"),
    }


def rebuild_faiss_from_database(
    db_session=None,
    embedding_service: Optional[BGEEmbeddingService] = None,
    vector_store: Optional[FAISSVectorStore] = None,
    index_path: Optional[str] = None,
    dimension: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Rebuilds the FAISS vector index from scratch using DocumentChunk records persisted in PostgreSQL.
    Guarantees index reconstruction in the exact order of chunk.vector_index.
    """
    import faiss

    session = db_session or db.session
    target_path = Path(index_path or INGESTION_CONFIG.get("faiss_index_path"))
    resolved_dim = dimension or SYSTEM_CONFIG.get("embedding_dimension", 384)

    if embedding_service is None:
        embedding_service = BGEEmbeddingService(
            SYSTEM_CONFIG.get("embedding_model", "BAAI/bge-small-en-v1.5"),
            INGESTION_CONFIG.get("embedding_batch_size", 32),
            resolved_dim,
        )

    # 1. Fetch all document chunks ordered by vector_index
    chunks = session.query(DocumentChunk).order_by(DocumentChunk.vector_index.asc()).all()
    chunk_count = len(chunks)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".rebuild.tmp")

    if chunk_count == 0:
        logger.info("No chunks in database. Initializing empty FAISS IndexFlatIP...")
        new_index = faiss.IndexFlatIP(resolved_dim)
        faiss.write_index(new_index, str(temp_path))
        temp_path.replace(target_path)

        if vector_store is not None:
            vector_store.reload()

        return {
            "rebuilt": True,
            "status": "empty_initialized",
            "chunks_indexed": 0,
            "vector_count": 0,
            "dimension": resolved_dim,
            "path": str(target_path),
        }

    logger.info(f"Rebuilding FAISS index for {chunk_count} database chunks...")
    chunk_texts = [c.content for c in chunks]

    try:
        vectors = embedding_service.generate(chunk_texts)
        if vectors.shape[0] != chunk_count:
            raise VectorStorageError(f"Embedding count ({vectors.shape[0]}) does not match chunk count ({chunk_count})")

        new_index = faiss.IndexFlatIP(resolved_dim)
        new_index.add(vectors)

        faiss.write_index(new_index, str(temp_path))
        temp_path.replace(target_path)

        if vector_store is not None:
            vector_store.reload()

        logger.info(f"✅ FAISS index rebuilt successfully with {new_index.ntotal} vectors.")
        return {
            "rebuilt": True,
            "status": "rebuilt_successfully",
            "chunks_indexed": chunk_count,
            "vector_count": int(new_index.ntotal),
            "dimension": resolved_dim,
            "path": str(target_path),
        }

    except Exception as error:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        logger.error(f"❌ Failed to rebuild FAISS index: {error}", exc_info=True)
        return {
            "rebuilt": False,
            "status": "failed",
            "chunks_indexed": 0,
            "vector_count": 0,
            "error": str(error),
            "path": str(target_path),
        }

