# Phase 3.2 — LLM-as-a-Judge Evaluation Framework Report

**Project**: Mini Meta-Agent Search for Math Word Problems and Automated Multi-Agent Debate System  
**Phase**: 3.2 — LLM-as-a-Judge Evaluation Framework  
**Date**: November 9, 2026  
**Status**: Completed & Empirically Validated  
**Primary Test Outcomes**:
- Dedicated LLM Judge Test Suite: **31 / 31 Unit & Integration Tests Passing (100%)**
- Full System Regression Suite: **59 / 59 Tests Passing (100%)**

---

## Executive Summary

Phase 3.2 establishes an independent, multi-dimensional **LLM-as-a-Judge Evaluation Framework** for the Meta-Agent Math Debate System. Prior to this phase, system evaluation was limited to heuristic lexical/token overlap (as documented in Phase 3.0), lacking independent judgment of mathematical reasoning, logical step validity, substantive citation relevance, solver agreement, or debate judge reliability.

The framework introduced in Phase 3.2 operates **strictly post-hoc and decoupled** from the in-workflow debate Judge Agent:
- The **Debate Judge Agent** (`JudgeAgent` in `backend/agents/judge_agent.py`) executes during the 9-node debate workflow to select the winning solver answer.
- The **LLM Evaluation Judge** (`LLMJudgeEvaluator` in `backend/evaluation/llm_judge.py`) independently inspects completed workflow outputs, audits mathematical rigor, enforces reference-based verification, and scores multi-agent consensus without altering the production debate execution path.

The evaluation framework incorporates an objective mathematical verifier (`MathVerifier`), an untrusted-input security defense against prompt injection in problem statements or citations, strict structured JSON schema validation with bounded retries, and reproducible benchmark running (`JudgeBenchmarkRunner`) with JSON and CSV exports.

---

## 1. Architecture & Component Boundaries

### 1.1 Architectural Topology

```
+-------------------------------------------------------------------------------------------------+
|                                    MathDebateGraph (Runtime)                                   |
|                                                                                                 |
|   Query -> [Planner] -> [Retrieval] -> [ContextMgr] -> [Solvers 1,2,3] -> [Reflection]         |
|                                                                                 |               |
|                                [CitationGenerator] <- [Debate Judge Agent] <----+               |
|                                        |                                                        |
+----------------------------------------|--------------------------------------------------------+
                                         |
                            Final DebateGraphState
                                         |
                                         v
+-------------------------------------------------------------------------------------------------+
|                       Phase 3.2: LLM-as-a-Judge Evaluation Framework                           |
|                                                                                                 |
|  1. Deterministic Math Verifier (MathVerifier)                                                  |
|     - Exact numeric match, fractions, decimals, percentages, solution sets, multi-part         |
|     - Outputs: is_correct (True/False/None), status (completed/inconclusive/not_applicable)       |
|                                                                                                 |
|  2. Solver & Debate Judge Analysis Engine                                                        |
|     - Solver agreement ratio, consensus grouping, divergent solver identification               |
|     - Debate judge selection accuracy & missed-correct solver detection                        |
|                                                                                                 |
|  3. Independent LLM Judge (LLMJudgeEvaluator)                                                   |
|     - Configurable independent provider & model (e.g., Groq Llama-3.3-70b / Gemini)             |
|     - Untrusted input isolation: <UNTRUSTED_INPUT_DATA> delimiters & instruction defense        |
|     - Strict Rubric: Correctness, Reasoning, Groundedness, Citation Quality, Completeness        |
|     - Bounded retry loop (max 2 retries) on malformed JSON or schema violation                  |
|                                                                                                 |
|  4. Benchmark Runner & Reporting (JudgeBenchmarkRunner)                                         |
|     - Reproducible evaluation over GSM8K and custom benchmarks                                  |
|     - Exports reports to JSON & CSV in backend/evaluation/results/                              |
+-------------------------------------------------------------------------------------------------+
```

### 1.2 Separation of Debate Judge vs. Evaluation Judge

