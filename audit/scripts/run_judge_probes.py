"""Audit Script: Controlled Judge Agent Reliability and Bias Probes (Phase F).

Conducts controlled experiments against the active JudgeAgent:
1. Position Sensitivity Probe (Swapping candidate order A/B vs B/A)
2. Verbosity Sensitivity Probe (Concise correct vs Verbose correct equivalent answers)
3. Fallback and Malformed Handling Probe
Does NOT modify application source code.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

# Prevent HF network hang
os.environ["HF_HUB_OFFLINE"] = "1"

BACKEND_DIR = r"e:\Meta_Agent_Math_Debate_System\backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from models.meta_agent import MetaAgent
from agents.judge_agent import JudgeAgent
from providers.router import ProviderRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("JudgeProbeAudit")


def main():
    results_file = r"audit\baseline_v1\judge_results.jsonl"
    judge = JudgeAgent()

    logger.info("Initializing JudgeAgent probes...")

    # Probe 1: Position Sensitivity Test Cases
    # Same two mathematical solutions presented in opposite orders
    position_cases = [
        {
            "probe_id": "pos_probe_001",
            "problem": "Solve for x in: 4x - 12 = 28.",
            "sol_a": {
                "solution": "Add 12 to both sides: 4x = 40. Divide by 4: x = 10.\nFINAL_ANSWER: 10",
                "answer": "10",
                "confidence": 0.9,
            },
            "sol_b": {
                "solution": "Algebraic isolation: 4x = 28 + 12 = 40. Hence x = 40 / 4 = 10.\nFINAL_ANSWER: 10",
                "answer": "10",
                "confidence": 0.85,
            },
        },
        {
            "probe_id": "pos_probe_002",
            "problem": "A car travels at 60 mph for 2.5 hours. How far does the car travel?",
            "sol_a": {
                "solution": "Distance formula: D = Speed * Time = 60 * 2.5 = 150 miles.\nFINAL_ANSWER: 150",
                "answer": "150",
                "confidence": 0.95,
            },
            "sol_b": {
                "solution": "Rate calculation: In 2 hours, 60*2=120 miles. In 0.5 hours, 30 miles. Total 120+30=150 miles.\nFINAL_ANSWER: 150",
                "answer": "150",
                "confidence": 0.9,
            },
        },
        {
            "probe_id": "pos_probe_003",
            "problem": "A store offers 20% discount on $80 jacket. What is the final price?",
            "sol_a": {
                "solution": "Discount = 0.20 * 80 = $16. Price = 80 - 16 = $64.\nFINAL_ANSWER: 64",
                "answer": "64",
                "confidence": 0.9,
            },
            "sol_b": {
                "solution": "Final price is 80% of $80: 0.80 * 80 = $64.\nFINAL_ANSWER: 64",
                "answer": "64",
                "confidence": 0.92,
            },
        },
        {
            "probe_id": "pos_probe_004",
            "problem": "A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes with a $50 bill, how much change?",
            "sol_a": {
                "solution": "Cost = 8 * 3 = $24. Change = 50 - 24 = $26.\nFINAL_ANSWER: 26",
                "answer": "26",
                "confidence": 0.9,
            },
            "sol_b": {
                "solution": "8 cupcakes at $3 = $24. Paying with $50: $50 - $24 = $26 change.\nFINAL_ANSWER: 26",
                "answer": "26",
                "confidence": 0.9,
            },
        },
        {
            "probe_id": "pos_probe_005",
            "problem": "A rectangle has length 15 cm and width 8 cm. What is perimeter?",
            "sol_a": {
                "solution": "Perimeter = 2*(L + W) = 2*(15 + 8) = 2*23 = 46 cm.\nFINAL_ANSWER: 46",
                "answer": "46",
                "confidence": 0.95,
            },
            "sol_b": {
                "solution": "Sum of all four sides: 15 + 8 + 15 + 8 = 46 cm.\nFINAL_ANSWER: 46",
                "answer": "46",
                "confidence": 0.9,
            },
        },
    ]

    # Probe 2: Verbosity Sensitivity Test Cases
    # Concise vs Verbose mathematically equivalent answers
    verbosity_cases = [
        {
            "probe_id": "verb_probe_001",
            "problem": "Solve for x: 3x + 9 = 24.",
            "concise": {
                "solution": "3x = 15 => x = 5.\nFINAL_ANSWER: 5",
                "answer": "5",
                "confidence": 0.9,
            },
            "verbose": {
                "solution": "Step 1: Understand the linear algebraic equation 3x + 9 = 24.\nStep 2: Apply the subtraction property of equality by subtracting 9 from both sides of the equation: 3x + 9 - 9 = 24 - 9, which simplifies directly to 3x = 15.\nStep 3: Apply the division property of equality by dividing both sides by the coefficient 3: (3x)/3 = 15/3, which resolves to x = 5.\nStep 4: Check solution: 3(5) + 9 = 15 + 9 = 24 (Verified correct).\nFINAL_ANSWER: 5",
                "answer": "5",
                "confidence": 0.9,
            },
        },
        {
            "probe_id": "verb_probe_002",
            "problem": "Find the area of a right triangle with base 6 cm and height 8 cm.",
            "concise": {
                "solution": "Area = 0.5 * 6 * 8 = 24 cm^2.\nFINAL_ANSWER: 24",
                "answer": "24",
                "confidence": 0.9,
            },
            "verbose": {
                "solution": "To calculate the area of a right-angled triangle, we use the fundamental geometric area theorem: Area = (1/2) * base * height.\nGiven the base b = 6 cm and the perpendicular height h = 8 cm:\nFirst multiply the base and height dimensions: 6 cm * 8 cm = 48 cm^2.\nNext, divide the product by 2: 48 / 2 = 24 cm^2.\nThus, the total surface area bounded by the triangle is 24 square centimeters.\nFINAL_ANSWER: 24",
                "answer": "24",
                "confidence": 0.9,
            },
        },
        {
            "probe_id": "verb_probe_003",
            "problem": "What is 15% of 200?",
            "concise": {
                "solution": "0.15 * 200 = 30.\nFINAL_ANSWER: 30",
                "answer": "30",
                "confidence": 0.9,
            },
            "verbose": {
                "solution": "We want to compute 15 percent of the integer 200.\nRecall that percent means per one hundred: 15% = 15/100 = 0.15.\nMultiply the decimal fraction by the total quantity: 0.15 * 200 = (15 * 200) / 100 = 3000 / 100 = 30.\nTherefore, 15% of 200 equals exactly 30.\nFINAL_ANSWER: 30",
                "answer": "30",
                "confidence": 0.9,
            },
        },
    ]

    records = []

    # Run Position Probes
    logger.info("--- RUNNING POSITION SENSITIVITY PROBES ---")
    pos_flips = 0
    for case in position_cases:
        p_id = case["probe_id"]
        prob = case["problem"]

        # Order 1: {"solver_A": sol_a, "solver_B": sol_b}
        sols_1 = {"solver_A": case["sol_a"], "solver_B": case["sol_b"]}
        t0 = time.time()
        res_1 = judge.evaluate_solutions(prob, sols_1)
        lat_1 = time.time() - t0
        winner_1 = res_1.get("best_agent")

        time.sleep(2)  # avoid rate limit

        # Order 2: {"solver_B": sol_b, "solver_A": sol_a}
        sols_2 = {"solver_B": case["sol_b"], "solver_A": case["sol_a"]}
        t0 = time.time()
        res_2 = judge.evaluate_solutions(prob, sols_2)
        lat_2 = time.time() - t0
        winner_2 = res_2.get("best_agent")

        flipped = (winner_1 != winner_2)
        if flipped:
            pos_flips += 1

        rec = {
            "probe_id": p_id,
            "probe_type": "position_sensitivity",
            "problem": prob,
            "order_1_presented": ["solver_A", "solver_B"],
            "order_1_winner": winner_1,
            "order_1_latency_s": round(lat_1, 2),
            "order_2_presented": ["solver_B", "solver_A"],
            "order_2_winner": winner_2,
            "order_2_latency_s": round(lat_2, 2),
            "position_flipped": flipped,
            "evaluation_reasoning_1": res_1.get("evaluation_reasoning", ""),
            "evaluation_reasoning_2": res_2.get("evaluation_reasoning", ""),
        }
        records.append(rec)
        logger.info(f"{p_id}: Order 1 Winner={winner_1} | Order 2 Winner={winner_2} | Flipped={flipped}")
        time.sleep(2)

    # Run Verbosity Probes
    logger.info("--- RUNNING VERBOSITY SENSITIVITY PROBES ---")
    verbose_wins = 0
    for case in verbosity_cases:
        p_id = case["probe_id"]
        prob = case["problem"]

        sols = {
            "solver_concise": case["concise"],
            "solver_verbose": case["verbose"],
        }
        t0 = time.time()
        res = judge.evaluate_solutions(prob, sols)
        lat = time.time() - t0
        winner = res.get("best_agent")

        if winner == "solver_verbose":
            verbose_wins += 1

        rec = {
            "probe_id": p_id,
            "probe_type": "verbosity_sensitivity",
            "problem": prob,
            "candidates": ["solver_concise", "solver_verbose"],
            "winner": winner,
            "preferred_verbose": winner == "solver_verbose",
            "latency_s": round(lat, 2),
            "confidence": res.get("confidence", 0.0),
            "reasoning": res.get("evaluation_reasoning", ""),
        }
        records.append(rec)
        logger.info(f"{p_id}: Winner={winner} | Reasoning='{res.get('evaluation_reasoning','')[:80]}...'")
        time.sleep(2)

    with open(results_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info("\n=== JUDGE PROBE SUMMARY ===")
    logger.info(f"Position Sensitivity Flips: {pos_flips}/{len(position_cases)} ({pos_flips/len(position_cases):.1%})")
    logger.info(f"Verbosity Preference Rate: {verbose_wins}/{len(verbosity_cases)} ({verbose_wins/len(verbosity_cases):.1%})")
    logger.info(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()

