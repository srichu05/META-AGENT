# Phase 3.5 — Production Security, Authentication & Access Control Report

**System:** Mini Meta-Agent Search for Math Word Problems and Automated Multi-Agent Debate System  
**Date:** November 2026  
**Status:** Completed & Validated (114 / 114 Regression Tests Passing)  
**Schema Revision:** `c8241d7e3f91` (`ix_documents_user_id`)  

---

## 1. Executive Summary

Phase 3.5 establishes production-grade security, authentication, tenant isolation, and resource protection for the Meta-Agent Math Debate System. Prior to Phase 3.5, the backend was accessible without credential verification, document metadata lacked ownership attribution, retrieved document chunks were drawn uniformly across all indexed records, semantic cache keys did not differentiate users, and endpoints lacked rate limiting against brute force and resource exhaustion.

The Phase 3.5 implementation introduces:
1. **RFC 7519 HS256 JWT Bearer Authentication**: Native, dependency-free token generation and constant-time signature validation implemented via Python's standard library (`hmac`, `hashlib`, `json`, `base64`).
2. **Role-Based Access Control (RBAC)**: Enforced least privilege across operational endpoints. Administrative endpoints (`/api/health/diagnostics`, `/api/debate/cache/clear`) require administrative role privileges (`role="admin"`).
3. **Document Ownership & Insecure Direct Object Reference (IDOR) Defense**: Database migration `c8241d7e3f91` added `user_id` to `Document`. All upload, listing, retrieval, and deletion operations enforce strict server-side ownership checks (403 Forbidden on foreign document access).
4. **FAISS & RAG Retrieval Isolation**: In a shared FAISS vector index architecture, server-side post-retrieval filtering (`filter_chunks_for_user`) deterministically removes chunks owned by other users prior to reranking, prompt context assembly, and citation generation.
5. **Cross-User Semantic Cache Isolation**: User identity is bound to the cache key scope hash (`compute_scope_hash`), guaranteeing that private queries, solutions, and grounded citations are never served across tenants or users.
6. **Thread-Safe Sliding-Window Rate Limiting**: Built-in sliding-window limiter enforcing quota policies across authentication, debate execution, and document uploads with standard HTTP 429 status and `Retry-After` headers.
7. **Resource & Payload Bounds**: Protection against oversized payloads (`MAX_QUERY_LENGTH=5000` characters) and retrieval depth denial-of-service (`MAX_TOP_K=50`).

All 114 unit, integration, and security tests across Phases 3.0 through 3.5 pass with 100% success.

---

## 2. Authentication Architecture

### 2.1 RFC 7519 HS256 JWT Token Implementation
To strictly adhere to zero unnecessary third-party dependencies, token authentication was implemented directly against standard RFC 7519 specifications using Python 3.11 standard library modules (`hmac`, `hashlib`, `json`, `base64`):

- **Header**: Standard `{"alg": "HS256", "typ": "JWT"}` encoded with URL-safe base64 without padding.
- **Payload**: Contains standard claims:
  - `sub`: Authenticated User Identifier (string)
  - `role`: Role assignment (`user` or `admin`)
  - `iat`: Issued At timestamp (Unix epoch seconds)
  - `exp`: Expiration timestamp (Unix epoch seconds, default: 3600s / 1 hour)
  - Optional custom claims (e.g. tenant, department).
- **Signature**: `HMAC-SHA256(secret_key, header_b64 + "." + payload_b64)`.
- **Validation**: Signature comparison uses `hmac.compare_digest` to eliminate side-channel timing attacks. Expiration is verified against system UTC time with strict rejection on expired timestamps (`TokenExpiredError`).

### 2.2 Token Lifecycle & Public Endpoints
- **Token Issuance (`POST /api/auth/token`)**: Public endpoint accepting `{"user_id": "...", "role": "user"}` and returning a signed JWT. If requesting `role="admin"`, the request must supply matching `ADMIN_AUTH_SECRET` if configured in the environment.
- **Session Introspection (`GET /api/auth/me`)**: Authenticated endpoint returning decoded token claims.
- **Protected Endpoints**:
  - `POST /api/debate/graph`: Multi-agent debate workflow execution.
  - `GET /api/debate/cache/stats`: Semantic cache telemetry.
  - `POST /api/debate/cache/clear`: Cache invalidation (admin only).
  - `POST /documents/upload`: Knowledge base file ingestion.
  - `GET /documents`: User document listing.
  - `GET /documents/<id>`: Document metadata and chunk inspection.
  - `DELETE /documents/<id>`: Document deletion.
  - `POST /retrieval/query`: Hybrid search query.
  - `GET /api/health/diagnostics`: System diagnostics (admin only).
