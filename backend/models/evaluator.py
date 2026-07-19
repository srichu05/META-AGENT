# backend/models/evaluator.py
from typing import List, Dict, Optional, Any
from statistics import mean

class Evaluator:
    """
    Single-run evaluator for hybrid setup:
    - Uses existing debate participants (multi-solvers),
    - Adds 2 probes via MetaAgent.solve_problem(): RAG and No-RAG.
    Judge score is mapped from 'confidence' when numeric judge scores are unavailable.
    """

    @staticmethod
    def _safe_mean(values):
        vals = [v for v in values if isinstance(v, (int, float))]
        return mean(vals) if vals else None

    @staticmethod
    def evaluate_single(
        agents_runs: List[Dict[str, Any]],
        judge_winner: Optional[str],
        ground_truth: Optional[str] = None,
        baseline_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        agents_runs item example:
        {
          "name": str,
          "answer": str,
          "used_rag": bool,
          "is_baseline": bool,
          "judge_score": Optional[float],    # mapped from confidence or a real judge score
          "start_time": Optional[float],     # monotonic start (optional)
          "end_time": Optional[float],       # monotonic end (optional)
          "correct": Optional[bool],         # optional precomputed
        }
        """
        per_agent: Dict[str, Any] = {}
        baseline_metrics = None

        # Build normalized metrics per agent
        for run in agents_runs:
            name = str(run.get("name", "Agent"))
            start = run.get("start_time")
            end = run.get("end_time")
            time_taken_ms = None
            if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                time_taken_ms = max(0, (end - start) * 1000.0)

            # compute correctness if ground truth supplied and not provided
            correct = run.get("correct")
            if correct is None and ground_truth is not None:
                try:
                    ga = str(ground_truth).strip()
                    ra = str(run.get("answer", "")).strip()
                    try:
                        correct = float(ra) == float(ga)
                    except Exception:
                        correct = (ra == ga)
                except Exception:
                    correct = None

            per_agent[name] = {
                "used_rag": bool(run.get("used_rag")),
                "is_baseline": bool(run.get("is_baseline")),
                "judge_score": run.get("judge_score"),
                "time_taken_ms": time_taken_ms,
                "answer": run.get("answer"),
                "correct": correct,
                "won": (judge_winner == name) if judge_winner else None,
            }

            if baseline_name and name == baseline_name:
                baseline_metrics = per_agent[name]

        # deltas vs baseline
        if baseline_metrics:
            bscore = baseline_metrics.get("judge_score")
            bacc = baseline_metrics.get("correct")
            for name, m in per_agent.items():
                if name == baseline_name:
                    m["delta_vs_baseline_score"] = 0.0
                    m["delta_vs_baseline_accuracy"] = 0 if bacc is None else 0
                    continue
                # score delta
                if m.get("judge_score") is not None and bscore is not None:
                    try:
                        m["delta_vs_baseline_score"] = float(m["judge_score"]) - float(bscore)
                    except Exception:
                        m["delta_vs_baseline_score"] = None
                else:
                    m["delta_vs_baseline_score"] = None
                # accuracy delta (single-run → -1, 0, +1)
                if m.get("correct") is not None and bacc is not None:
                    m["delta_vs_baseline_accuracy"] = (1 if m["correct"] else 0) - (1 if bacc else 0)
                else:
                    m["delta_vs_baseline_accuracy"] = None
        else:
            for m in per_agent.values():
                m["delta_vs_baseline_score"] = None
                m["delta_vs_baseline_accuracy"] = None

        # RAG boost (compare best judge_score among used_rag vs non-rag)
        rag_scores = [m["judge_score"] for m in per_agent.values() if m["used_rag"] and isinstance(m["judge_score"], (int, float))]
        no_rag_scores = [m["judge_score"] for m in per_agent.values() if (not m["used_rag"]) and isinstance(m["judge_score"], (int, float))]
        best_rag = max(rag_scores) if rag_scores else None
        best_norag = max(no_rag_scores) if no_rag_scores else None
        rag_boost = (best_rag - best_norag) if (best_rag is not None and best_norag is not None) else None

        summary = {
            "winner": judge_winner,
            "best_rag_judge_score": best_rag,
            "best_non_rag_judge_score": best_norag,
            "rag_boost_score": rag_boost,
            "ground_truth_used": ground_truth is not None,
        }

        return {
            "per_agent": per_agent,
            "summary": summary,
        }
