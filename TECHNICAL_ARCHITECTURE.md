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
Citation Generator Node (Source document attribution)
    ↓
Final Answer + RAG Citations
```

---

## 4. Provider Gateway & Routing Architecture

All cloud LLM and reranker calls are routed authoritatively through `ProviderRouter`:

- **Active Provider Adapters**:
  - `GeminiAdapter`: Default reasoning engine (`gemini-2.5-flash`)
  - `GroqAdapter`: High-speed inference (`llama-3.3-70b-versatile`)
  - `OpenRouterAdapter`: Diverse reasoning solver (`deepseek/deepseek-r1-distill-llama-70b`)
  - `CohereAdapter`: Reranking engine (`rerank-v3.5`)
- **Resilience Features**:
  - Automatic cross-provider fallback (`GEMINI -> GROQ -> OPENROUTER`)
  - Response normalization into standardized `ProviderResponse` dataclass
  - Latency, token usage, and error metrics tracked via `ProviderMetrics`

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
3. **Context Manager**:
   - Deduplicates chunks, filters below similarity threshold, and formats structured prompt context within configurable character/token budget (`max_context_length=4000`).

---

## 6. Evaluation & Benchmarking Subsystem

- **RAGAS Metric Evaluator** (`backend/evaluation/ragas_evaluator.py`):
  - **Faithfulness**: Measures grounding of generated answer in retrieved context.
  - **Answer Relevance**: Measures semantic alignment between user question and final answer.
  - **Context Precision**: Measures rank positioning of relevant context chunks.
  - **Context Recall**: Measures coverage of reference answer claims in context.
- **GSM8K Benchmark Harness** (`backend/evaluation/dataset.py`, `backend/evaluation/benchmark_runner.py`):
  - Curated 10-problem GSM8K dataset subset with reference answers.
  - Executes questions end-to-end through `MathDebateGraph`, capturing all intermediate solver states, reflection notes, and judge decisions.
  - Exports aggregated reports in JSON and CSV formats.
- **Evaluation REST Endpoints**:
  - `POST /api/evaluation/benchmark`: Triggers benchmark run over $N$ items.
  - `GET /api/evaluation/benchmark`: Returns cached or fresh benchmark metrics report.

---

## 7. Database Architecture

- **`documents`**: Tracks uploaded files, file hashes, MIME types, processing status, and OCR metadata.
- **`document_chunks`**: Stores chunk text, character boundaries, section headings, page numbers, and deterministic `vector_index` pointers mapping to FAISS.
- **`system_settings`**: Key-value runtime configuration persistence.