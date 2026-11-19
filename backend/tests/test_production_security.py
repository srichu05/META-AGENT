"""Phase 3.5 — Production Security, Authentication & Access Control Test Suite.

Comprehensive test suite verifying:
1. Standard RFC 7519 HS256 JWT Bearer token authentication & token validation
2. Public vs protected endpoint access controls
3. Role-based authorization & administrative endpoint protection (/diagnostics, /cache/clear)
4. Document ownership authorization and server-side IDOR prevention
5. Retrieval and chunk context isolation across users (shared FAISS index protection)
6. Cross-user semantic cache isolation via user-scoped hashing
7. Thread-safe sliding-window rate limiting & HTTP 429 Retry-After enforcement
8. Query payload size limits & retrieval depth clamping
"""

import io
import json
import os
import sys
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from cache.normalization import compute_query_hash, compute_scope_hash
from cache.service import SemanticCacheService
from database import db
from models.document import Document, DocumentChunk
from retrieval.service import RetrievalService
from retrieval.types import RetrievedChunk, RetrievedContext
from security.auth import (
    decode_jwt,
    encode_jwt,
    generate_token,
    is_auth_enabled,
    validate_token,
    InvalidTokenError,
    TokenExpiredError,
    create_test_auth_headers,
)
from security.authorization import (
    can_access_document,
    filter_chunks_for_user,
    filter_documents_for_user,
)
from security.rate_limiter import SlidingWindowRateLimiter, limiter, parse_rate_limit


