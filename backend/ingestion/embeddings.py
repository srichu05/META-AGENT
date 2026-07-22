"""Batch BAAI BGE embedding service for ingestion-only vector generation."""

from typing import Iterable, Optional

import numpy as np

from .exceptions import EmbeddingGenerationError


class BGEEmbeddingService:
    """Lazily loads the configured BGE model and returns normalized float32 vectors."""

    def __init__(self, model_name: str, batch_size: int, expected_dimension: Optional[int] = None):
        self.model_name = model_name
        self.batch_size = batch_size
        self.expected_dimension = expected_dimension
        self._model = None

    def generate(self, texts: Iterable[str]) -> np.ndarray:
        values = list(texts)
        if not values:
            raise EmbeddingGenerationError("At least one text chunk is required for embedding generation.")
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception as error:
                raise EmbeddingGenerationError(f"Unable to load embedding model '{self.model_name}': {error}") from error
        try:
            vectors = self._model.encode(
                values,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as error:
            raise EmbeddingGenerationError(f"Embedding generation failed: {error}") from error

        result = np.ascontiguousarray(vectors, dtype=np.float32)
        if result.ndim != 2 or result.shape[0] != len(values):
            raise EmbeddingGenerationError("Embedding model returned an invalid batch shape.")
        if self.expected_dimension and result.shape[1] != self.expected_dimension:
            raise EmbeddingGenerationError(
                f"Embedding dimension {result.shape[1]} does not match configured dimension {self.expected_dimension}."
            )
        return result
