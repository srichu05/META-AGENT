"""Relational metadata models for uploaded documents and their chunks."""

from database.extensions import db


class Document(db.Model):
    """An uploaded source document; embeddings are intentionally stored elsewhere."""

    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(512), nullable=False)
    stored_filename = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(32), nullable=False, index=True)
    storage_path = db.Column(db.Text, nullable=False)
    text_length = db.Column(db.Integer, nullable=False, default=0)
    chunk_count = db.Column(db.Integer, nullable=False, default=0)
    uploaded_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)

    chunks = db.relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.position",
    )

    def to_dict(self, include_chunks=False):
        data = {
            "document_id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "text_length": self.text_length,
            "chunk_count": self.chunk_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
        if include_chunks:
            data["chunks"] = [chunk.to_dict() for chunk in self.chunks]
        return data


class DocumentChunk(db.Model):
    """Chunk text and citation metadata, mapped to one FAISS vector position."""

    __tablename__ = "document_chunks"

    id = db.Column(db.String(36), primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    section_heading = db.Column(db.String(512), nullable=True)
    position = db.Column(db.Integer, nullable=False)
    char_start = db.Column(db.Integer, nullable=False)
    char_end = db.Column(db.Integer, nullable=False)
    vector_index = db.Column(db.Integer, nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    document = db.relationship("Document", back_populates="chunks")

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "chunk_id": self.id,
            "filename": self.document.filename if self.document else None,
            "file_type": self.document.file_type if self.document else None,
            "page_number": self.page_number,
            "section_heading": self.section_heading,
            "upload_timestamp": self.document.uploaded_at.isoformat() if self.document and self.document.uploaded_at else None,
            "chunk_position": self.position,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "vector_index": self.vector_index,
        }