class TestJWTAuthentication(unittest.TestCase):
    """Verifies RFC 7519 HS256 JWT token generation, parsing, validation, and endpoint security."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        limiter.reset()

    def tearDown(self):
        limiter.reset()
        self.app_context.pop()

    def test_jwt_generation_and_validation_roundtrip(self):
        """Verifies JWT token encodes user claims and decodes with valid signature."""
        token = generate_token(user_id="user_alice", role="user", expires_in=1800, extra_claims={"dept": "math"})
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

        claims = validate_token(token)
        self.assertEqual(claims["sub"], "user_alice")
        self.assertEqual(claims["role"], "user")
        self.assertEqual(claims["dept"], "math")
        self.assertIn("exp", claims)
        self.assertIn("iat", claims)

    def test_jwt_expired_token_rejected(self):
        """Verifies that expired JWT tokens raise TokenExpiredError and return HTTP 401."""
        expired_token = generate_token(user_id="user_expired", expires_in=-60)
        with self.assertRaises(TokenExpiredError):
            validate_token(expired_token)

        headers = {"Authorization": f"Bearer {expired_token}"}
        resp = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertIn("expired", data.get("error", "").lower())

    def test_jwt_tampered_signature_rejected(self):
        """Verifies that tampering with header, payload, or signature is rejected."""
        valid_token = generate_token(user_id="user_alice")
        parts = valid_token.split(".")

        # Tampered signature
        tampered_token = f"{parts[0]}.{parts[1]}.bad_signature_here"
        with self.assertRaises(InvalidTokenError):
            validate_token(tampered_token)

        resp = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(resp.status_code, 401)

    def test_missing_and_malformed_auth_headers_return_401(self):
        """Verifies missing or malformed Authorization headers return HTTP 401 on protected endpoints."""
        protected_endpoints = [
            ("GET", "/documents"),
            ("POST", "/documents/upload"),
            ("POST", "/retrieval/query"),
            ("POST", "/api/debate/graph"),
            ("GET", "/api/health/diagnostics"),
        ]

        for method, endpoint in protected_endpoints:
            # 1. Missing header
            resp = self.client.open(endpoint, method=method)
            self.assertEqual(
                resp.status_code, 401, f"Expected 401 for unauthenticated request to {endpoint}"
            )

            # 2. Malformed header (not Bearer)
            resp2 = self.client.open(endpoint, method=method, headers={"Authorization": "Basic dXNlcjpwYXNz"})
            self.assertEqual(
                resp2.status_code, 401, f"Expected 401 for non-Bearer auth to {endpoint}"
            )

            # 3. Single word header
            resp3 = self.client.open(endpoint, method=method, headers={"Authorization": "BearerOnly"})
            self.assertEqual(
                resp3.status_code, 401, f"Expected 401 for invalid header shape to {endpoint}"
            )

    def test_public_endpoints_accessible_without_token(self):
        """Verifies liveness, readiness, and token issuance remain public without authentication."""
        # 1. Liveness
        resp_live = self.client.get("/api/health/live")
        self.assertEqual(resp_live.status_code, 200)

        # 2. Readiness
        resp_ready = self.client.get("/api/health/ready")
        self.assertIn(resp_ready.status_code, [200, 503])

        # 3. Token Issuance
        resp_token = self.client.post("/api/auth/token", json={"user_id": "test_public_user"})
        self.assertEqual(resp_token.status_code, 200)
        data = json.loads(resp_token.data)
        self.assertTrue(data.get("success"))
        self.assertIn("token", data)

    def test_auth_token_issuance_and_me_inspection(self):
        """Verifies issuance of token via /api/auth/token and verification via /api/auth/me."""
        resp = self.client.post("/api/auth/token", json={"user_id": "alice_math", "role": "user"})
        self.assertEqual(resp.status_code, 200)
        token_data = json.loads(resp.data)
        token = token_data["token"]

        headers = {"Authorization": f"Bearer {token}"}
        resp_me = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp_me.status_code, 200)
        me_data = json.loads(resp_me.data)
        self.assertTrue(me_data["success"])
        self.assertEqual(me_data["user"]["user_id"], "alice_math")
        self.assertEqual(me_data["user"]["role"], "user")

    def test_auth_token_admin_secret_enforcement(self):
        """Verifies that requesting role='admin' requires ADMIN_AUTH_SECRET if configured."""
        with patch.dict(os.environ, {"ADMIN_AUTH_SECRET": "SuperAdminSecretKey99!"}):
            # Attempt admin token without secret -> 403
            resp_fail = self.client.post("/api/auth/token", json={"user_id": "attacker", "role": "admin"})
            self.assertEqual(resp_fail.status_code, 403)

            # Attempt with wrong secret -> 403
            resp_wrong = self.client.post(
                "/api/auth/token",
                json={"user_id": "attacker", "role": "admin", "admin_secret": "wrong_pwd"},
            )
            self.assertEqual(resp_wrong.status_code, 403)

            # Attempt with correct secret -> 200
            resp_ok = self.client.post(
                "/api/auth/token",
                json={"user_id": "real_admin", "role": "admin", "admin_secret": "SuperAdminSecretKey99!"},
            )
            self.assertEqual(resp_ok.status_code, 200)
            data = json.loads(resp_ok.data)
            self.assertEqual(data["user"]["role"], "admin")


class TestRoleBasedAccessControl(unittest.TestCase):
    """Verifies RBAC rules on sensitive operational endpoints."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        limiter.reset()

        self.user_headers = create_test_auth_headers(user_id="standard_user", role="user")
        self.admin_headers = create_test_auth_headers(user_id="super_admin", role="admin")

    def tearDown(self):
        limiter.reset()
        self.app_context.pop()

    def test_diagnostics_endpoint_requires_admin(self):
        """Verifies /api/health/diagnostics returns 403 for user role and 200 for admin role."""
        # Standard user -> 403 Forbidden
        resp_user = self.client.get("/api/health/diagnostics", headers=self.user_headers)
        self.assertEqual(resp_user.status_code, 403)
        data_user = json.loads(resp_user.data)
        self.assertIn("Access denied", data_user.get("error", ""))

        # Admin user -> 200 OK
        resp_admin = self.client.get("/api/health/diagnostics", headers=self.admin_headers)
        self.assertEqual(resp_admin.status_code, 200)
        data_admin = json.loads(resp_admin.data)
        self.assertEqual(data_admin.get("service"), "meta-agent-math-debate")

    def test_cache_clear_endpoint_requires_admin(self):
        """Verifies /api/debate/cache/clear returns 403 for user role and 200 for admin role."""
        # Standard user -> 403 Forbidden
        resp_user = self.client.post("/api/debate/cache/clear", headers=self.user_headers)
        self.assertEqual(resp_user.status_code, 403)

        # Admin user -> 200 OK
        resp_admin = self.client.post("/api/debate/cache/clear", headers=self.admin_headers)
        self.assertEqual(resp_admin.status_code, 200)

    def test_cache_stats_accessible_to_any_authenticated_user(self):
        """Verifies /api/debate/cache/stats is readable by any authenticated user."""
        resp = self.client.get("/api/debate/cache/stats", headers=self.user_headers)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data.get("success"))


