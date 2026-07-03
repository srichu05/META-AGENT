# Technical Summary – Meta‑Agent Math Debate System

## Project Structure (non‑test files)

```
Meta_Agent_Math_Debate_System/
├─ backend/
│  ├─ app.py                # Flask API entry point, routes, CORS, init
│  ├─ config.py             # Provider configs (Gemini, Cohere, HuggingFace, etc.)
│  ├─ main.py               # Shortcut runner (calls initialize_app & app.run)
│  ├─ .env                  # Environment variables (API keys, secrets)
│  ├─ requirements-backend.txt
│  ├─ models/
│  │   └─ meta_agent.py      # Core MetaAgent class – orchestrates LLM providers,
│  │                         # vector‑store RAG, debate logic, evaluation
│  ├─ utils/
│  │   ├─ __init__.py
│  │   ├─ api_client.py      # Thin wrapper around selected LLM APIs (Groq, Cohere,
│  │   │                     # Gemini, HuggingFace). Provides `get_completion` and
│  │   │                     # `get_embeddings`.
│  │   ├─ data_processor.py  # Handles corpus loading, validation, sample‑problem
│  │   │                     # retrieval, and persistence on disk.
│  │   ├─ logger.py          # Centralised logger configuration used by all modules.
│  │   └─ knowledge_base_loader.py (optional loader for external knowledge).
│  └─ rag/                 # Vector‑store implementation (FAISS‑like) used by
│                           # MetaAgent for retrieval‑augmented generation.
│
├─ frontend/
│  ├─ index.html            # Static UI – tabs for Solve, Debate, Analyse, Stats.
│  ├─ script.js             # Front‑end controller class `MathDebateSystem`.
│  │   • Sends HTTP requests to backend (`/api/solve`, `/api/debate`, …).
│  │   • Receives raw LLM answer, runs `sanitizeAnswer` to strip markup
│  │   • Formats each line via `formatSolutionText` → separate `<div>` per line.
│  └─ style.css             # Visual theme (dark‑mode, glass‑morphism, animations).
│
└─ requirements-frontend.txt
```

## How the Pieces Connect

### 1. Frontend → Backend Communication
* **`script.js`** creates a `MathDebateSystem` instance. All UI actions (solve, debate, analyse) call `makeRequest(endpoint, method, data)` which uses **`fetch`** against the Flask API (`http://127.0.0.1:5000/api/...`).
* The response JSON is passed through `sanitizeAnswer` (removes `[*]`, `="number">`, HTML entities, markdown artifacts) and then rendered with `formatSolutionText`, which now **splits on `\n`** and wraps each line in a `<div class="solution-line">`. This gives the line‑by‑line view the user requested.

### 2. Flask API Core (`app.py`)
* Initializes **CORS**, logger, and loads environment variables.
* Global objects:
  * `meta_agent : Optional[MetaAgent]`
  * `data_processor : Optional[DataProcessor]`
  * `last_evaluation` – snapshot stored for the Evaluation tab.
* Routes:
  * `POST /api/solve` → calls `meta_agent.solve_problem(problem)`.
  * `POST /api/debate` → `meta_agent.run_debate(problem, rounds)`.
  * `POST /api/analyze` → uses `meta_agent.retriever_agent` for pattern detection.
  * `GET /api/problems`, `GET /api/stats`, `GET /api/evaluation/last`, `POST /api/upload_corpus` etc.
* Each route builds an **evaluation snapshot** via `_build_evaluation` and stores it for the UI.

### 3. MetaAgent (`models/meta_agent.py`)
* Central orchestrator:
  * Holds references to **LLM providers** via `api_client` (Groq, Cohere, Gemini, HuggingFace).
  * Contains a **vector‑store** (`self.vector_store`) for RAG; populated by `data_processor` and the upload‑corpus endpoint.
  * Implements:
    * `solve_problem(problem)` – selects a provider (configurable order), optionally retrieves RAG context, calls `api_client.get_completion`, parses the answer.
    * `run_debate(problem, rounds)` – creates multiple solver instances, gathers their outputs, decides a winner, returns a structured debate timeline.
    * `analyze_problem(problem)` – uses the retriever to extract patterns/hints.
    * `get_stats()` – aggregates vector‑store stats, agent counts, etc.
