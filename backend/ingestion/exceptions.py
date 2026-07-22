"""Typed errors returned by the document ingestion pipeline."""


class IngestionError(Exception):
    """Base class for expected ingestion failures."""


class UploadValidationError(IngestionError):
    """Raised when an uploaded file is not accepted by the pipeline."""


class DocumentParsingError(IngestionError):
    """Raised when a supported document cannot yield usable text."""


class EmbeddingGenerationError(IngestionError):
    """Raised when a chunk batch cannot be embedded."""


class VectorStorageError(IngestionError):
    """Raised when vectors cannot be appended to the FAISS index."""