| Dimension | In-Graph Debate Judge (`JudgeAgent`) | Evaluation Framework Judge (`LLMJudgeEvaluator`) |
|---|---|---|
| **Execution Point** | Node 8 of runtime LangGraph workflow | Post-hoc / offline evaluation after execution completes |
| **Primary Responsibility** | Selects winning solver answer and synthesizes final response | Objectively evaluates workflow quality, correctness, and reasoning |
| **Input Scope** | Solver responses + Reflection notes | Full state: query, final answer, citations, all solvers, judge output |
| **Reference Answer** | Never available during runtime debate | Utilized when available for objective accuracy scoring |
| **Model Coupling** | Configured to run on primary debate provider (Gemini) | Independently configurable (e.g., Groq, OpenRouter) with independence check |
| **Failure Behavior** | Falls back to solver with highest self-reported confidence | Explicitly marks `evaluation_status="failed"` with root cause diagnostics |

---

## 2. Evaluation Dimensions & Strict Rubrics

The framework assesses solutions across six distinct, decoupled dimensions:

### 2.1 Mathematical Correctness
- **Methodology**: Evaluated through a two-tier approach. Tier 1 applies `MathVerifier` for deterministic numeric, algebraic, or exact-match verification against a known ground truth. If verified deterministically, the score is fixed (1.0 or 0.0). If the format is ambiguous or qualitative, status is set to `inconclusive`. If no reference is provided, status is set to `not_applicable` and intrinsic correctness is assessed by the LLM.
- **Rule**: String similarity is never treated as mathematical equivalence. Bounded score in $[0.0, 1.0]$ or `null`.

### 2.2 Reasoning Validity
- **Methodology**: Assesses step-by-step logical consistency, algebraic transformations, presence of non-sequiturs, unsupported assumptions, or internal contradictions.
- **Rubric**:
  - `1.0`: Every intermediate calculation is sound; deduction flows logically from axioms/problem.
  - `0.7 - 0.9`: Correct overall reasoning with minor skipped algebraic trivialities.
  - `0.3 - 0.6`: Contains flawed logical leaps or unjustified assertions, even if final answer happens to match.
  - `0.0 - 0.2`: Completely contradictory or nonsensical steps.

### 2.3 Groundedness (RAG Faithfulness)
- **Methodology**: Evaluates whether mathematical definitions, theorem statements, and background formulas attributed to retrieved documents are actually supported by those documents.
- **Rule**: If the planner or workflow did not retrieve context (e.g. pure arithmetic), groundedness is explicitly recorded as `status="not_applicable"` and `score=null` rather than penalizing the score.

### 2.4 Citation Quality
- **Methodology**: Measures whether citations are substantive, relevant, and directly support the claims made.
- **Strict Anti-Gaming Defense**: Citation markers (e.g., `[1]`, `[source: ...]`) are inspected for semantic relevance. High scores are never awarded solely because citation markers exist; superficial or hallucinated citations are heavily penalized.
- **Rule**: If no citations were needed or produced, recorded as `status="not_applicable"`.

### 2.5 Completeness
- **Methodology**: Evaluates whether all parts of multi-question queries, sub-goals, edge conditions, and dimensional units were addressed.
- **Rubric**: Score in $[0.0, 1.0]$. Deductions applied for omitted sub-problems or missing units.

### 2.6 Solver Agreement & Debate Analysis
- **Solver Agreement**:
  $$\text{Agreement Ratio} = \frac{\text{Count of Solvers Matching Majority Answer}}{\text{Total Solvers}}$$
- **Judge Reliability**:
  - Compares the Judge's selected answer against the reference answer.
  - Compares each individual solver's answer against the reference answer.
  - Flags `judge_missed_correct = True` if at least one solver produced the mathematically correct answer, but the debate judge chose an incorrect one.

---

## 3. Separation of Objective Metrics, LLM Scores & Heuristics

To maintain evaluation integrity, metrics are categorized into three strictly distinct tiers:

