"""REST endpoints for Draft 2 retrieval testing and context inspection."""

from flask import Blueprint, current_app, jsonify, request

from retrieval.service import RetrievalService
from models.document import Document, DocumentChunk
from ingestion.faiss_store import FAISSVectorStore
from config import INGESTION_CONFIG, SYSTEM_CONFIG

retrieval_blueprint = Blueprint("retrieval", __name__, url_prefix="/retrieval")


def _service() -> RetrievalService:
    service = current_app.extensions.get("retrieval_service")
    if service is None:
        service = RetrievalService()
        current_app.extensions["retrieval_service"] = service
    return service


@retrieval_blueprint.route("/query", methods=["POST"])
def query_retrieval():
    """Query the retrieval pipeline and return formatted context, chunks, and citations."""
    data = request.get_json(force=True) or {}
    query = (data.get("query") or data.get("problem") or "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query string is required."}), 400

    top_k = int(data.get("top_k", SYSTEM_CONFIG.get("top_k_retrieval", 5)))

    try:
        context = _service().retrieve(query, top_k=top_k)
        return jsonify({"success": True, "result": context.to_dict()}), 200
    except Exception as error:
        current_app.logger.exception("Retrieval query failed unexpectedly")
        return jsonify({"success": False, "error": str(error)}), 500


@retrieval_blueprint.route("/status", methods=["GET"])
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
