"""REST endpoints for retrieval testing, context inspection, and status."""

import os
from flask import Blueprint, current_app, jsonify, request

from config import INGESTION_CONFIG, SYSTEM_CONFIG
from ingestion.faiss_store import FAISSVectorStore
from models.document import Document, DocumentChunk
from retrieval.service import RetrievalService
from security import get_current_user, rate_limit, require_auth

retrieval_blueprint = Blueprint("retrieval", __name__, url_prefix="/retrieval")


def _service() -> RetrievalService:
    service = current_app.extensions.get("retrieval_service")
    if service is None:
        service = RetrievalService()
        current_app.extensions["retrieval_service"] = service
    return service


@retrieval_blueprint.route("/query", methods=["POST"])
@require_auth()
@rate_limit(scope="debate")
def query_retrieval():
    """Query the retrieval pipeline with user isolation and return formatted context."""
    data = request.get_json(force=True) or {}
    query = (data.get("query") or data.get("problem") or "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query string is required."}), 400

    max_len = int(os.getenv("MAX_QUERY_LENGTH", "5000"))
    if len(query) > max_len:
        return jsonify({
            "success": False,
            "error": f"Query length ({len(query)}) exceeds maximum allowed ({max_len} characters).",
        }), 400

    try:
        max_k = int(os.getenv("MAX_TOP_K", "50"))
        top_k = int(data.get("top_k", SYSTEM_CONFIG.get("top_k_retrieval", 5)))
        top_k = max(1, min(max_k, top_k))
    except (ValueError, TypeError):
        top_k = 5

    current_user = get_current_user() or {}
    user_id = current_user.get("user_id")

    try:
        context = _service().retrieve(query, top_k=top_k, user_id=user_id)
        return jsonify({"success": True, "result": context.to_dict()}), 200
    except Exception as error:
        current_app.logger.exception("Retrieval query failed unexpectedly")
        return jsonify({"success": False, "error": str(error)}), 500


@retrieval_blueprint.route("/status", methods=["GET"])
@require_auth()
def get_retrieval_status():
    """Inspect retrieval index status, FAISS vector count, and database chunk count."""
    try:
        vector_store = FAISSVectorStore(
            INGESTION_CONFIG["faiss_index_path"],
            SYSTEM_CONFIG["embedding_dimension"],
        )
        faiss_count = vector_store.vector_count
        db_chunks = DocumentChunk.query.count()
        db_docs = Document.query.count()

        return jsonify({
            "success": True,
            "faiss_vector_count": faiss_count,
            "database_document_count": db_docs,
            "database_chunk_count": db_chunks,
            "faiss_index_path": str(vector_store.index_path),
            "status": "ready" if faiss_count > 0 and db_chunks > 0 else "empty",
        }), 200
    except Exception as error:
        current_app.logger.exception("Retrieval status check failed")
        return jsonify({"success": False, "error": str(error)}), 500