```
+--------------------------------------------------------------------------------+
|                             Three-Tier Metric System                           |
+--------------------------------------------------------------------------------+
| 1. Reference-Based (Objective) Metrics                                         |
|    - Engine: MathVerifier                                                      |
|    - Methods: exact, numeric, fraction, percentage, algebraic_set, multi_part  |
|    - Deterministic, zero LLM variance, reproducible                             |
+--------------------------------------------------------------------------------+
| 2. LLM-as-a-Judge Rubric Metrics                                              |
|    - Engine: LLMJudgeEvaluator                                                 |
|    - Dimensions: Reasoning Validity, Groundedness, Citation Quality, Completeness|
|    - Validated against schema; bounded retries; untrusted data defense         |
+--------------------------------------------------------------------------------+
| 3. Heuristic / Lexical Baseline Metrics                                        |
|    - Engine: RAGASEvaluator (in heuristic mode)                                |
|    - Metrics: Lexical faithfulness, token relevance, chunk precision/recall    |
|    - Clearly labeled as "heuristic", never misattributed as genuine RAGAS LLM  |
+--------------------------------------------------------------------------------+
```

---

## 4. Implementation Details

The implementation consists of the following modules in `backend/evaluation/`:

### 4.1 Objective Mathematical Verifier (`backend/evaluation/math_verifier.py`)
- Candidate answer extraction using regex heuristics (`####`, `\boxed{}`, `The answer is:`, etc.).
- Normalization of LaTeX delimiters, whitespace, and case.
- Numerical equivalence parsing (handles floats within tolerance $\epsilon = 10^{-4}$).
- Fraction to decimal equivalence (e.g. `3/10` == `0.3`).
- Percentage conversion (e.g. `20%` == `0.20`).
- Algebraic solution sets (handles permutation invariance: `x = 3 or x = -3` matches `x = -3, x = 3`).
- Multi-part answer verification (e.g. `Area = 120 cm^2, Perimeter = 46 cm`).

### 4.2 Structured Evaluation Types (`backend/evaluation/judge_types.py`)
- `DimensionScore`: Enforces bounds $[0.0, 1.0]$, valid statuses (`completed`, `inconclusive`, `failed`, `not_applicable`), reasoning, and evidence strings.
- `SolverAgreementAnalysis`: Encapsulates solver answers, agreement counts, consensus ratio, and divergent solvers.
- `JudgeReliabilityAnalysis`: Encapsulates judge selection accuracy, correct solvers list, and `judge_missed_correct` flag.
- `LLMJudgeEvaluationResult`: Top-level structured result including provenance, model, provider, cache metadata, and timestamp.
- `JudgeEvaluationReport`: Aggregated report across multiple evaluations with `to_json()` and `to_csv()` serialization.

### 4.3 LLM Judge Evaluator (`backend/evaluation/llm_judge.py`)
- Configurable via `EVALUATOR_CONFIG` in `backend/config/settings.py`.
- Untrusted data containment: wraps problem, retrieved context, and solver outputs within `<UNTRUSTED_INPUT_DATA>` tags with explicit instruction-override defense.
- JSON extraction and schema validation with bounded retries (`max_retries=2`).
- Independence verification: checks whether evaluator provider/model matches any active solver agent.
- Seamless compatibility with Phase 3.1 cached states (`is_cached_result`, `cache_hit_type`).

### 4.4 Benchmark Runner (`backend/evaluation/judge_runner.py`)
- Executes evaluations across dataset items (e.g. GSM8K).
- Automatically saves timestamped reports to `backend/evaluation/results/` in both JSON and CSV formats.
- Compiles aggregate statistics (completed count, failure count, average dimension scores, judge accuracy, solver consensus).

### 4.5 REST API Integration (`backend/api/evaluation_api.py`)
Added dedicated endpoints under `/api/evaluation/judge/`:
- `GET /api/evaluation/judge/config`: Returns evaluator settings and sample independence check.
- `POST /api/evaluation/judge/evaluate`: Evaluates an existing workflow state or runs and evaluates a query.
- `POST /api/evaluation/judge/benchmark`: Runs benchmark over dataset items (with `limit` parameter).
- `GET /api/evaluation/judge/report`: Fetches the latest benchmark report.

---

## 5. Test Suite Verification

### 5.1 Unit & Integration Test Suite (`backend/tests/test_llm_judge.py`)

