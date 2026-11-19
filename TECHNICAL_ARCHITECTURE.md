# Technical Architecture – Meta-Agent Math Debate System (Draft 2)

---

## 1. Project Overview

The **Meta-Agent Math Debate System** is a modular, production-ready Flask backend that solves complex mathematical problems through a multi-agent debate workflow supported by personalized Retrieval-Augmented Generation (RAG) and automated RAGAS evaluation.

The system emphasizes explainability, modularity, fault tolerance, and quantitative performance evaluation.

---

## 2. Technology Stack

- **Backend Framework**: Flask 3.0, Flask-CORS, Flask-SQLAlchemy, Flask-Migrate
- **Relational Database**: PostgreSQL / SQLite (via SQLAlchemy ORM)
- **Vector Search**: FAISS (`IndexFlatIP` inner-product similarity search)
- **Embedding Model**: BAAI BGE Embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **Lexical Retrieval**: BM25 keyword search
- **Reranker**: Cohere Rerank (`rerank-v3.5`)
- **Orchestration**: LangGraph DAG / LangChain Core (9-node state graph)
- **Document Ingestion**: PyMuPDF (PDF), python-docx (DOCX), PaddleOCR (Image OCR)
- **Evaluation & Benchmarking**: RAGAS (Faithfulness, Answer Relevance, Context Precision, Context Recall) + GSM8K benchmark harness
- **Cloud LLM Providers**: Google Gemini, Groq, OpenRouter, Cohere

---

## 3. End-to-End Orchestration Architecture

```
User Query
    ↓
Planner Node (Query decomposition & retrieval strategy)
    ↓
Hybrid Retrieval Node (FAISS vector search + BM25 keyword search)
    ↓
RRF Fusion ($k=60$) & PostgreSQL Metadata Hydration
    ↓
Cohere Rerank Node (`rerank-v3.5` with fallback)
    ↓
Context Manager Node (Deduplication, score filtering, token budget)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Multi-Solver Parallel Reasoning Nodes                      │
│ ├── Solver 1 (Analytical / Step-by-Step) → Google Gemini    │
│ ├── Solver 2 (Fast / Algebraic)         → Groq              │
│ └── Solver 3 (Alternative / Verification) → OpenRouter      │
└─────────────────────────────────────────────────────────────┘
    ↓
Reflection Agent Node (Cross-solution contradiction & error audit)
    ↓
Judge Agent Node (Multi-criteria scoring & best solution selection)
    ↓
Citation Generator Node (Source document attribution with anti-fabrication grounding filter)
    ↓
Final Answer + RAG Citations
```

- **Execution Mode Observability**: `MathDebateGraph` populates `execution_mode` (`"langgraph"` vs `"builtin_dag"`), `partial_execution` (boolean flag set if intermediate nodes catch exceptions), and `failed_node` (tracking the exact node failure). Intermediate solver outputs are preserved even if later stages fail.

---

## 4. Provider Gateway & Routing Architecture

All cloud LLM and reranker calls are routed authoritatively through `ProviderRouter`:

- **Active Provider Adapters**:
  - `GeminiAdapter`: Default reasoning engine (`gemini-2.5-flash`)
  - `GroqAdapter`: High-speed inference (`llama-3.3-70b-versatile`)
  - `OpenRouterAdapter`: Diverse reasoning solver (`deepseek/deepseek-r1-distill-llama-70b`)
  - `CohereAdapter`: Reranking engine (`rerank-v3.5`)
- **Resilience Features**:
  - Automatic cross-provider fallback (`GEMINI -> GROQ -> OPENROUTER`) with finite deduplicated traversal to prevent infinite fallback loops.
  - Transparent fallback observability: `ProviderResponse` records `intended_provider`, `actual_provider`, `actual_model`, `fallback_occurred`, `fallback_reason`, `attempts`, and standardized `error_category` (`AUTHENTICATION_ERROR`, `RATE_LIMIT`, `MODEL_NOT_FOUND`, `TIMEOUT`, `CONNECTION_ERROR`, `SERVER_ERROR`, `PROVIDER_ERROR`).
  - Response normalization into standardized `ProviderResponse` dataclass.
  - Latency, token usage, and error metrics tracked via `ProviderMetrics`.