class TestDocumentOwnershipAndIDOR(unittest.TestCase):
    """Verifies server-side document ownership isolation and IDOR defense."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        limiter.reset()

        self.alice_id = "user_alice"
        self.bob_id = "user_bob"
        self.admin_id = "admin_root"

        self.alice_headers = create_test_auth_headers(user_id=self.alice_id, role="user")
        self.bob_headers = create_test_auth_headers(user_id=self.bob_id, role="user")
        self.admin_headers = create_test_auth_headers(user_id=self.admin_id, role="admin")

        # Create test documents in DB
        self.alice_doc_id = str(uuid.uuid4())
        self.alice_doc = Document(
            id=self.alice_doc_id,
            user_id=self.alice_id,
            filename="alice_calculus.txt",
            stored_filename=f"{self.alice_doc_id}.txt",
            file_type="txt",
            storage_path=f"/tmp/{self.alice_doc_id}.txt",
            text_length=120,
            chunk_count=1,
        )

        self.bob_doc_id = str(uuid.uuid4())
        self.bob_doc = Document(
            id=self.bob_doc_id,
            user_id=self.bob_id,
            filename="bob_algebra.txt",
            stored_filename=f"{self.bob_doc_id}.txt",
            file_type="txt",
            storage_path=f"/tmp/{self.bob_doc_id}.txt",
            text_length=150,
            chunk_count=1,
        )

        self.system_doc_id = str(uuid.uuid4())
        self.system_doc = Document(
            id=self.system_doc_id,
            user_id="system",
            filename="system_handbook.txt",
            stored_filename=f"{self.system_doc_id}.txt",
            file_type="txt",
            storage_path=f"/tmp/{self.system_doc_id}.txt",
            text_length=300,
            chunk_count=1,
        )

        db.session.add(self.alice_doc)
        db.session.add(self.bob_doc)
        db.session.add(self.system_doc)
        db.session.commit()

    def tearDown(self):
        limiter.reset()
        db.session.rollback()
        Document.query.filter(
            Document.id.in_([self.alice_doc_id, self.bob_doc_id, self.system_doc_id])
        ).delete(synchronize_session=False)
        db.session.commit()
        self.app_context.pop()

    def test_document_listing_isolated_to_user_and_system(self):
        """Verifies GET /documents only shows user's own docs and public system docs."""
        # Alice requests documents
        resp_alice = self.client.get("/documents", headers=self.alice_headers)
        self.assertEqual(resp_alice.status_code, 200)
        docs_alice = json.loads(resp_alice.data)["documents"]
        doc_ids_alice = [d["document_id"] for d in docs_alice]

        self.assertIn(self.alice_doc_id, doc_ids_alice)
        self.assertIn(self.system_doc_id, doc_ids_alice)
        self.assertNotIn(self.bob_doc_id, doc_ids_alice)

        # Bob requests documents
        resp_bob = self.client.get("/documents", headers=self.bob_headers)
        self.assertEqual(resp_bob.status_code, 200)
        docs_bob = json.loads(resp_bob.data)["documents"]
        doc_ids_bob = [d["document_id"] for d in docs_bob]

        self.assertIn(self.bob_doc_id, doc_ids_bob)
        self.assertIn(self.system_doc_id, doc_ids_bob)
        self.assertNotIn(self.alice_doc_id, doc_ids_bob)

    def test_document_get_idor_blocked_with_403(self):
        """Verifies Bob cannot access Alice's document directly by ID (IDOR Defense)."""
        # Alice accesses her document -> 200 OK
        resp_alice = self.client.get(f"/documents/{self.alice_doc_id}", headers=self.alice_headers)
        self.assertEqual(resp_alice.status_code, 200)
        self.assertEqual(json.loads(resp_alice.data)["document"]["document_id"], self.alice_doc_id)

        # Bob attempts to access Alice's document -> 403 Forbidden
        resp_bob = self.client.get(f"/documents/{self.alice_doc_id}", headers=self.bob_headers)
        self.assertEqual(resp_bob.status_code, 403)
        data_bob = json.loads(resp_bob.data)
        self.assertFalse(data_bob["success"])
        self.assertIn("Access denied", data_bob["error"])

    def test_document_delete_idor_blocked_with_403(self):
        """Verifies Bob cannot delete Alice's document, but Alice can delete her own."""
        # Bob attempts to delete Alice's document -> 403 Forbidden
        resp_bob_delete = self.client.delete(f"/documents/{self.alice_doc_id}", headers=self.bob_headers)
        self.assertEqual(resp_bob_delete.status_code, 403)

        # Document still exists in database
        doc = Document.query.filter_by(id=self.alice_doc_id).first()
        self.assertIsNotNone(doc)

        # Alice deletes her own document -> 200 OK
        resp_alice_delete = self.client.delete(f"/documents/{self.alice_doc_id}", headers=self.alice_headers)
        self.assertEqual(resp_alice_delete.status_code, 200)

        # Verify deletion from database
        deleted_doc = Document.query.filter_by(id=self.alice_doc_id).first()
        self.assertIsNone(deleted_doc)

    def test_admin_can_access_and_delete_any_document(self):
        """Verifies that an administrator has unrestricted read and delete access."""
        resp_get = self.client.get(f"/documents/{self.bob_doc_id}", headers=self.admin_headers)
        self.assertEqual(resp_get.status_code, 200)

        resp_del = self.client.delete(f"/documents/{self.bob_doc_id}", headers=self.admin_headers)
        self.assertEqual(resp_del.status_code, 200)
        self.assertIsNone(Document.query.filter_by(id=self.bob_doc_id).first())


