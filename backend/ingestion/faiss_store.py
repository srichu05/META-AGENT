"""FAISS vector-only persistence for document chunk embeddings."""

from pathlib import Path
from typing import Optional

import numpy as np

from .exceptions import VectorStorageError


class FAISSVectorStore:
    """Appends normalized vectors to an inner-product FAISS index without search APIs."""

    def __init__(self, index_path: str, expected_dimension: Optional[int] = None):
        self.index_path = Path(index_path)
        self.expected_dimension = expected_dimension
        self._index = None

    @property
    def vector_count(self) -> int:
        self._load()
        return int(self._index.ntotal)

    def append(self, vectors: np.ndarray) -> int:
        normalized = np.ascontiguousarray(vectors, dtype=np.float32)
        if normalized.ndim != 2 or not normalized.shape[0]:
            raise VectorStorageError("FAISS requires a non-empty two-dimensional vector batch.")
        if not np.isfinite(normalized).all():
            raise VectorStorageError("FAISS cannot store non-finite vector values.")

        self._load(dimension=normalized.shape[1])
        if self._index.d != normalized.shape[1]:
            raise VectorStorageError("Embedding dimension does not match the existing FAISS index.")
        start_index = int(self._index.ntotal)
        self._index.add(normalized)
        return start_index

    def search(self, query_vectors: np.ndarray, top_k: int = 5):
        """Perform inner-product (cosine similarity for L2-normalized vectors) similarity search."""
        self._load()
        if self._index.ntotal == 0:
            return np.array([[]], dtype=np.float32), np.array([[]], dtype=np.int64)

        normalized = np.ascontiguousarray(query_vectors, dtype=np.float32)
        if normalized.ndim == 1:
            normalized = np.expand_dims(normalized, axis=0)

        if normalized.shape[1] != self._index.d:
            raise VectorStorageError(
                f"Query dimension {normalized.shape[1]} does not match FAISS index dimension {self._index.d}."
            )

        k = min(top_k, int(self._index.ntotal))
        scores, indices = self._index.search(normalized, k)
        return scores, indices


    def save(self) -> None:
        self._load()
        try:
            import faiss

            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.index_path.with_suffix(self.index_path.suffix + ".tmp")
            faiss.write_index(self._index, str(temporary_path))
            temporary_path.replace(self.index_path)
        except Exception as error:
            raise VectorStorageError(f"Unable to save the FAISS index: {error}") from error

    def reload(self) -> None:
        self._index = None
        self._load()

    def _load(self, dimension: Optional[int] = None) -> None:
        if self._index is not None:
            return
        try:
            import faiss
        except ImportError as error:
            raise VectorStorageError("faiss-cpu is not installed.") from error

        try:
            if self.index_path.exists():
                self._index = faiss.read_index(str(self.index_path))
            else:
                resolved_dimension = dimension or self.expected_dimension
                if not resolved_dimension:
                    raise VectorStorageError("An embedding dimension is required to initialize the FAISS index.")
                self._index = faiss.IndexFlatIP(resolved_dimension)
        except VectorStorageError:
            raise
        except Exception as error:
            raise VectorStorageError(f"Unable to load the FAISS index: {error}") from error

        if self.expected_dimension and self._index.d != self.expected_dimension:
            raise VectorStorageError("Existing FAISS index dimension conflicts with configured embedding dimension.")
