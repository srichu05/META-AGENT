"""Orchestrates the Draft 2 ingestion pipeline without retrieval behavior."""

from datetime import datetime
import logging
import uuid

from werkzeug.datastructures import FileStorage

from config import INGESTION_CONFIG, SYSTEM_CONFIG
from database.extensions import db
from models.document import Document, DocumentChunk

from .chunking import SemanticChunker
from .embeddings import BGEEmbeddingService
from .exceptions import IngestionError
from .faiss_store import FAISSVectorStore
from .metadata import build_chunk_metadata
from .parsers import DocumentParserRegistry
from .storage import UploadStorage


logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Runs upload, parsing, chunking, embedding, FAISS storage, and metadata persistence."""

    def __init__(self):
        self.storage = UploadStorage(
            SYSTEM_CONFIG["upload_folder"],
            INGESTION_CONFIG["supported_file_types"],
            INGESTION_CONFIG["max_file_size_bytes"],
        )
        self.parsers = DocumentParserRegistry()
        self.chunker = SemanticChunker(INGESTION_CONFIG["chunk_size"], INGESTION_CONFIG["chunk_overlap"])
        self.embedding_service = BGEEmbeddingService(
            SYSTEM_CONFIG["embedding_model"],
            INGESTION_CONFIG["embedding_batch_size"],
            SYSTEM_CONFIG["embedding_dimension"],
        )
        self.vector_store = FAISSVectorStore(
            INGESTION_CONFIG["faiss_index_path"],
            SYSTEM_CONFIG["embedding_dimension"],
        )

    def ingest(self, file: FileStorage):
        document_id = str(uuid.uuid4())
        stored_upload = self.storage.save(file, document_id)
        parsed_document = self.parsers.get_parser(stored_upload.file_type).parse(stored_upload.storage_path)
        chunks = self.chunker.chunk(parsed_document, document_id)
        if not chunks:
            raise IngestionError("The document did not produce any chunks.")

        vectors = self.embedding_service.generate(chunk.content for chunk in chunks)
        upload_timestamp = datetime.utcnow()
        metadata = build_chunk_metadata(
            document_id,
            stored_upload.filename,
            stored_upload.file_type,
            upload_timestamp,
            chunks,
        )

        vector_start = None
        try:
            vector_start = self.vector_store.append(vectors)
            self.vector_store.save()

            document = Document(
                id=document_id,
                filename=stored_upload.filename,
                stored_filename=stored_upload.stored_filename,
                file_type=stored_upload.file_type,
                storage_path=str(stored_upload.storage_path),
                text_length=len(parsed_document.text),
                chunk_count=len(chunks),
                uploaded_at=upload_timestamp,
            )
            db.session.add(document)
            for chunk, chunk_metadata in zip(chunks, metadata):
                db.session.add(
                    DocumentChunk(
                        id=chunk_metadata["chunk_id"],
                        document_id=document_id,
                        content=chunk.content,
                        page_number=chunk_metadata["page_number"],
                        section_heading=chunk_metadata["section_heading"],
                        position=chunk_metadata["chunk_position"],
                        char_start=chunk_metadata["char_start"],
                        char_end=chunk_metadata["char_end"],
                        vector_index=vector_start + chunk.position,
                    )
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            if vector_start is not None:
                try:
                    self.vector_store.reload()
                except Exception:
                    logger.exception("Failed to reload FAISS after an ingestion rollback")
            raise

        return {
            "document": document.to_dict(),
            "processing": {
                "text_length": len(parsed_document.text),
                "chunk_count": len(chunks),
                "embedding_dimension": int(vectors.shape[1]),
                "faiss_vector_start": vector_start,
                "faiss_vector_end": vector_start + len(chunks) - 1,
            },
        }
