"""User authorization, document ownership verification, and IDOR prevention."""

import logging
from typing import Any, List, Optional

from models.document import Document

logger = logging.getLogger(__name__)


def can_access_document(document: Optional[Document], user_id: Optional[str], role: str = "user") -> bool:
    """
    Checks if an authenticated user is authorized to read or manipulate a document.
    Enforces server-side IDOR prevention.
    """
    if document is None:
        return False

    # Administrators have universal read/write permissions
    if role == "admin":
        return True

    # Public or unassigned system corpus documents are readable by any authenticated user
    doc_owner = getattr(document, "user_id", None)
    if doc_owner in (None, "", "system"):
        return True

    # Document owner matches authenticated user
    return bool(user_id and str(doc_owner) == str(user_id))


def filter_documents_for_user(query, user_id: Optional[str], role: str = "user"):
    """Applies ownership filtering to a SQLAlchemy Document query."""
    if role == "admin":
        return query

    if not user_id:
        return query.filter((Document.user_id.is_(None)) | (Document.user_id == "system"))

    return query.filter(
        (Document.user_id == user_id) | (Document.user_id.is_(None)) | (Document.user_id == "system")
    )


def filter_chunks_for_user(chunks: List[Any], user_id: Optional[str], role: str = "user") -> List[Any]:
    """
    Filters retrieved document chunks to ensure unauthorized chunks do not enter context or citations.
    Enforces server-side retrieval isolation over a shared FAISS index.
    """
    if not chunks:
        return []

    if role == "admin" or not user_id:
        return chunks

    authorized = []
    for chunk in chunks:
        chunk_owner = getattr(chunk, "user_id", None)
        if chunk_owner in (None, "", "system") or str(chunk_owner) == str(user_id):
            authorized.append(chunk)
        else:
            logger.warning(
                f"🛡️ Retrieval isolation: Filtered chunk {getattr(chunk, 'chunk_id', 'unknown')} "
                f"owned by '{chunk_owner}' from query requested by user '{user_id}'."
            )

    return authorized