* The **orchestration flow** is:
  1. Receive request from Flask.
  2. Optionally query vector‑store for similar problems (RAG).
  3. Call `api_client` with a **prompt template** that includes any retrieved context.
  4. Return JSON with `solution`, `answer`, `confidence`, `total_time`, `api_used`, and optional `rag_usage_stats`.

### 4. API Client (`utils/api_client.py`)
* Reads `SYSTEM_CONFIG` from `config.py` to know which providers are available and their keys.
* Provides:
  * `get_completion(model, prompt)` – abstracts HTTP calls to the chosen provider.
  * `get_embeddings(text)` – used when indexing a new corpus (upload endpoint).
* The client is **stateless**; the MetaAgent decides which model (e.g., Gemini‑flash, Groq‑mixtral) to call.

### 5. Data Processor (`utils/data_processor.py`)
* Loads the **corpus JSON file** (`data/problems.json` or similar) into memory.
* Offers helpers:
  * `get_sample_problems()` – used by API `GET /api/problems`.
  * `overwrite_problems_file(problems)` – replaces the stored corpus after upload.
  * Validation of problem structure (ensuring `problem`, `solution`, `answer`).
* The upload‑corpus endpoint (`/api/upload_corpus`) uses this class to:
  1. Parse the uploaded JSON/JSONL.
  2. Standardise fields.
  3. Generate embeddings via `api_client.get_embeddings`.
  4. Store embeddings in the **vector store** (`meta_agent.vector_store`).

### 6. Logger (`utils/logger.py`)
* Central `setup_logger(name)` returns a configured `logging.Logger` with a stream handler and a consistent format. All modules import this logger for unified diagnostics.

### 7. Vector Store (inside `backend/rag/` – not shown in the file list)
* Provides `add_math_problems(problems, embeddings)`, `clear()`, `search(query)`, and stores metadata about usage counts (`rag_usage_count`, `rag_similarity_scores`).
* Used by MetaAgent for **RAG‑enhanced solving** and by the upload‑corpus flow to re‑index.

### 8. Frontend Rendering Details (`script.js`)
* **Sanitizer** (`sanitizeAnswer`) removes all leftover markup (`[\*]`, `="number">`, HTML tags, markdown). It now keeps newline characters, then collapses only spaces/tabs.
* **Formatter** (`formatSolutionText`) splits the clean text on `\n`, highlights numbers (`<span class="number">`), operators (`<span class="operator">`), and step markers (`<strong class="step-marker">`). Each line becomes `<div class="solution-line">…</div>` – the UI now displays a vertical list.
* UI components (tabs, toasts, loading overlay) are wired to backend calls, and the evaluation tab reads `last_evaluation` from `/api/evaluation/last`.

## End‑to‑End Flow (Solve Example)
1. **User types a problem** → clicks *Solve* → `solveProblem()` in `script.js`.
2. `makeRequest('/solve', 'POST', {problem})` → **POST** to Flask `/api/solve`.
3. Flask `solve_problem()` extracts JSON, records RAG baseline, calls `meta_agent.solve_problem()`.
4. `MetaAgent.solve_problem()`:
   * Optionally fetches similar problems from the vector store.
   * Builds a prompt (base + retrieved context).
   * Calls `api_client.get_completion()` (e.g., Gemini‑flash).
   * Parses model output into `solution`, `answer`, `confidence`.
5. Result JSON is returned to the frontend.
6. Frontend runs `sanitizeAnswer` → `formatSolutionText` → inserts HTML into `#solution-text`.
7. UI shows each logical step on its own line, with coloured numbers/operators.

## Orchestration Summary
* **MetaAgent** is the brain – it decides *which* LLM to call, *when* to augment with RAG, and *how* to aggregate multiple agents for debate.
* **API Client** abstracts provider‑specific HTTP details, enabling easy swapping of models (e.g., switch from Cohere to Gemini by editing `config.py`).
* **Data Processor** and **Vector Store** supply the *knowledge corpus* that the user can upload at runtime. The corpus is indexed on‑the‑fly and used for every subsequent solve/debate.
* **Flask app** exposes a clean JSON API; the **frontend** is a thin wrapper that only concerns itself with UI/UX and sanitising the raw LLM text.

---
*This summary is deliberately self‑contained: any downstream AI can ingest the markdown above and instantly understand the file responsibilities, their inter‑dependencies, and the overall execution pipeline of the Meta‑Agent Math Debate System.*