- **Public Endpoints Preserved**:
  - `GET /api/health/live`: Unauthenticated container liveness probe.
  - `GET /api/health/ready`: Unauthenticated readiness probe for orchestrators (Kubernetes/ECS).
  - `POST /api/auth/token`: Token issuance.

---

## 3. Authorization & IDOR Defense

### 3.1 Relational Schema Migration (`c8241d7e3f91`)
The PostgreSQL relational schema was upgraded using Flask-Migrate / Alembic:
```python
# backend/migrations/versions/c8241d7e3f91_add_user_id_to_documents.py
def upgrade():
    op.add_column('documents', sa.Column('user_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
```
- Existing documents default to `user_id="system"`, making them universally accessible as public reference corpora.
- All new documents ingested via `POST /documents/upload` are stamped with the authenticated user's ID (`g.current_user["user_id"]`).

### 3.2 Server-Side Ownership Controls
Server-side ownership verification (`backend/security/authorization.py`) prevents Insecure Direct Object References (IDOR):
1. **Document Listing (`GET /documents`)**: Filtered at query time: `Document.user_id == user_id | Document.user_id.is_(None) | Document.user_id == "system"`. User B cannot see User A's uploaded documents.
2. **Direct Document Inspection (`GET /documents/<id>`)**: Server checks `can_access_document(document, user_id, role)`. If User B attempts to access User A's document, the server returns HTTP 403 Forbidden with zero chunk data.
3. **Document Deletion (`DELETE /documents/<id>`)**: Server enforces ownership. User B receives HTTP 403 Forbidden when attempting to delete User A's document.
4. **Administrative Override**: Users with `role="admin"` retain unrestricted operational authority to audit or purge any document.

---

## 4. FAISS & Context Retrieval Isolation

### 4.1 Shared FAISS Vector Index Boundary
Because FAISS flat and IVFFlat indexes store unpartitioned raw vector embeddings in a single file (`document_vectors.faiss`), vector distance calculations are performed globally across the corpus.

### 4.2 Multi-Stage Context Filtering Defense
To prevent cross-tenant information disclosure:
1. **Metadata Hydration**: FAISS returns candidate `vector_index` positions. The system hydrates these candidates against PostgreSQL `document_chunks` joined with `documents`, retrieving the owning `user_id`.
2. **Chunk Filtering (`filter_chunks_for_user`)**: Before reciprocal rank fusion (RRF), Cohere reranking, context formatting, or citation generation, candidate chunks are evaluated:
   $$\text{Keep Chunk } c \iff c.\text{user\_id} \in \{\text{None}, \text{"system"}, u_{\text{requesting}}\} \lor \text{role} == \text{"admin"}$$
3. Chunks belonging to another tenant are dropped and logged at warning level:
   `🛡️ Retrieval isolation: Filtered chunk <id> owned by 'user_A' from query requested by user 'user_B'.`
4. The filtered chunk list guarantees that foreign private text never enters LLM prompt context or citation metadata.

---

## 5. Cross-User Semantic Cache Isolation

### 5.1 Deterministic User-Scoped Hashing
In Phase 3.1, semantic cache keys were scoped by namespace, schema version, prompt version, model, and temperature. In Phase 3.5, `compute_scope_hash` incorporates user identity:
```python
def compute_scope_hash(..., user_id: Optional[str] = None) -> str:
    user_segment = f":user_{user_id}" if user_id else ""
    scope_str = f"{namespace}:{schema_version}:{prompt_version}:{model}:{temperature:.2f}{user_segment}"
    return hashlib.sha256(scope_str.encode("utf-8")).hexdigest()[:16]
```

### 5.2 Cache Protection Guarantees
- **Tier 1 (Exact Match)**: O(1) hash lookup combines `normalized_query` and `scope_hash`. If User A solves a problem and it is cached, User B querying the exact same problem generates a distinct `scope_hash`, resulting in a cache miss.
- **Tier 2 (Semantic Match)**: Vector candidate evaluation rejects candidates where `candidate.scope_hash != current_scope_hash`.
- **Privacy Assurance**: Private document citations, custom agent reflections, and user-specific reasoning chains are isolated strictly to the user who executed the query.