---

## 5. RAG Retrieval Subsystem

1. **Document Ingestion**:
   - Parses PDF, DOCX, TXT, Markdown, and handwritten notes/images via PaddleOCR.
   - Cleans text and applies semantic chunking (`chunk_size=500`, `chunk_overlap=50`).
   - Generates 384-d normalized BGE embeddings and appends to `document_vectors.faiss`.
   - Stores chunk location metadata (`filename`, `page_number`, `section_heading`, `char_start`, `char_end`) in PostgreSQL.
2. **Hybrid Retrieval**:
   - Computes inner-product similarity across FAISS index ($w=0.7$).
   - Computes BM25 keyword frequency scores ($w=0.3$).
   - Merges candidate rankings using Reciprocal Rank Fusion ($RRF = \sum \frac{w}{60 + \text{rank}}$).
   - Re-ranks top candidates via Cohere Rerank API.
   - Observability: `RetrievedContext` exposes `error`, `rerank_status` (`"disabled"`, `"success"`, `"fallback"`, `"skipped_missing_credentials"`, `"skipped_disabled"`, `"skipped_empty"`), and explicit diagnostics for 0-result states (`vector_index_empty`, `no_matches_found`, `database_query_error`).
3. **Context Manager**:
   - Deduplicates chunks, filters below similarity threshold, and formats structured prompt context within configurable character/token budget (`max_context_length=4000`).
4. **Citation Grounding**:
   - Anti-fabrication lexical/marker grounding filter in `citation_generator_node` ensures citations are only attached when candidate chunks were genuinely utilized in the final answer.

---

## 6. Evaluation & Benchmarking Subsystem

- **RAGAS Metric Evaluator** (`backend/evaluation/ragas_evaluator.py`):
  - **Faithfulness**: Measures grounding of generated answer in retrieved context.
  - **Answer Relevance**: Measures semantic alignment between user question and final answer.
  - **Context Precision**: Measures rank positioning of relevant context chunks.
  - **Context Recall**: Measures coverage of reference answer claims in context.
  - **Mode Transparency**: Explicitly tags `evaluation_mode` (`"genuine_ragas"`, `"heuristic"`, `"deterministic"`, or `"mock"`) and `ragas_installed` so heuristic metrics are never misreported as genuine RAGAS.
- **GSM8K Benchmark Harness** (`backend/evaluation/dataset.py`, `backend/evaluation/benchmark_runner.py`):
  - Curated 10-problem GSM8K dataset subset with reference answers.
  - Executes questions end-to-end through `MathDebateGraph`, capturing all intermediate solver states, reflection notes, and judge decisions.
  - Exports aggregated reports in JSON and CSV formats with evaluation mode metadata.
- **Evaluation REST Endpoints**:
  - `POST /api/evaluation/benchmark`: Triggers benchmark run over $N$ items.
  - `GET /api/evaluation/benchmark`: Returns cached or fresh benchmark metrics report.
  - `GET /api/evaluation/status`: Returns evaluation subsystem mode, library availability, and descriptions.

---

## 7. Database Architecture

- **Migrations Repository**: Managed via Flask-Migrate / Alembic under `backend/migrations/` (`b4131a3fb826_create_documents_and_chunks_schema.py`). Destructive auto-drops are prevented across production and testing lifecycles.
- **`documents`**: Tracks uploaded files, file hashes, MIME types, processing status, and text length.
- **`document_chunks`**: Stores chunk text, character boundaries, section headings, page numbers, and deterministic `vector_index` pointers mapping to FAISS.
- **`student`**: Preserved legacy schema table for student interactions.
- **`system_settings`**: Key-value runtime configuration persistence.