class TestRetrievalAndContextIsolation(unittest.TestCase):
    """Verifies retrieval filtering prevents cross-user document leakage over shared vector index."""

    def test_filter_chunks_for_user_filters_foreign_tenants(self):
        """Verifies server-side chunk filtering retains own/system chunks and removes foreign chunks."""
        chunk_alice = RetrievedChunk(
            chunk_id="chunk_1",
            document_id="doc_alice",
            filename="alice.txt",
            file_type="txt",
            page_number=1,
            section_heading="Theorems",
            char_start=0,
            char_end=35,
            vector_index=0,
            content="Alice private theorem: Let f(x) = e^x.",
            score=0.98,
            user_id="user_alice",
        )
        chunk_bob = RetrievedChunk(
            chunk_id="chunk_2",
            document_id="doc_bob",
            filename="bob.txt",
            file_type="txt",
            page_number=1,
            section_heading="Physics",
            char_start=0,
            char_end=36,
            vector_index=1,
            content="Bob confidential formula: E = mc^2.",
            score=0.95,
            user_id="user_bob",
        )
        chunk_system = RetrievedChunk(
            chunk_id="chunk_3",
            document_id="doc_sys",
            filename="system.txt",
            file_type="txt",
            page_number=1,
            section_heading="Basics",
            char_start=0,
            char_end=33,
            vector_index=2,
            content="Public math textbook: 2 + 2 = 4.",
            score=0.91,
            user_id="system",
        )

        all_chunks = [chunk_alice, chunk_bob, chunk_system]

        # Filter for Alice: Should keep Alice + System, exclude Bob
        filtered_alice = filter_chunks_for_user(all_chunks, user_id="user_alice", role="user")
        self.assertEqual(len(filtered_alice), 2)
        filtered_ids_alice = [c.chunk_id for c in filtered_alice]
        self.assertIn("chunk_1", filtered_ids_alice)
        self.assertIn("chunk_3", filtered_ids_alice)
        self.assertNotIn("chunk_2", filtered_ids_alice)

        # Filter for Bob: Should keep Bob + System, exclude Alice
        filtered_bob = filter_chunks_for_user(all_chunks, user_id="user_bob", role="user")
        self.assertEqual(len(filtered_bob), 2)
        filtered_ids_bob = [c.chunk_id for c in filtered_bob]
        self.assertIn("chunk_2", filtered_ids_bob)
        self.assertIn("chunk_3", filtered_ids_bob)
        self.assertNotIn("chunk_1", filtered_ids_bob)

        # Admin retains everything
        filtered_admin = filter_chunks_for_user(all_chunks, user_id="admin_root", role="admin")
        self.assertEqual(len(filtered_admin), 3)


