"""REST endpoints for Draft 2 document ingestion and metadata inspection."""

from flask import Blueprint, current_app, jsonify, request

from config import INGESTION_CONFIG
from ingestion.exceptions import DocumentParsingError, EmbeddingGenerationError, IngestionError, UploadValidationError, VectorStorageError
from ingestion.service import DocumentIngestionService
from models.document import Document


documents_blueprint = Blueprint("documents", __name__, url_prefix="/documents")


def _service():
    service = current_app.extensions.get("document_ingestion_service")
    if service is None:
        service = DocumentIngestionService()
        current_app.extensions["document_ingestion_service"] = service
    return service


@documents_blueprint.route("/upload", methods=["POST"])
def upload_document():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify({"success": False, "error": "A file field is required."}), 400
    try:
        result = _service().ingest(uploaded_file)
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
def list_documents():
    documents = (
        Document.query.order_by(Document.uploaded_at.desc())
        .limit(INGESTION_CONFIG["document_list_limit"])
        .all()
    )
    return jsonify({"success": True, "documents": [document.to_dict() for document in documents]})


@documents_blueprint.route("/<document_id>", methods=["GET"])
def get_document(document_id):
    document = Document.query.filter_by(id=document_id).first()
    if document is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    return jsonify({"success": True, "document": document.to_dict(include_chunks=True)})
