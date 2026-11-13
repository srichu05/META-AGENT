# Meta-Agent Baseline Audit & Benchmarking Suite (Phase 1)

**Version:** 1.0.0 (Baseline Frozen)  
**Target Commit:** `85c9af20c0958ef41e70f54002f494b1d1481765`  
**Execution Environment:** Windows 10 (10.0.22621), Python 3.11.9 64-bit  
**Scope:** Phase 1 Baseline Audit, Performance Profiling, and Security Hardening Assessment  

---

## 1. Overview & Objective

This directory contains the frozen, reproducible baseline evaluation for the **Meta-Agent Math Debate System** prior to the implementation of:
1. **Semantic Caching Layer** (for latency and LLM cost reduction)
2. **LLM-as-a-Judge Evaluation Framework** (for automated grading and bias mitigation)
3. **RAG Security & Defense Hardening** (for injection, poisoning, and data access prevention)

The primary purpose is to establish an immutable, quantitative benchmark against which all future architectural improvements, latency optimizations, and regressions will be measured.

---

## 2. Directory Structure & Inventory

```
audit/
├── baseline_v1/
│   ├── README.md                     # This reproducibility protocol and guide
│   ├── baseline_manifest.json        # Machine-readable environment and system configuration
│   ├── architecture_audit.md         # Full component inventory & runtime discrepancy analysis
│   ├── math_benchmark.jsonl          # Frozen 20-problem benchmark (GSM8K + verified samples)
│   ├── math_results.jsonl            # Execution outputs, answers, judge decisions, and latencies
│   ├── retrieval_results.jsonl       # Controlled hybrid retrieval metrics (Recall@k, MRR, latency)
│   ├── judge_results.jsonl           # Judge reliability, position sensitivity, and verbosity probes
│   ├── performance_results.jsonl     # Latency percentiles, token usage, and cost estimates
│   ├── cache_query_pairs.jsonl       # 25 semantic cache query pairs with BGE cosine similarities
│   ├── security_test_cases.jsonl     # 30 synthetic security test cases across 10 attack classes
│   ├── security_results.jsonl        # Security evaluation results, pass rates, and vulnerability log
│   ├── metrics_summary.json          # Consolidated system metrics across all dimensions
│   └── baseline_report.md            # Final 12-section comprehensive engineering baseline report
└── scripts/
    ├── generate_benchmark.py         # Generates math_benchmark.jsonl with SHA-256 validation
    ├── generate_cache_pairs.py       # Computes BGE embeddings & cosine similarities for cache pairs
    ├── run_retrieval_experiment.py   # Controlled evaluation of BM25, FAISS, RRF, and Cohere
    ├── run_judge_probes.py           # Position bias and verbosity bias probe suite
    ├── run_math_benchmark.py         # End-to-end LangGraph debate runner over benchmark dataset
    ├── run_security_suite.py         # Automated execution of 30 security attack vectors
    └── compile_metrics.py            # Aggregates raw outputs into metrics_summary.json & manifest
```

---

## 3. Reproducibility Protocol

All experiments are designed to run deterministically and safely without modifying production or backend source code.

### 3.1 Prerequisites & Environment Setup
- Python 3.11+ in `backend/venv`
- HuggingFace cache pre-populated with `BAAI/bge-small-en-v1.5`
- Environment variables: `HF_HUB_OFFLINE=1` (to prevent external huggingface network timeouts on Windows)
- Valid API keys in `.env` (Gemini, Groq, OpenRouter, Cohere)

### 3.2 Command-Line Reproduction Guide

Execute all commands from the repository root: `e:\Meta_Agent_Math_Debate_System`:

#### Step 1: Regenerate Benchmark Dataset
```powershell
backend\venv\Scripts\python.exe audit\scripts\generate_benchmark.py
```
*Expected Output:* `audit/baseline_v1/math_benchmark.jsonl` (20 problems, SHA-256: `4f14bbd8021b3742ce43f33db8b2e215384845f7ad7c6238cb28fff1048df0f7`).

#### Step 2: Run Controlled Retrieval Experiment
```powershell
backend\venv\Scripts\python.exe audit\scripts\run_retrieval_experiment.py
```
*Expected Output:* `audit/baseline_v1/retrieval_results.jsonl` (10 queries evaluated across BM25, FAISS IndexFlatIP, RRF fusion, and Cohere).

#### Step 3: Run Semantic Caching Similarity Profiler
```powershell
backend\venv\Scripts\python.exe audit\scripts\generate_cache_pairs.py
```
*Expected Output:* `audit/baseline_v1/cache_query_pairs.jsonl` (25 query pairs with exact BGE dense embeddings and cosine similarity values).

#### Step 4: Run Judge Position & Verbosity Bias Probes
```powershell
backend\venv\Scripts\python.exe audit\scripts\run_judge_probes.py
```
*Expected Output:* `audit/baseline_v1/judge_results.jsonl` (5 position-swap pairs and 3 length/verbosity pairs).

#### Step 5: Execute Math Benchmark Suite
```powershell
backend\venv\Scripts\python.exe audit\scripts\run_math_benchmark.py
```
*Expected Output:* `audit/baseline_v1/math_results.jsonl` (Full 9-node debate execution for all 20 benchmark questions).

#### Step 6: Execute Security Attack Suite
```powershell
backend\venv\Scripts\python.exe audit\scripts\run_security_suite.py
```
*Expected Output:* `audit/baseline_v1/security_results.jsonl` (Evaluation of 30 attack payloads against graph and storage layers).

#### Step 7: Compile Metrics Summary & Manifest
```powershell
backend\venv\Scripts\python.exe audit\scripts\compile_metrics.py
```
*Expected Output:* `metrics_summary.json`, `performance_results.jsonl`, and `baseline_manifest.json`.

---

## 4. Benchmark Dataset Summary

The 20-problem benchmark consists of:
- **10 Verified GSM8K Problems** (`gsm8k_001` through `gsm8k_010`): Multistep arithmetic, rate-time-distance, money, percentages, and proportional reasoning.
- **10 Verified Advanced Problems** (`sample_001` through `sample_010`): Linear algebra, quadratic equations, geometry (right triangle, circle), fractions, and logic.

Every question has an unambiguous, closed-form reference answer verified by symbolic math.

---

## 5. Protocol for Future Phases

When implementing subsequent phases:
1. **Semantic Caching**: Test cache hit rates against `cache_query_pairs.jsonl`. Verify that non-equivalent math problems (`pair_009` through `pair_017`) achieve **0% false positive cache hits**.
2. **LLM-as-a-Judge**: Run `run_judge_probes.py` after prompt or judge model modifications. The target is **0% position flips** and **<20% verbosity bias**.
3. **RAG Security**: Run `run_security_suite.py`. All 30 test cases must achieve a **100% pass rate** before production deployment.
4. **No In-Place Overwrites**: Never overwrite the `audit/baseline_v1/` artifacts. Create `audit/phase2_caching/`, `audit/phase3_judge/`, and `audit/phase4_security/` for comparative reporting.