---

## 6. Rate Limiting & Resource Abuse Controls

### 6.1 Sliding-Window Rate Limiter
A thread-safe `SlidingWindowRateLimiter` (`backend/security/rate_limiter.py`) tracks request timestamps using double-ended queues (`collections.deque`) protected by `threading.Lock`:
- **Scopes & Default Quotas**:
  - `auth`: `10/minute` (brute force protection on token endpoint)
  - `debate`: `30/minute` (LLM quota and token exhaustion defense)
  - `upload`: `10/minute` (disk space and parsing exhaustion defense)
  - `default`: `60/minute`
- **Client Identification**: Uses `user:<user_id>` for authenticated requests and `ip:<remote_addr>` for unauthenticated endpoints.
- **HTTP 429 Response**: Returns:
  ```json
  {
    "success": false,
    "error": "Rate limit exceeded. Allowed 10 requests per 60 seconds.",
    "limit": "10/minute",
    "retry_after_seconds": 45
  }
  ```
  Headers attached: `Retry-After: 45`, `X-RateLimit-Limit: 10`, `X-RateLimit-Remaining: 0`.

### 6.2 Input & Retrieval Bounds
- **Query Length Clamping**: Input problem and retrieval queries are limited to `MAX_QUERY_LENGTH=5000` characters. Exceeding queries receive HTTP 400 Bad Request.
- **Retrieval Depth Clamping**: `top_k` parameters are clamped to `[1, MAX_TOP_K=50]` to prevent memory exhaustion and excessive database serialization load.

---

## 7. Verification & Test Results

The new dedicated test suite `backend/tests/test_production_security.py` executes 22 adversarial security tests:

| Test Class | Test Case | Target Capability | Result |
| :--- | :--- | :--- | :--- |
| `TestJWTAuthentication` | `test_jwt_generation_and_validation_roundtrip` | RFC 7519 HS256 claims roundtrip | PASS |
| `TestJWTAuthentication` | `test_jwt_expired_token_rejected` | Expiration check & HTTP 401 | PASS |
| `TestJWTAuthentication` | `test_jwt_tampered_signature_rejected` | Signature integrity & HTTP 401 | PASS |
| `TestJWTAuthentication` | `test_missing_and_malformed_auth_headers_return_401` | Header format validation | PASS |
| `TestJWTAuthentication` | `test_public_endpoints_accessible_without_token` | Liveness, readiness, token endpoint | PASS |
| `TestJWTAuthentication` | `test_auth_token_issuance_and_me_inspection` | Token issue & session inspection | PASS |
| `TestJWTAuthentication` | `test_auth_token_admin_secret_enforcement` | Admin secret credential check | PASS |
| `TestRoleBasedAccessControl` | `test_diagnostics_endpoint_requires_admin` | RBAC on `/api/health/diagnostics` | PASS |
| `TestRoleBasedAccessControl` | `test_cache_clear_endpoint_requires_admin` | RBAC on `/api/debate/cache/clear` | PASS |
| `TestRoleBasedAccessControl` | `test_cache_stats_accessible_to_any_authenticated_user` | User access on cache telemetry | PASS |
| `TestDocumentOwnershipAndIDOR` | `test_document_listing_isolated_to_user_and_system` | Document listing isolation | PASS |
| `TestDocumentOwnershipAndIDOR` | `test_document_get_idor_blocked_with_403` | IDOR prevention on `GET /documents/<id>` | PASS |
| `TestDocumentOwnershipAndIDOR` | `test_document_delete_idor_blocked_with_403` | IDOR prevention on `DELETE /documents/<id>` | PASS |
| `TestDocumentOwnershipAndIDOR` | `test_admin_can_access_and_delete_any_document` | Admin universal access | PASS |
| `TestRetrievalAndContextIsolation` | `test_filter_chunks_for_user_filters_foreign_tenants` | Server-side chunk isolation | PASS |
| `TestSemanticCacheIsolation` | `test_scope_hash_differentiates_user_identity` | Deterministic user scope hashing | PASS |
| `TestSemanticCacheIsolation` | `test_cross_user_cache_isolation_prevents_cache_hits` | Cross-user cache miss guarantee | PASS |
| `TestRateLimitingAndResourceControls` | `test_parse_rate_limit_expressions` | Expression string parsing | PASS |
| `TestRateLimitingAndResourceControls` | `test_sliding_window_rate_limiter_unit` | Sliding-window memory state unit test | PASS |
| `TestRateLimitingAndResourceControls` | `test_auth_rate_limiting_triggers_http_429` | HTTP 429 & Retry-After headers | PASS |
| `TestRateLimitingAndResourceControls` | `test_query_length_limit_exceeded_returns_400` | Max query length rejection (HTTP 400) | PASS |
| `TestRateLimitingAndResourceControls` | `test_retrieval_depth_clamped_to_safe_bounds` | Retrieval depth clamped to $\le 50$ | PASS |