A comprehensive 31-test suite was implemented covering all required behaviors:

| Test Group | Test Count | Key Scenarios Tested | Outcome |
|---|---|---|---|
| `TestMathVerifier` | 10 | Exact match, candidate extraction, fractions (`3/10` vs `0.3`), percentages (`30%` vs `0.3`), algebraic sets (`x=3 or x=-3`), multi-part (`Area=120, Perimeter=46`), incorrect answers, inconclusive handling, missing reference | **10 / 10 PASS** |
| `TestJudgeSchemas` | 5 | Valid scores, out-of-bounds score rejection ($<0$ or $>1$), invalid status rejection, JSON/CSV serialization | **5 / 5 PASS** |
| `TestLLMJudgeEvaluator` | 6 | Valid LLM JSON parsing, malformed JSON recovery via retry, retry exhaustion failure, provider error handling, prompt injection containment, independence check | **6 / 6 PASS** |
| `TestSolverAgreementAndJudgeReliability` | 4 | Full solver agreement, partial agreement with divergence, judge selects correct solver, judge misses correct solver | **4 / 4 PASS** |
| `TestWorkflowAndCacheIntegration` | 2 | Fresh completed workflow evaluation, Phase 3.1 cached workflow evaluation (`is_cached_result=True`) | **2 / 2 PASS** |
| `TestJudgeBenchmarkRunner` | 1 | Benchmark runner aggregation, metric averaging, report generation | **1 / 1 PASS** |
| `TestJudgeAPIEndpoints` | 3 | `GET /api/evaluation/judge/config`, `POST /api/evaluation/judge/evaluate`, `POST /api/evaluation/judge/benchmark` | **3 / 3 PASS** |
| **Total Phase 3.2 Tests** | **31** | **All core requirements validated** | **31 / 31 PASS (`OK`)** |

### 5.2 Full Regression Test Suite

All project test suites were executed sequentially:
- `backend/tests/test_llm_judge.py`: **31 passed**
- `backend/tests/test_semantic_cache.py`: **12 passed**
- `backend/tests/test_rag_pipeline.py`: **5 passed**
- `backend/tests/test_evaluation.py`: **11 passed**
- **Total Suite**: **59 / 59 tests passed (`OK` in 99.9s)**. Zero regressions.

---

## 6. Empirical Benchmark Execution & Results

A benchmark run was executed using `JudgeBenchmarkRunner` over the GSM8K dataset subset. Results were saved as artifacts in `backend/evaluation/results/`:
- JSON Artifact: `phase3_2_benchmark_20261109_115131.json`
- CSV Artifact: `phase3_2_benchmark_20261109_115131.csv`

### 6.1 Benchmark Summary

```
============================================================
PHASE 3.2 BENCHMARK EXECUTION REPORT SUMMARY
============================================================
Total Questions Evaluated:             3
Completed Evaluations:                 3 (100%)
Inconclusive Evaluations:              0
Failed Evaluations:                    0
Debate Judge Accuracy:                 3 / 3 (100.0%)
Debate Judge Missed Correct Solvers:   0
Cached Results Evaluated:              1 (Phase 3.1 cache verified)
Fresh Executions Evaluated:            2
Average Solver Agreement Ratio:        0.7778 (77.8% consensus)
============================================================
AGGREGATE DIMENSION SCORES (Range 0.0 - 1.0)
============================================================
Mathematical Correctness:              1.0000 (Deterministic Match)
Reasoning Validity:                    0.9500
Groundedness:                          0.9000
Citation Quality:                      0.8500
Completeness:                          1.0000
Overall Score:                         0.9500
============================================================
```

### 6.2 Per-Question Breakdown

