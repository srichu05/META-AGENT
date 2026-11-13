# Architecture Audit: Component Inventory & Real vs. Stated Architecture

**Audit Phase:** Phase 1 — Meta-Agent Baseline Audit, Performance Profiling & Evaluation  
**Target Commit:** `85c9af20c0958ef41e70f54002f494b1d1481765`  
**Execution Environment:** Windows 10 (10.0.22621), Python 3.11.9 (64-bit AMD64)  
**Database:** PostgreSQL 16 (SQLAlchemy engine connected)  
**Target Architecture:** Draft 2 Specification (`PRD.md`, `TECHNICAL_ARCHITECTURE.md`)

---

## 1. Executive Summary

This architecture audit evaluates the exact disparity between the **documented system architecture** (Draft 2 target specifications) and the **concrete runtime implementation** of the Meta-Agent Math Debate System. 

Every component has been verified through static inspection of AST/imports and dynamic execution of requests through the system's entrypoints (`backend/app.py`, `backend/graph/workflow.py`, `backend/retrieval/service.py`, `backend/providers/router.py`).

### Key High-Level Findings
1. **LangGraph vs. Fallback State Graph**: The external package `langgraph` is **not installed** in the runtime virtual environment (`backend/venv`). However, `backend/graph/workflow.py` contains a fully functional built-in sequential state-machine fallback (`_BuiltinStateGraph`) that faithfully executes the 9-node DAG in Python memory.
2. **PostgreSQL & Database Tables**: SQLAlchemy engine connects successfully to the local PostgreSQL instance via `DATABASE_URL`. However, the relational tables (`documents`, `document_chunks`) have not been migrated via Alembic/metadata (`psycopg2.errors.UndefinedTable: relation "document_chunks" does not exist`).
3. **FAISS & Local Embedding**: `BAAI/bge-small-en-v1.5` dense embedding generation and FAISS (`IndexFlatIP`) index operations are 100% active and functional. When the database is unpopulated, FAISS reports size 0 and gracefully returns empty lists without unhandled exceptions.
4. **BM25 Search**: Functional via `rank_bm25.BM25Okapi`. In the live request path, BM25 attempts to load document chunks from PostgreSQL; because the database table is unmigrated, it catches the SQLAlchemy error and returns 0 documents.
5. **Cohere Reranker**: Implemented in `backend/retrieval/reranker.py` via `CohereReranker` calling `api.cohere.com/v2/rerank`. In default configuration, `RAG_CONFIG["cohere_rerank_enabled"]` is set to `False`, activating `PassThroughReranker`.
6. **Multi-Model Provider Routing**: `ProviderRouter` handles model selection across Gemini, Groq, and OpenRouter. 
   - `GEMINI`: Primary active provider (`gemini-2.5-flash`), functional at runtime until API quota limits are encountered. Free tier enforces a strict 20-request/day quota (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`).
   - `GROQ`: Configured with `llama-3.3-70b-versatile`, which returns `HTTP 404: The model does not exist or you do not have access to it` on the current API tier (available models on key: `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`).
   - `OPENROUTER`: Configured with `deepseek/deepseek-r1-distill-llama-70b`, currently failing due to zero account balance.
   - Fallback cascading works robustly: when cloud providers fail, solvers and judge fall back to graceful degradation stubs without crashing.
7. **RAGAS Evaluation Subsystem**: The `ragas` package is **not installed** in the virtual environment. `backend/evaluation/ragas_evaluator.py` detects this at initialization and routes evaluation requests to custom heuristic regex and keyword matchers.

---

## 2. Component Inventory Matrix

| Component Name | Stated Purpose (Draft 2) | Source Path | Classification | In Runtime Path? | Real Observed Behavior | Known Gaps vs Spec |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Flask API Server** | REST API endpoints for solving, retrieval, upload, health | `backend/app.py` | Real / Active | Yes | Listens on port 5000; exposes `/api/v1/*` routes with JSON schema validation | Zero critical gaps |
| **MathDebateGraph** | Orchestrates 9-node debate workflow | `backend/graph/workflow.py` | Real (Internal Fallback) | Yes | Sequential state machine executing: Planner -> Retrieval -> Context -> Solvers (1,2,3) -> Reflection -> Judge -> Citation | `langgraph` package not installed; runs built-in linear DAG executor |
| **Planner Node** | Deconstructs problem into reasoning plan | `backend/graph/nodes/planner_node.py` | Real / Active | Yes | Invokes `PlannerAgent.create_plan` via `ProviderRouter` | Falls back to static template plan if LLM is unavailable |
| **Retrieval Node** | Retrieves chunks via hybrid RAG | `backend/graph/nodes/retrieval_node.py` | Real / Active | Yes | Invokes `RetrievalService.retrieve` | Returns 0 chunks when DB tables/indices are unmigrated |
| **Context Manager Node** | Synthesizes & formats retrieved context | `backend/graph/nodes/context_node.py` | Real / Active | Yes | Formats chunk metadata and citations for solver injection | Passes empty string gracefully when 0 chunks retrieved |
| **Solver 1 (Gemini)** | Primary mathematical solver | `backend/graph/nodes/solver_nodes.py` | Real / Active | Yes | Dispatches to `GeminiAdapter` (`gemini-2.5-flash`) | Subject to 20 request/day free-tier rate limits |
| **Solver 2 (Groq)** | Fast analytical solver | `backend/graph/nodes/solver_nodes.py` | Configured but Misconfigured | Yes | Dispatches to Groq; gets 404; router cascades to Gemini | Groq default model `llama-3.3-70b-versatile` does not exist on key |
| **Solver 3 (OpenRouter)** | Diverse reasoning solver | `backend/graph/nodes/solver_nodes.py` | Configured but Unreachable | Yes | Dispatches to OpenRouter; fails; router cascades to Gemini | OpenRouter credits depleted |
| **Reflection Agent** | Detects hallucinations & contradictions | `backend/agents/reflection_agent.py` | Real / Active | Yes | Cross-examines 3 solver solutions; outputs structured JSON | Relies on Gemini; falls back to heuristic empty dict on failure |
| **Judge Agent** | Evaluates solutions and picks winner | `backend/agents/judge_agent.py` | Real / Active | Yes | LLM evaluation comparing clarity, correctness, rigor | Fallback picks first candidate on tie; exhibits 100% verbosity bias |
| **Citation Generator** | Injects grounding sources and page refs | `backend/graph/nodes/citation_node.py` | Real / Active | Yes | Deterministic regex/string matching against retrieved context | Bypassed when retrieved context is empty |
| **Document Ingestion** | Ingests PDF, DOCX, TXT, images | `backend/ingestion/` | Real / Active | Staged (via `/api/v1/upload`) | Upload storage and format validation active | OCR engines (Tesseract/EasyOCR) optional stubs if uninstalled |
| **Chunking Engine** | Recursive character & semantic split | `backend/retrieval/chunking.py` | Real / Active | Staged | Splits text into 500-char chunks with 50-char overlap | Functional for newly ingested docs |
| **Embedding Engine** | Dense vector representations | `backend/retrieval/embeddings.py` | Real / Active | Yes | Local `BAAI/bge-small-en-v1.5` model generates 384-d vectors | Fully functional, cached in `~/.cache/huggingface` |
| **FAISS Vector Store** | Dense similarity search | `backend/retrieval/vector_search.py` | Real / Active | Yes | Cosine similarity via `IndexFlatIP`; handles empty store safely | In-memory index empty until documents are ingested |
| **BM25 Search** | Sparse lexical keyword search | `backend/retrieval/bm25_search.py` | Real / Active | Yes | `rank_bm25.BM25Okapi` tokenizer | Fails query when DB table `document_chunks` does not exist |
| **RRF Fusion** | Merges dense and sparse ranks | `backend/retrieval/hybrid.py` | Real / Active | Yes | Formula: $RRF\_Score = \sum \frac{1}{60 + rank_i}$ | Fully tested, verified 100% recall on controlled tests |
| **Cohere Reranker** | Cross-encoder precision reranking | `backend/retrieval/reranker.py` | Staged (Disabled by Flag) | Yes (via PassThrough) | `PassThroughReranker` active by default; Cohere client staged | `cohere_rerank_enabled` defaults to `False` in settings |
| **PostgreSQL DB** | Persistent storage for docs & chunks | `backend/database/` | Real / Staged | Connected | SQLAlchemy engine connects to `localhost:5432/math_debate` | Tables `documents` and `document_chunks` not created |
| **RAGAS Evaluator** | Automated RAG & answer benchmarking | `backend/evaluation/ragas_evaluator.py` | Heuristic Fallback | Secondary path | Heuristic regex matching for faithfulness & relevance | `ragas` package uninstalled; uses fallback score generator |

---

## 3. Discrepancy & Gap Analysis

### 3.1 LangGraph Orchestration
- **Stated Architecture**: System relies on `langgraph.graph.StateGraph` and `langgraph.checkpoint` for compiled graph execution with conditional branches and human-in-the-loop state persistence.
- **Actual Runtime**: The `langgraph` package is omitted from the active virtual environment. `backend/graph/workflow.py` implements:
  ```python
  class _BuiltinStateGraph:
      def __init__(self):
          self.nodes = {}
          self.edges = []
          self.entry_point = None
      def add_node(self, name, fn): ...
      def add_edge(self, src, dst): ...
      def compile(self): return self
      def invoke(self, state):
          # Linear execution loop through edge sequence
  ```
- **Consequence**: Execution is purely linear and synchronous. Branching conditions (e.g., conditional debate re-round) are evaluated as single-pass state transformations.

### 3.2 Provider Availability & Multi-Model Diversity
- **Stated Architecture**: 3 distinct, independent LLM providers debate each problem:
  - Solver 1: Google Gemini 2.5 Flash
  - Solver 2: Groq LLaMA 3.3 70B
  - Solver 3: OpenRouter DeepSeek R1 Distill / Qwen 2.5 72B
- **Actual Runtime**:
  - Gemini is the **only functional provider**.
  - Groq requests fail with `HTTP 404: The model llama-3.3-70b-versatile does not exist or you do not have access to it`. The API key is valid, but the account only has access to models such as `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, etc.
  - OpenRouter requests fail due to zero balance.
  - Because `ProviderRouter` cascades to `GEMINI` on failure, **Solver 1, Solver 2, Solver 3, Reflection, and Judge all invoke Gemini**.
  - As a result, the debate suffers from **model homogeneity** (Gemini debating Gemini evaluated by Gemini) and rapidly exhausts the 20 request/day free-tier quota.

### 3.3 Database State & Retrieval Bypass
- **Stated Architecture**: User questions trigger hybrid retrieval against a knowledge base of mathematical theorems, formulas, and textbook excerpts stored in PostgreSQL and indexed in FAISS + BM25.
- **Actual Runtime**:
  - PostgreSQL is running and accepting connections, but database tables `documents` and `document_chunks` have not been created.
  - When `RetrievalService.retrieve()` executes:
    1. FAISS returns an empty list (`vector store is empty`).
    2. BM25 catches `UndefinedTable: relation "document_chunks" does not exist`.
    3. Retrieval returns 0 chunks in ~6ms.
    4. Context Manager formats an empty string.
    5. Solvers solve purely from parametric memory.
- **Controlled Retrieval Test**: In our controlled retrieval experiment (`audit/scripts/run_retrieval_experiment.py`) with a dedicated in-memory index of 10 math textbook chunks, the hybrid retrieval pipeline achieved **Recall@1 = 100%**, **Recall@3 = 100%**, and **MRR = 1.0000**. The retrieval logic is mathematically sound; the runtime defect is strictly the absence of migrated database tables.

### 3.4 Evaluation Subsystem (RAGAS)
- **Stated Architecture**: Quantitative evaluation using genuine RAGAS metrics (`faithfulness`, `answer_relevance`, `context_precision`, `context_recall`) via OpenAI or HuggingFace embeddings.
- **Actual Runtime**:
  - `ragas` package is not installed.
  - `backend/evaluation/ragas_evaluator.py` returns synthetic mock scores derived from simple keyword overlap and text length heuristics:
    ```python
    def _evaluate_heuristic(self, question, answer, contexts, ground_truth):
        # Heuristic word-overlap ratios
        return {
            "faithfulness": min(1.0, overlap_count / total_words),
            "answer_relevance": 0.85, ...
        }
    ```
- **Consequence**: Existing automated evaluations cannot be relied upon for academic or production quality measurement until genuine evaluation harnesses (such as our Phase 1 benchmark) are used.