### Full Test Suite Regression Summary
```
Ran 114 tests in 52.415s across 7 modules:
- backend.tests.test_production_security:  22 tests OK
- backend.tests.test_deployment_readiness: 17 tests OK
- backend.tests.test_rag_security:         15 tests OK
- backend.tests.test_llm_judge:            31 tests OK
- backend.tests.test_semantic_cache:       16 tests OK
- backend.tests.test_rag_pipeline:          5 tests OK
- backend.tests.test_evaluation:            8 tests OK

Result: OK (114 passing, 0 failures, 0 errors)
```

---

## 8. Configuration Reference

The following environment variables control Phase 3.5 security parameters:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `JWT_SECRET_KEY` | Falls back to `SECRET_KEY` | Secret key used to sign and verify RFC 7519 HS256 JWT tokens. |
| `JWT_EXPIRATION_SECONDS` | `3600` (1 hour) | Default validity duration of issued JWT tokens in seconds. |
| `AUTH_ENABLED` | `true` | When true (or in production), mandatory Bearer token auth is enforced. |
| `ADMIN_AUTH_SECRET` | None | Passphrase required to claim `role="admin"` via `/api/auth/token`. |
| `RATE_LIMIT_ENABLED` | `true` | When true, sliding-window rate limits are enforced. |
| `RATE_LIMIT_AUTH` | `10/minute` | Rate limit for `/api/auth/token` endpoint. |
| `RATE_LIMIT_DEBATE` | `30/minute` | Rate limit for `/api/debate/graph` and `/retrieval/query`. |
| `RATE_LIMIT_UPLOAD` | `10/minute` | Rate limit for `/documents/upload`. |
| `MAX_QUERY_LENGTH` | `5000` | Maximum character length for incoming problem queries. |
| `MAX_TOP_K` | `50` | Maximum allowable retrieval top_k depth. |

---

## 9. Architectural Limitations & Production Deployment Guidance

1. **Physical Vector Index Boundary**:
   - *Limitation*: All document vectors reside in a single shared FAISS index file (`document_vectors.faiss`). Isolation is currently achieved at the application layer through database metadata filtering.
   - *Production Recommendation*: For strict multi-tenant compliance (e.g. SOC2, HIPAA), separate FAISS indexes or partition namespaces (e.g., using pgvector with row-level security / schema per tenant) should be adopted.
2. **In-Memory Rate Limiting**:
   - *Limitation*: The sliding-window rate limiter stores request timestamps in Python process memory. In a multi-worker WSGI/Gunicorn setup or clustered multi-instance deployment, rate limits are tracked per process rather than cluster-wide.
   - *Production Recommendation*: Back the rate limiter with a centralized Redis instance using Redis sorted sets (`ZADD` / `ZREMRANGEBYSCORE`) or enforce limits at an API Gateway / reverse proxy (e.g. NGINX `limit_req`, AWS WAF, or Cloudflare).
3. **Transport Layer Security (TLS)**:
   - *Limitation*: The Flask backend operates over plain HTTP in local and test environments.
   - *Production Recommendation*: Place the application behind an SSL-terminating reverse proxy (NGINX, Caddy, AWS ALB) configured for HTTPS with TLS 1.3 to protect tokens in transit.
4. **Key Management**:
   - *Limitation*: Secrets (`JWT_SECRET_KEY`, `ADMIN_AUTH_SECRET`) are read from environment variables.
   - *Production Recommendation*: Integrate a dedicated Hardware Security Module or secret manager (AWS Secrets Manager, Google Cloud Secret Manager, or HashiCorp Vault) with periodic key rotation.