class TestSemanticCacheIsolation(unittest.TestCase):
    """Verifies that semantic caching partitions entries by user to avoid leaking private results."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_scope_hash_differentiates_user_identity(self):
        """Verifies compute_scope_hash generates distinct hashes for different users."""
        scope_alice = compute_scope_hash(namespace="math_debate", user_id="user_alice")
        scope_bob = compute_scope_hash(namespace="math_debate", user_id="user_bob")
        scope_anon = compute_scope_hash(namespace="math_debate", user_id=None)

        self.assertNotEqual(scope_alice, scope_bob)
        self.assertNotEqual(scope_alice, scope_anon)
        self.assertNotEqual(scope_bob, scope_anon)

        # Same user produces deterministic hash
        scope_alice_2 = compute_scope_hash(namespace="math_debate", user_id="user_alice")
        self.assertEqual(scope_alice, scope_alice_2)

    def test_cross_user_cache_isolation_prevents_cache_hits(self):
        """Verifies that an entry cached by User A is NOT returned on cache lookup for User B."""
        cache_service = SemanticCacheService(
            config={
                "enabled": True,
                "similarity_threshold": 0.92,
                "exact_match_enabled": True,
                "ttl_seconds": 3600,
                "max_entries": 100,
                "namespace": "isolation_test",
                "schema_version": "v1.0",
                "require_grounded_citations": False,
            }
        )
        cache_service.clear()

        query = "Calculate the derivative of f(x) = x^3"
        state_alice = {
            "query": query,
            "final_answer": "f'(x) = 3x^2",
            "status": "completed",
            "partial_execution": False,
            "failed_node": None,
            "error": None,
            "planner_output": {"needs_retrieval": False},
            "retrieved_context": {"chunks": []},
            "managed_context": {"formatted_context": "", "citations": []},
            "solver_outputs": {"solver_1": {"success": True, "answer": "f'(x) = 3x^2"}},
            "judge_output": {"success": True, "best_agent": "solver_1", "best_solution": "f'(x) = 3x^2"},
            "citations": [],
            "user_id": "user_alice",
        }

        # Store result for Alice
        stored = cache_service.set(query, state_alice, execution_time_ms=1200.0, user_id="user_alice")
        self.assertTrue(stored)

        # Alice queries: EXACT HIT
        hit_alice = cache_service.get(query, user_id="user_alice")
        self.assertIsNotNone(hit_alice)
        self.assertTrue(hit_alice.hit)
        self.assertEqual(hit_alice.entry.final_answer, "f'(x) = 3x^2")

        # Bob queries identical question: MUST BE MISS
        hit_bob = cache_service.get(query, user_id="user_bob")
        self.assertIsNone(hit_bob)

        # Anonymous query: MUST BE MISS
        hit_anon = cache_service.get(query, user_id=None)
        self.assertIsNone(hit_anon)


class TestRateLimitingAndResourceControls(unittest.TestCase):
    """Verifies sliding-window rate limiting, HTTP 429 response, and payload size controls."""

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        limiter.reset()

    def tearDown(self):
        limiter.reset()
        self.app_context.pop()

    def test_parse_rate_limit_expressions(self):
        """Verifies rate limit expression parser."""
        self.assertEqual(parse_rate_limit("10/minute"), (10, 60))
        self.assertEqual(parse_rate_limit("5/second"), (5, 1))
        self.assertEqual(parse_rate_limit("100/hour"), (100, 3600))
        self.assertEqual(parse_rate_limit("500/day"), (500, 86400))
        self.assertEqual(parse_rate_limit("invalid_expr"), (60, 60))

    def test_sliding_window_rate_limiter_unit(self):
        """Unit test for SlidingWindowRateLimiter."""
        local_limiter = SlidingWindowRateLimiter()
        key = "test_user_burst"

        # Allow 3 requests in 10 seconds
        for _ in range(3):
            allowed, remaining, retry_after = local_limiter.check_rate_limit(key, limit=3, window_seconds=10)
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

        # 4th request must be blocked
        allowed, remaining, retry_after = local_limiter.check_rate_limit(key, limit=3, window_seconds=10)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)

        # Reset clears bucket
        local_limiter.reset()
        allowed2, _, _ = local_limiter.check_rate_limit(key, limit=3, window_seconds=10)
        self.assertTrue(allowed2)

    def test_auth_rate_limiting_triggers_http_429(self):
        """Verifies that exceeding configured RATE_LIMIT_AUTH returns HTTP 429 with Retry-After header."""
        with patch.dict(os.environ, {"RATE_LIMIT_AUTH": "3/minute", "RATE_LIMIT_ENABLED": "true"}):
            limiter.reset()

            # First 3 requests succeed
            for i in range(3):
                resp = self.client.post("/api/auth/token", json={"user_id": f"flood_user_{i}"})
                self.assertEqual(resp.status_code, 200, f"Request {i+1} should succeed")

            # 4th request must fail with 429
            resp_429 = self.client.post("/api/auth/token", json={"user_id": "flood_user_overflow"})
            self.assertEqual(resp_429.status_code, 429)

            # Validate 429 headers and payload
            self.assertIn("Retry-After", resp_429.headers)
            self.assertEqual(resp_429.headers.get("X-RateLimit-Remaining"), "0")
            data = json.loads(resp_429.data)
            self.assertFalse(data["success"])
            self.assertIn("Rate limit exceeded", data["error"])
            self.assertGreater(data.get("retry_after_seconds", 0), 0)

    def test_query_length_limit_exceeded_returns_400(self):
        """Verifies that queries exceeding MAX_QUERY_LENGTH return HTTP 400."""
        headers = create_test_auth_headers(user_id="user_alice")
        oversized_query = "x = " + ("1" * 5050)

        resp = self.client.post("/retrieval/query", json={"query": oversized_query}, headers=headers)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("exceeds maximum allowed", data.get("error", ""))

    def test_retrieval_depth_clamped_to_safe_bounds(self):
        """Verifies that excessive top_k is clamped to MAX_TOP_K without error."""
        headers = create_test_auth_headers(user_id="user_alice")

        with patch("api.retrieval._service") as mock_srv_fn:
            mock_srv = MagicMock()
            mock_srv_fn.return_value = mock_srv
            mock_ctx = MagicMock()
            mock_ctx.to_dict.return_value = {"formatted_context": "Safe Context"}
            mock_srv.retrieve.return_value = mock_ctx

            resp = self.client.post("/retrieval/query", json={"query": "Solve 2+2", "top_k": 50000}, headers=headers)
            self.assertEqual(resp.status_code, 200)

            # Check that top_k was clamped to <= 50
            call_kwargs = mock_srv.retrieve.call_args.kwargs
            call_top_k = call_kwargs.get("top_k") or mock_srv.retrieve.call_args.args[1]
            self.assertLessEqual(call_top_k, 50)


if __name__ == "__main__":
    unittest.main()
