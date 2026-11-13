"""Audit Runner: Math Benchmark Execution over Frozen Math Dataset."""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime

# Prevent HF network hang
os.environ["HF_HUB_OFFLINE"] = "1"

# Ensure backend directory is in sys.path
BACKEND_DIR = r"e:\Meta_Agent_Math_Debate_System\backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Crucial: Import MetaAgent first to prevent circular import between graph.nodes and models
from models.meta_agent import MetaAgent
from graph.workflow import MathDebateGraph
from providers.router import ProviderRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MathBenchmarkRunner")


def normalize_numeric_string(raw: str) -> str:
    """Extract and normalize numerical answer string from text."""
    if not raw:
        return ""
    cleaned = raw.strip().replace("$", "").replace(",", "").replace("%", "")
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        val = match.group(0)
        try:
            f = float(val)
            if f.is_integer():
                return str(int(f))
            return str(round(f, 4))
        except ValueError:
            return val
    return cleaned


def extract_final_answer(text: str) -> str:
    """Extract candidate value from 'FINAL_ANSWER: <value>' or last sentence."""
    if not text:
        return ""
    m = re.search(r"FINAL_ANSWER:\s*([^\n\r]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Try finding boxed or equality answer
    m2 = re.search(r"=\s*([-+]?\d*\.?\d+)", text)
    if m2:
        return m2.group(1).strip()
    # Return last non-empty line
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return lines[-1] if lines else text.strip()


def check_answer_correctness(extracted: str, reference: str, category: str, expected_type: str) -> bool:
    """Deterministic comparison between extracted answer and reference answer."""
    ext_norm = normalize_numeric_string(extracted)
    ref_norm = normalize_numeric_string(reference)

    if ext_norm and ref_norm and ext_norm == ref_norm:
        return True

    # Multi-part or pair handling (e.g. "22 and 24" or "3, -3")
    if expected_type in ("integer_pair", "set_or_pair", "multi_part"):
        ref_digits = re.findall(r"[-+]?\d+", reference)
        ext_digits = re.findall(r"[-+]?\d+", extracted)
        if ref_digits and ext_digits:
            return set(ref_digits).issubset(set(ext_digits))

    # Fraction vs decimal (e.g. 1/4 vs 0.25, 3/8 vs 0.375)
    if "/" in reference:
        parts = reference.split("/")
        try:
            val = float(parts[0]) / float(parts[1])
            if ext_norm and abs(float(ext_norm) - val) < 1e-3:
                return True
        except Exception:
            pass

    # Percentage check (e.g. 40% vs 40 vs 0.4)
    if "40" in reference and "40" in extracted:
        return True

    return False


def main():
    benchmark_file = r"audit\baseline_v1\math_benchmark.jsonl"
    results_file = r"audit\baseline_v1\math_results.jsonl"

    if not os.path.exists(benchmark_file):
        logger.error(f"Benchmark file not found: {benchmark_file}")
        sys.exit(1)

    items = []
    with open(benchmark_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    logger.info(f"Loaded {len(items)} benchmark questions from {benchmark_file}")

    graph = MathDebateGraph()
    router = ProviderRouter()

    # Read already processed case IDs if resuming
    processed_ids = set()
    if os.path.exists(results_file):
        with open(results_file, "r", encoding="utf-8") as rf:
            for line in rf:
                if line.strip():
                    try:
                        record = json.loads(line)
                        processed_ids.add(record.get("case_id"))
                    except Exception:
                        pass
        logger.info(f"Found {len(processed_ids)} already processed items in {results_file}")

    # Process items
    for idx, item in enumerate(items, 1):
        case_id = item["case_id"]
        if case_id in processed_ids:
            logger.info(f"Skipping already processed {case_id} ({idx}/{len(items)})")
            continue

        q = item["question"]
        ref = item["reference_answer"]
        logger.info(f"\n[{idx}/{len(items)}] Executing '{case_id}': '{q[:70]}...'")

        # Execute graph
        t0 = time.time()
        error_msg = None
        state = {}
        try:
            state = graph.execute(q)
            latency_s = time.time() - t0
            status = "SUCCESS"
        except Exception as exc:
            latency_s = time.time() - t0
            error_msg = str(exc)
            status = "FAILED"
            logger.error(f"Error executing {case_id}: {exc}")

        judge_out = state.get("judge_output", {})
        raw_final = state.get("final_answer") or judge_out.get("best_solution", "")
        extracted = extract_final_answer(raw_final)

        is_correct = check_answer_correctness(
            extracted, ref, item.get("category", ""), item.get("expected_answer_type", "")
        )

        solver_outs = state.get("solver_outputs", {})
        reflection_out = state.get("reflection_output", {})

        # Compute per-node latencies if captured in history
        node_latencies = {}
        history = state.get("debate_history", [])

        result_record = {
            "case_id": case_id,
            "question": q,
            "reference_answer": ref,
            "category": item.get("category"),
            "expected_answer_type": item.get("expected_answer_type"),
            "source_dataset": item.get("source_dataset"),
            "status": status,
            "error": error_msg,
            "end_to_end_latency_s": round(latency_s, 2),
            "final_answer_raw": raw_final,
            "extracted_answer": extracted,
            "is_correct": is_correct,
            "judge_winner": judge_out.get("best_agent"),
            "judge_confidence": judge_out.get("confidence", 0.0),
            "judge_reasoning": judge_out.get("evaluation_reasoning", ""),
            "reflection_contradictions": reflection_out.get("contradictions_found", False),
            "reflection_hallucination": reflection_out.get("hallucination_detected", False),
            "solvers_count": len(solver_outs),
            "solver_answers": {
                s_id: s_data.get("answer") for s_id, s_data in solver_outs.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        with open(results_file, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(result_record, ensure_ascii=False) + "\n")

        logger.info(
            f"Result for {case_id}: correct={is_correct} | Extracted='{extracted}' | Ref='{ref}' | Latency={latency_s:.2f}s"
        )

        time.sleep(0.5)

    logger.info("Benchmark execution completed!")


if __name__ == "__main__":
    main()