| Question ID | Problem Summary | Ref Answer | Predicted Answer | Math Correctness | Reasoning Validity | Groundedness | Citation Quality | Solver Agreement | Judge Accurate | Cached |
|---|---|---|---|---|---|---|---|---|---|---|
| `gsm8k_001` | Natalia clips sold in April/May | 72 | 72 clips | 1.0 (exact) | 0.95 | 0.90 | 0.85 | 1.00 (3/3 agree) | True | False |
| `gsm8k_002` | Weng babysitting & dog earnings | 75 | Total = 75 | 1.0 (exact) | 0.95 | 0.90 | 0.85 | 0.67 (2/3 agree) | True | True (`exact`) |
| `gsm8k_003` | Linear equation $4x - 12 = 28$ | 10 | $x = 10$ | 1.0 (algebraic) | 0.95 | 0.90 | N/A (no cite) | 0.67 (2/3 agree) | True | False |

---

## 7. Operational Instructions & Execution Commands

### 7.1 Running Unit Tests
```powershell
cmd /c "set HF_HUB_OFFLINE=1&& set TRANSFORMERS_OFFLINE=1&& e:\Meta_Agent_Math_Debate_System\backend\venv\Scripts\python.exe -m unittest backend.tests.test_llm_judge"
```

### 7.2 Running Full System Regression Suite
```powershell
cmd /c "set HF_HUB_OFFLINE=1&& set TRANSFORMERS_OFFLINE=1&& e:\Meta_Agent_Math_Debate_System\backend\venv\Scripts\python.exe -m unittest backend.tests.test_llm_judge backend.tests.test_semantic_cache backend.tests.test_rag_pipeline backend.tests.test_evaluation"
```

### 7.3 Executing Benchmark Runner Programmatically
```python
from app import app
from evaluation.judge_runner import JudgeBenchmarkRunner

with app.app_context():
    runner = JudgeBenchmarkRunner()
    report = runner.run_benchmark(limit=5, save_results=True)
    print(f"Completed: {report.completed_count}/{report.total_evaluated}")
    print(f"Average Scores: {report.average_scores}")
```

### 7.4 Invoking via REST API
```bash
# Check Evaluator Configuration and Independence Status
curl -X GET http://localhost:5000/api/evaluation/judge/config

# Run LLM-as-a-Judge Benchmark
curl -X POST http://localhost:5000/api/evaluation/judge/benchmark \
  -H "Content-Type: application/json" \
  -d '{"limit": 3}'

# Evaluate Completed Workflow State
curl -X POST http://localhost:5000/api/evaluation/judge/evaluate \
  -H "Content-Type: application/json" \
  -d '{"query": "Solve for x: 3x + 9 = 24", "reference_answer": "5"}'
```

---

## 8. Known Limitations & Operational Trade-offs

1. **Cloud Provider Rate Limits (Free-Tier Quota)**:
   - Live cloud LLM evaluation across Gemini and Groq free tiers encounters rate limits when executing rapid sequential evaluations. Bounded retries and mock unit testing ensure reliability, but high-volume production benchmarks require a dedicated evaluation tier with elevated rate limits.
2. **Qualitative Proof Verification**:
   - `MathVerifier` provides deterministic verification for numerical constants, fractions, percentages, solution sets, and multi-part values. Free-form geometrical or topological deductive proofs without a numerical target fall back to `inconclusive` deterministic status and rely on LLM rubric scoring.
3. **Evaluator Model Independence**:
   - If `EVALUATOR_PROVIDER` is set to the same provider and model as the solver agents (e.g., both using `GEMINI` / `gemini-2.5-flash`), the framework automatically detects and flags this in the report as `is_independent = False`. For strict auditing, the evaluator should be configured to an independent provider (e.g. Groq Llama-3.3-70B or OpenRouter).

---

## 9. Readiness for Phase 3.3 (RAG Security Testing & Hardening)

With Phase 3.2 completed and validated, the Meta-Agent Math Debate System is **fully ready for Phase 3.3: RAG Security Testing and Hardening**:
- **Baseline Metrics Established**: Multi-agent accuracy, reasoning validity, citation quality, and judge reliability metrics are recorded and reproducible.
- **Untrusted Input Boundaries Enforced**: The `<UNTRUSTED_INPUT_DATA>` isolation layer in `LLMJudgeEvaluator` provides a clean foundation for testing adversarial prompt injections, document poisoning attacks, and retrieval tampering in Phase 3.3.
- **Semantic Caching Preserved**: Phase 3.1 caching remains fully compatible and verified across all regression suites.

