"""REST endpoints for document ingestion, ownership authorization, and inspection."""

from flask import Blueprint, current_app, jsonify, request

from config import INGESTION_CONFIG
from database.extensions import db
from ingestion.exceptions import (
    DocumentParsingError,
    EmbeddingGenerationError,
    IngestionError,
    UploadValidationError,
    VectorStorageError,
)
from ingestion.service import DocumentIngestionService
from models.document import Document
from security import (
    can_access_document,
    filter_documents_for_user,
    get_current_user,
    rate_limit,
    require_auth,
)

documents_blueprint = Blueprint("documents", __name__, url_prefix="/documents")


def _service():
    service = current_app.extensions.get("document_ingestion_service")
    if service is None:
        service = DocumentIngestionService()
        current_app.extensions["document_ingestion_service"] = service
    return service


@documents_blueprint.route("/upload", methods=["POST"])
@require_auth()
@rate_limit(scope="upload")
def upload_document():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "error": "A file field is required."}), 400

    current_user = get_current_user() or {}
    user_id = current_user.get("user_id", "system")

    try:
        result = _service().ingest(uploaded_file, user_id=user_id)
        return jsonify({"success": True, **result}), 201
    except UploadValidationError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except DocumentParsingError as error:
        return jsonify({"success": False, "error": str(error)}), 422
    except (EmbeddingGenerationError, VectorStorageError) as error:
        return jsonify({"success": False, "error": str(error)}), 503
    except IngestionError as error:
        return jsonify({"success": False, "error": str(error)}), 422
    except Exception:
        current_app.logger.exception("Document ingestion failed unexpectedly")
        return jsonify({"success": False, "error": "Document ingestion failed."}), 500


@documents_blueprint.route("", methods=["GET"])
@require_auth()
def list_documents():
    current_user = get_current_user() or {}
    user_id = current_user.get("user_id")
    role = current_user.get("role", "user")

    query = Document.query.order_by(Document.uploaded_at.desc())
    filtered_query = filter_documents_for_user(query, user_id=user_id, role=role)
    documents = filtered_query.limit(INGESTION_CONFIG["document_list_limit"]).all()

    return jsonify({"success": True, "documents": [doc.to_dict() for doc in documents]})


@documents_blueprint.route("/<document_id>", methods=["GET"])
@require_auth()
def get_document(document_id):
    current_user = get_current_user() or {}
    user_id = current_user.get("user_id")
    role = current_user.get("role", "user")

    document = Document.query.filter_by(id=document_id).first()
    if document is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    # Server-side IDOR prevention
    if not can_access_document(document, user_id=user_id, role=role):
        return jsonify({
            "success": False,
            "error": "Access denied. You do not have permission to access this document.",
        }), 403

    return jsonify({"success": True, "document": document.to_dict(include_chunks=True)})


@documents_blueprint.route("/<document_id>", methods=["DELETE"])
@require_auth()
def delete_document(document_id):
    current_user = get_current_user() or {}
    user_id = current_user.get("user_id")
    role = current_user.get("role", "user")

    document = Document.query.filter_by(id=document_id).first()
    if document is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    # Server-side ownership check
    if not can_access_document(document, user_id=user_id, role=role):
        return jsonify({
            "success": False,
            "error": "Access denied. You do not have permission to delete this document.",
        }), 403

    try:
        db.session.delete(document)
        db.session.commit()
        return jsonify({"success": True, "message": "Document deleted successfully."}), 200
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete document {document_id}: {err}")
        return jsonify({"success": False, "error": "Failed to delete document."}), 500
