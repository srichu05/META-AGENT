"""Unit tests for Phase 3.4 Deployment Readiness and Observability."""

import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np

# Ensure app context is initialized
from app import app
from config.validator import (
    get_cors_origins,
    mask_database_url,
    validate_startup_config,
)
from database import check_database_connectivity, check_migration_status, db
from ingestion.faiss_store import FAISSVectorStore
from ingestion.recovery import check_index_consistency, rebuild_faiss_from_database
from models.document import DocumentChunk
from security import create_test_auth_headers
from utils.observability import (
    ExecutionTelemetry,
    SensitiveDataFilter,
    get_correlation_id,
    redact_sensitive_dict,
    redact_sensitive_text,
)


class TestDeploymentReadiness(unittest.TestCase):
    """Test suite verifying Phase 3.4 deployment readiness and observability controls."""

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # --- 1. Startup Configuration & Secrets Validation ---

    def test_startup_config_validation_development(self):
        with patch.dict(os.environ, {"FLASK_ENV": "development", "DEBUG": "True"}):
            status = validate_startup_config()
            self.assertTrue(status["valid"])
            self.assertEqual(status["environment"], "development")
            self.assertFalse(status["is_production"])
            self.assertIn("database_valid", status)
            self.assertTrue(status["database_valid"])

    def test_startup_config_validation_production_debug_forbidden(self):
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "DEBUG": "True",
                "SECRET_KEY": "a-very-long-production-secret-key-12345",
            },
        ):
            status = validate_startup_config()
            self.assertFalse(status["valid"])
            self.assertTrue(status["is_production"])
            self.assertTrue(any("DEBUG mode must not be enabled" in err for err in status["errors"]))

    def test_startup_config_validation_production_insecure_secret_forbidden(self):
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "DEBUG": "False",
                "SECRET_KEY": "dev-fallback-key-change-in-production",
            },
        ):
            status = validate_startup_config()
            self.assertFalse(status["valid"])
            self.assertTrue(any("SECRET_KEY is insecure" in err for err in status["errors"]))

    def test_mask_database_url(self):
        raw_url = "postgresql+psycopg2://meta_user:super_secret_pw123@localhost:5432/math_debate_db"
        masked = mask_database_url(raw_url)
        self.assertNotIn("super_secret_pw123", masked)
        self.assertIn("meta_user:***@localhost:5432/math_debate_db", masked)
        self.assertEqual(mask_database_url(None), "not-configured")

    def test_cors_origins_parsing(self):
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"}):
            self.assertEqual(get_cors_origins(), ["*"])

        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://app.example.com, https://admin.example.com"}):
            origins = get_cors_origins()
            self.assertIn("https://app.example.com", origins)
            self.assertIn("https://admin.example.com", origins)

    # --- 2. Database Connectivity & Migration Checks ---

    def test_database_connectivity_success(self):
        result = check_database_connectivity()
        self.assertTrue(result["connected"])
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["latency_ms"], 0.0)
        self.assertIn(result["dialect"], ["postgresql", "sqlite"])

    def test_database_connectivity_failure_handled(self):
        with patch.object(db.session, "execute", side_effect=Exception("Connection refused to database")):
            result = check_database_connectivity()
            self.assertFalse(result["connected"])
            self.assertIn("Connection refused", result["error"])

    def test_migration_status_check(self):
        status = check_migration_status()
        self.assertIn(status["status"], ["up_to_date", "pending", "unversioned"])
        self.assertIn("head_revision", status)
        self.assertIsNotNone(status["head_revision"])

    # --- 3. FAISS Vector Persistence, Integrity & Recovery ---

    def test_faiss_integrity_verification_existing(self):
        from config import INGESTION_CONFIG
        faiss_path = INGESTION_CONFIG.get("faiss_index_path")
        store = FAISSVectorStore(faiss_path, expected_dimension=384)
        integrity = store.verify_integrity()
        self.assertTrue(integrity["valid"])
        self.assertGreaterEqual(integrity["vector_count"], 0)
        self.assertEqual(integrity["dimension"], 384)

    def test_faiss_integrity_verification_missing_and_corrupt(self):
        missing_store = FAISSVectorStore("non_existent_dir/index.faiss", expected_dimension=384)
        integrity = missing_store.verify_integrity()
        self.assertFalse(integrity["valid"])
        self.assertIn("does not exist", integrity["error"])

        with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as empty_file:
            empty_path = empty_file.name

        try:
            empty_store = FAISSVectorStore(empty_path, expected_dimension=384)
            empty_integrity = empty_store.verify_integrity()
            self.assertFalse(empty_integrity["valid"])
            self.assertIn("empty (0 bytes)", empty_integrity["error"])
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)

    def test_faiss_consistency_reconciliation(self):
        consistency = check_index_consistency()
        self.assertIn("consistent", consistency)
        self.assertIn("faiss_vectors", consistency)
        self.assertIn("db_chunks", consistency)
        self.assertEqual(consistency["status"], "synchronized" if consistency["consistent"] else "out_of_sync")

    def test_faiss_rebuild_from_database(self):
        # Test rebuilding to a temporary index path
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_index_path = os.path.join(temp_dir, "rebuilt_vectors.faiss")

            # Mock embedding service that generates normalized vectors
            mock_embedding = MagicMock()
            mock_embedding.generate.side_effect = lambda texts: np.ascontiguousarray(
                np.ones((len(list(texts)), 384), dtype=np.float32) / np.sqrt(384)
            )

            result = rebuild_faiss_from_database(
                embedding_service=mock_embedding,
                index_path=temp_index_path,
                dimension=384,
            )

            self.assertTrue(result["rebuilt"])
            self.assertIn(result["status"], ["rebuilt_successfully", "empty_initialized"])
            self.assertTrue(os.path.exists(temp_index_path))

            # Validate the rebuilt index using FAISSVectorStore
            store = FAISSVectorStore(temp_index_path, expected_dimension=384)
            integrity = store.verify_integrity()
            self.assertTrue(integrity["valid"])
            self.assertEqual(integrity["vector_count"], result["vector_count"])

    # --- 4. Health, Readiness, and Diagnostics Endpoints ---

    def test_liveness_endpoint(self):
        response = self.client.get("/api/health/live")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "alive")
        self.assertEqual(data["service"], "meta-agent-math-debate")
        self.assertIn("correlation_id", data)
        self.assertIn("X-Correlation-ID", response.headers)

    def test_readiness_endpoint_healthy(self):
        response = self.client.get("/api/health/ready")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["healthy"])
        self.assertTrue(data["database"]["connected"])
        self.assertTrue(data["faiss_index"]["valid"])
        self.assertIn("cache", data)
        self.assertIn("providers", data)

    def test_readiness_endpoint_unhealthy_when_db_down(self):
        with patch(
            "api.health.check_database_connectivity",
            return_value={"connected": False, "error": "Database unreachable", "latency_ms": 10.0},
        ):
            response = self.client.get("/api/health/ready")
            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertEqual(data["status"], "unready")
            self.assertFalse(data["healthy"])
            self.assertFalse(data["database"]["connected"])

    def test_diagnostics_endpoint_secrets_redacted(self):
        headers = create_test_auth_headers(user_id="test_admin", role="admin")
        response = self.client.get("/api/health/diagnostics", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["service"], "meta-agent-math-debate")
        self.assertIn("runtime", data)
        self.assertIn("index_consistency", data)
        self.assertIn("system_config", data)

        # Verify no raw secrets or passwords leak
        sys_cfg = data["system_config"]
        if "secret_key" in sys_cfg:
            self.assertEqual(sys_cfg["secret_key"], "***[REDACTED]***")

        # Database URL should have password masked
        db_url = sys_cfg.get("database_url", "")
        self.assertNotIn("password", db_url.lower())

    # --- 5. Observability & Correlation ID Tracking ---

    def test_correlation_id_propagation_in_headers(self):
        custom_id = "test-corr-id-987654321"
        response = self.client.get("/api/health/live", headers={"X-Correlation-ID": custom_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Correlation-ID"), custom_id)
        data = response.get_json()
        self.assertEqual(data["correlation_id"], custom_id)

    def test_sensitive_data_redaction_text(self):
        text_with_keys = (
            "User provided API key sk-1234567890abcdef1234567890 and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz "
            "with connection string postgresql+psycopg2://user:mysecretpwd@localhost:5432/db"
        )
        redacted = redact_sensitive_text(text_with_keys)
        self.assertNotIn("sk-1234567890abcdef1234567890", redacted)
        self.assertIn("sk-***[REDACTED]***", redacted)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)
        self.assertNotIn("mysecretpwd", redacted)
        self.assertIn("user:***@localhost:5432/db", redacted)

    def test_sensitive_data_redaction_dict(self):
        cfg = {
            "api_key": "sk-secretvalue123",
            "password": "supersecretpassword",
            "safe_value": "normal_config",
            "nested": {"token": "token123", "param": 42},
        }
        redacted = redact_sensitive_dict(cfg)
        self.assertEqual(redacted["api_key"], "***[REDACTED]***")
        self.assertEqual(redacted["password"], "***[REDACTED]***")
        self.assertEqual(redacted["safe_value"], "normal_config")
        self.assertEqual(redacted["nested"]["token"], "***[REDACTED]***")
        self.assertEqual(redacted["nested"]["param"], 42)

    def test_sensitive_data_logging_filter(self):
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Connecting using password=secretpass and sk-1234567890abcdef12345678",
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        self.assertNotIn("secretpass", record.msg)
        self.assertNotIn("sk-1234567890abcdef12345678", record.msg)
        self.assertIn("[REDACTED]", record.msg)

    # --- 6. Workflow Failure Handling & Telemetry ---

    def test_workflow_failure_categorization_and_no_cache(self):
        from graph.workflow import MathDebateGraph

        mock_cache = MagicMock()
        mock_cache.is_enabled.return_value = True
        mock_cache.get.return_value = None

        graph = MathDebateGraph(cache_service=mock_cache)

        # Force a failure in the Planner node with a timeout signature
        def failing_planner(state):
            raise TimeoutError("HTTP request timed out contacting LLM provider")

        with patch("graph.workflow.planner_node", side_effect=failing_planner):
            final_state = graph.execute("What is 5 + 5?")

            # Assert failure state representation
            self.assertTrue(final_state["partial_execution"])
            self.assertEqual(final_state["failed_node"], "Planner")
            self.assertEqual(final_state["error_category"], "timeout")
            self.assertEqual(final_state["status"], "failed")
            self.assertIn("HTTP request timed out", final_state["error"])

            # Verify that failed execution was NEVER committed to semantic cache
            mock_cache.set.assert_not_called()


if __name__ == "__main__":
    unittest.main()

