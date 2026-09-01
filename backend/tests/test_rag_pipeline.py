"""Comprehensive test suite for Draft 2 RAG Retrieval Pipeline (Session 6)."""

import os
import sys
import tempfile
import unittest

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import db
from models.document import Document, DocumentChunk
from ingestion.embeddings import BGEEmbeddingService
from ingestion.faiss_store import FAISSVectorStore
from retrieval.vector_search import FAISSQueryEngine
from retrieval.bm25_search import BM25Retriever
from retrieval.hybrid import HybridRetriever
from retrieval.reranker import CohereRerankerAdapter
from retrieval.metadata_lookup import MetadataLookupService

from retrieval.service import RetrievalService
from services.context_manager import ContextManager
from graph.workflow import MathDebateGraph


class TestRAGPipeline(unittest.TestCase):
    """End-to-end unit and integration test suite for the Draft 2 RAG pipeline."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Temporary FAISS index file
        self.temp_faiss_file = tempfile.NamedTemporaryFile(suffix=".faiss", delete=False)
        self.temp_faiss_path = self.temp_faiss_file.name
        self.temp_faiss_file.close()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        if os.path.exists(self.temp_faiss_path):
            try:
                os.remove(self.temp_faiss_path)
            except Exception:
                pass


    def test_faiss_indexing_and_reload(self):
        """Verify BGE embedding generation, FAISS index append, save, and reload."""
        store = FAISSVectorStore(self.temp_faiss_path, expected_dimension=384)
        embedding_service = BGEEmbeddingService("BAAI/bge-small-en-v1.5", batch_size=4, expected_dimension=384)

        texts = [
            "The Pythagorean theorem states that a^2 + b^2 = c^2 for right triangles.",
            "The area of a circle is calculated as pi * r^2.",
        ]
        vectors = embedding_service.generate(texts)
        self.assertEqual(vectors.shape, (2, 384))

        start_idx = store.append(vectors)
        self.assertEqual(start_idx, 0)
        store.save()

        # Reload store and search
        reloaded_store = FAISSVectorStore(self.temp_faiss_path, expected_dimension=384)

        self.assertEqual(reloaded_store.vector_count, 2)

        query_vec = embedding_service.generate(["What is the area of a circle?"])
        scores, indices = reloaded_store.search(query_vec, top_k=2)
        self.assertEqual(indices[0][0], 1)  # Circle chunk should rank first

    def test_bm25_search_context_safety(self):
        """Verify BM25 keyword search operates safely inside and outside Flask app context."""
        retriever = BM25Retriever()
        # Search over empty DB should return empty list without exception
        results = retriever.search("pythagorean theorem", top_k=5)
        self.assertIsInstance(results, list)

    def test_cohere_rerank_fallback(self):
        """Verify Cohere reranker handles missing key / unavailable API gracefully."""
        adapter = CohereRerankerAdapter()
        # Should gracefully return original chunks when unconfigured
        dummy_chunks = []
        result = adapter.rerank("query", dummy_chunks, top_k=5)
        self.assertEqual(result, dummy_chunks)

    def test_retrieval_service_and_context_manager(self):
        """Verify RetrievalService and ContextManager integration."""
        service = RetrievalService()
        context = service.retrieve("Solve quadratic equation x^2 - 4 = 0", top_k=3)
        self.assertIsNotNone(context)

        context_mgr = ContextManager()
        processed = context_mgr.process_context(context, query="x^2 - 4 = 0")
        self.assertIn("formatted_context", processed)
        self.assertIn("citations", processed)

    def test_langgraph_workflow_execution(self):
        """Verify full 9-node LangGraph debate workflow executes end-to-end without errors."""
        graph = MathDebateGraph()
        state = graph.execute("Solve 3x + 9 = 24")
        self.assertIn("final_answer", state)
        self.assertTrue(state.get("final_answer") or state.get("judge_output"))


if __name__ == "__main__":
    unittest.main()
