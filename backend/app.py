"""
API-Only Flask Backend for Meta-Agent Math Debate System
SEPARATED: This version serves pure JSON APIs and does not handle frontend files.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from datetime import datetime
import traceback
import os
import sys
from typing import Dict, Any, Optional

# Load .env BEFORE importing config
load_dotenv()

# Adjust Python path to include the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.meta_agent import MetaAgent
from utils.data_processor import DataProcessor
from utils.logger import setup_logger
from config import SYSTEM_CONFIG
from database import init_database
from api.documents import documents_blueprint

# --- Flask App Initialization ---
app = Flask(__name__)
app.config.update(
    SECRET_KEY=SYSTEM_CONFIG["secret_key"],
    SQLALCHEMY_DATABASE_URI=SYSTEM_CONFIG["database_url"],
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
init_database(app)
app.config["MAX_CONTENT_LENGTH"] = SYSTEM_CONFIG["max_upload_file_size_bytes"]
app.register_blueprint(documents_blueprint)

# CORS (single init is enough)
allowed_origins = [
    "http://127.0.0.1:5501",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://localhost:5500",
    "*"
]
CORS(
    app,
    origins=allowed_origins,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    supports_credentials=True,
    max_age=3600,
)

logger = setup_logger(__name__)

# --- Global Application State ---
meta_agent: Optional[MetaAgent] = None
data_processor: Optional[DataProcessor] = None

# Store the most recent evaluation snapshot for the Evaluation tab
last_evaluation: Dict[str, Any] = {}


def _compute_eval_feedback(ok: bool, rag_used: bool, conf: float, latency_s: float) -> str:
    """Tiny rule-based feedback line for the eval tab."""
    if not ok:
        if rag_used:
            return "Solution failed even with RAG; try a simpler query or check embeddings."
        return "Solution failed without RAG; enable RAG or rephrase the problem."
    hints = []
    if conf < 0.5:
        hints.append("low confidence")
    if latency_s > 8:
        hints.append("slow; consider a faster provider/model")
    if rag_used:
        hints.append("RAG assisted")
    return "OK" + (f" — {', '.join(hints)}" if hints else "")


def _build_evaluation(problem: str, result: Dict[str, Any], rag_delta: int, rag_avg_sim: float) -> Dict[str, Any]:
    """
    Build an evaluation object from a solve/debate result.
    Accuracy is left None unless you pass/compute a ground truth elsewhere.
    """
    ok = bool(result.get("success"))
    latency_s = float(result.get("total_time", 0.0))
    confidence = float(result.get("confidence", 0.0))
    api_used = result.get("api_used") or "—"
    rag_used = bool(result.get("rag_enabled") or result.get("rag_usage_stats") or rag_delta > 0)
    feedback = _compute_eval_feedback(ok, rag_used, confidence, latency_s)

    # Optional: if you add ground truth later, set accuracy True/False here.
    accuracy = None

    return {
        "timestamp": datetime.now().isoformat(),
        "problem": problem,
        "success": ok,
        "accuracy": accuracy,                       # shown as "—" in UI if None
        "confidence": confidence,
        "total_time": round(latency_s, 2),
        "api_used": api_used,
        "rag_used": rag_used,
        "rag_similarity": round(rag_avg_sim, 3) if rag_avg_sim else 0.0,
        "feedback": feedback,
    }


def initialize_app() -> bool:
    """Initialize all application components, including the MetaAgent."""
    global meta_agent, data_processor

    try:
        logger.info("🚀 Initializing Meta-Agent Math Debate System (API-Only)...")

        # Warn if external providers not set; allow local fallbacks if your APIClient supports it
        required_env_vars = ["GROQ_API_KEY", "OPENAI_API_KEY", "COHERE_API_KEY", "HUGGING_FACE_API_KEY"]
        missing_vars = [v for v in required_env_vars if not os.getenv(v)]
        if missing_vars:
            logger.warning(
                "⚠️ Missing API keys for providers: %s — proceeding (local/other fallbacks may be used).",
                ", ".join(missing_vars),
            )

        data_processor = DataProcessor()
        meta_agent = MetaAgent()
        if not meta_agent.initialize():
            raise RuntimeError("Failed to initialize the MetaAgent and its sub-components.")

        logger.info("✅ Application initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {str(e)}", exc_info=True)
        return False


# --- HTML Pages ---

@app.route("/", methods=["GET"])
def root():
    """Root endpoint - provides welcome page with API information"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Meta-Agent Math Debate System API</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px;
            }}
            .container {{ max-width: 900px; margin: 50px auto; background: white; padding: 40px;
                border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }}
            h1 {{ color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 15px; margin-bottom: 20px; }}
            h2 {{ color: #764ba2; margin-top: 30px; margin-bottom: 15px; }}
            .endpoint {{ background: #f0f9ff; padding: 15px; margin: 10px 0; border-left: 4px solid #3b82f6; border-radius: 4px; }}
            .endpoint strong {{ color: #667eea; }}
            .endpoint code {{ background: #e2e8f0; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 12px; }}
            .btn {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
                padding: 15px 30px; border-radius: 8px; text-decoration: none; margin: 10px 10px 10px 0; font-weight: bold;
                transition: transform 0.2s, box-shadow 0.2s; }}
            .btn:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); }}
            .status {{ background: #10b981; color: white; padding: 10px 20px; border-radius: 25px; display: inline-block; margin-bottom: 20px; }}
            .info-box {{ background: #f8fafc; border: 2px solid #e2e8f0; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧮 Meta-Agent Math Debate System</h1>
            <div class="status">✅ API Server Online</div>

            <p>Welcome! Use the endpoints below or connect your frontend.</p>

            <h2>🚀 Quick Access</h2>
            <a href="/test" class="btn">🧪 Open Test Interface</a>
            <a href="/api/health" class="btn">✅ Health Check</a>
            <a href="/api/problems" class="btn">📚 Sample Problems</a>
            <a href="/api/stats" class="btn">📊 System Stats</a>

            <h2>📖 API Endpoints</h2>
            <div class="endpoint"><strong>GET</strong> <a href="/api/health" target="_blank">/api/health</a></div>
            <div class="endpoint"><strong>GET</strong> <a href="/api/problems" target="_blank">/api/problems</a></div>
            <div class="endpoint"><strong>GET</strong> <a href="/api/stats" target="_blank">/api/stats</a></div>
            <div class="endpoint"><strong>GET</strong> <a href="/api/evaluation/last" target="_blank">/api/evaluation/last</a></div>
            <div class="endpoint"><strong>POST</strong> /api/solve &nbsp;&nbsp;<code>{{"problem": "25 + 17 = ?"}}</code></div>
            <div class="endpoint"><strong>POST</strong> /api/debate &nbsp;<code>{{"problem": "...", "rounds": 3}}</code></div>
            <div class="endpoint"><strong>POST</strong> /api/analyze &nbsp;<code>{{"problem": "..."}}</code></div>

            <div class="info-box">
                <h2>🔧 System Configuration</h2>
                <p><strong>Environment:</strong> {os.getenv('FLASK_ENV', 'development')}</p>
                <p><strong>Port:</strong> {os.getenv('PORT', '5000')}</p>
                <p><strong>Debug Mode:</strong> {os.getenv('DEBUG', 'False')}</p>
            </div>
        </div>
    </body>
    </html>
    """


@app.route("/test", methods=["GET"])
def test_page():
    """Serve the test HTML page"""
    try:
        html_path = os.path.join(os.path.dirname(__file__), "test_backend.html")
        if os.path.exists(html_path):
            return send_file(html_path)
        return jsonify(
            {"success": False, "error": "test_backend.html not found in backend folder", "path_checked": html_path}
        ), 404
    except Exception as e:
        logger.error(f"Error serving test page: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# --- API Endpoints ---

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "Meta-Agent Math Debate API is active.",
            "environment": os.getenv("FLASK_ENV", "development"),
        }
    )


@app.route("/api/solve", methods=["POST"])
def solve_problem():
    """Solve a single problem and record an evaluation snapshot."""
    global last_evaluation

    try:
        data = request.get_json(force=True) or {}
        problem = (data.get("problem") or "").strip()
        if not problem:
            return jsonify({"success": False, "error": "Problem text is required"}), 400
        if not meta_agent:
            return jsonify({"success": False, "error": "System not initialized"}), 500

        # capture RAG usage baseline (per-call delta)
        rag_before = 0
        rag_avg_before = 0.0
        if getattr(meta_agent, "vector_store", None):
            vs = meta_agent.vector_store
            rag_before = getattr(vs, "rag_usage_count", 0)
            scores = getattr(vs, "rag_similarity_scores", []) or []
            rag_avg_before = float(sum(scores) / len(scores)) if scores else 0.0

        logger.info(f"📝 Solve request: '{problem[:80]}...'")

        result = meta_agent.solve_problem(problem)

        # compute rag deltas
        rag_delta = 0
        rag_avg_sim = 0.0
        if getattr(meta_agent, "vector_store", None):
            vs = meta_agent.vector_store
            rag_after = getattr(vs, "rag_usage_count", rag_before)
            rag_delta = max(0, rag_after - rag_before)
            scores = getattr(vs, "rag_similarity_scores", []) or []
            rag_avg_after = float(sum(scores) / len(scores)) if scores else 0.0
            rag_avg_sim = rag_avg_after if rag_after > rag_before else rag_avg_before

        # build evaluation snapshot and store it
        last_evaluation = _build_evaluation(problem, result, rag_delta, rag_avg_sim)

        # Return the original result (front-end already expects this shape)
        return jsonify(result)

    except Exception as e:
        logger.error(f"✗ Error in /api/solve: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/debate", methods=["POST"])
def run_debate():
    """Run debate and record an evaluation snapshot as well (winner-based)."""
    global last_evaluation

    try:
        data = request.get_json(force=True) or {}
        problem = (data.get("problem") or "").strip()
        rounds = int(data.get("rounds", 3))
        if not problem:
            return jsonify({"success": False, "error": "Problem text is required"}), 400
        if not meta_agent:
            return jsonify({"success": False, "error": "System not initialized"}), 500

        rag_before = 0
        rag_avg_before = 0.0
        if getattr(meta_agent, "vector_store", None):
            vs = meta_agent.vector_store
            rag_before = getattr(vs, "rag_usage_count", 0)
            scores = getattr(vs, "rag_similarity_scores", []) or []
            rag_avg_before = float(sum(scores) / len(scores)) if scores else 0.0

        logger.info(f"🎪 Debate request: '{problem[:80]}...', rounds={rounds}")

        debate_result = meta_agent.run_debate(problem, rounds)

        rag_delta = 0
        rag_avg_sim = 0.0
        if getattr(meta_agent, "vector_store", None):
            vs = meta_agent.vector_store
            rag_after = getattr(vs, "rag_usage_count", rag_before)
            rag_delta = max(0, rag_after - rag_before)
            scores = getattr(vs, "rag_similarity_scores", []) or []
            rag_avg_after = float(sum(scores) / len(scores)) if scores else 0.0
            rag_avg_sim = rag_avg_after if rag_after > rag_before else rag_avg_before

        # Build evaluation snapshot (use fields from judge result if present)
        eval_source = {
            "success": bool(debate_result.get("success", True)),
            "confidence": float(debate_result.get("confidence", 0.0)),
            "total_time": float(debate_result.get("total_time", 0.0)),
            "api_used": debate_result.get("api_used") or "—",
            "rag_enabled": bool(debate_result.get("rag_usage_stats")),
        }
        last_evaluation = _build_evaluation(problem, eval_source, rag_delta, rag_avg_sim)

        return jsonify(debate_result)

    except Exception as e:
        logger.error(f"💥 Error in /api/debate: {str(e)}", exc_info=True)
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "debate_winner": "Error",
                "final_solution": f"Exception: {str(e)}",
                "traceback": traceback.format_exc(),
            }
        ), 500


@app.route("/api/analyze", methods=["POST"])
def analyze_problem():
    try:
        data = request.get_json(force=True) or {}
        problem = (data.get("problem") or "").strip()
        if not problem:
            return jsonify({"success": False, "error": "Problem text is required"}), 400
        if not meta_agent or not meta_agent.retriever_agent:
            return jsonify({"success": False, "error": "System not initialized"}), 500

        logger.info(f"🔍 Analyze request: '{problem[:80]}...'")

        patterns = meta_agent.retriever_agent.find_solution_patterns(problem)
        hints = meta_agent.retriever_agent.get_contextual_hints(problem, max_hints=5)

        result = {
            "success": True,
            "problem": problem,
            "problem_type": patterns.get("problem_type", "unknown"),
            "difficulty": patterns.get("difficulty", "medium"),
            "concepts": patterns.get("concepts", ""),
            "approaches": patterns.get("approaches", ""),
            "hints": hints,
            "confidence": patterns.get("confidence", 0.5),
            "similar_count": patterns.get("similar_count", 0),
        }
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in /api/analyze: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        if not meta_agent:
            return jsonify({"success": False, "error": "System not initialized"}), 500
        stats = meta_agent.get_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload_corpus", methods=["POST"])
def upload_corpus():
    """Upload and index a custom knowledge corpus (JSON or JSONL) for RAG."""
    import json
    import re
    if not data_processor or not meta_agent or not meta_agent.vector_store:
        return jsonify({"success": False, "error": "System not fully initialized"}), 500

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    try:
        content_str = file.read().decode("utf-8")
        problems = []

        # Try parsing as JSON first
        try:
            data = json.loads(content_str)
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list):
                problems = data
        except json.JSONDecodeError:
            # Try parsing as JSONL (line by line)
            lines = content_str.strip().split("\n")
            for line_idx, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    problems.append(json.loads(line))
                except json.JSONDecodeError as line_err:
                    return jsonify({"success": False, "error": f"Invalid JSONL at line {line_idx}: {str(line_err)}"}), 400

        if not problems:
            return jsonify({"success": False, "error": "No problems found in the uploaded file"}), 400

        # Standardize problem structures
        standardized_problems = []
        for p in problems:
            if not isinstance(p, dict):
                continue
            
            problem_text = p.get("problem") or p.get("question") or ""
            problem_text = str(problem_text).strip()
            if not problem_text or len(problem_text) < 10:
                continue

            solution_text = p.get("solution") or p.get("answer") or ""
            solution_text = str(solution_text).strip()

            # Separate numeric answer if answer field is structured
            answer_val = p.get("answer") or ""
            if "\n" in str(answer_val) or len(str(answer_val)) > 80:
                if not solution_text:
                    solution_text = str(answer_val)
                match = re.search(r"####\s*(.+)", str(answer_val))
                if match:
                    answer_val = match.group(1).strip()

            standardized_problems.append({
                "problem": problem_text,
                "solution": solution_text,
                "answer": str(answer_val).strip(),
                "type": p.get("type") or data_processor._detect_problem_type(problem_text),
                "difficulty": p.get("difficulty") or "medium",
                "source": p.get("source") or "uploaded_corpus",
                "steps": p.get("steps") or []
            })

        if not standardized_problems:
            return jsonify({"success": False, "error": "No valid math problems found in the file after validation"}), 400

        logger.info(f"Uploading corpus: {len(standardized_problems)} problems parsed. Generating embeddings...")

        # 1. Overwrite problems JSON database
        data_processor.overwrite_problems_file(standardized_problems)

        # 2. Clear vector store and re-index
        meta_agent.vector_store.clear()
        
        texts = [p["problem"] for p in standardized_problems]
        embeddings = []
        for txt in texts:
            emb = meta_agent.api_client.get_embeddings(txt)
            embeddings.append(emb if emb else [0.0] * meta_agent.vector_store.dimension)

        meta_agent.vector_store.add_math_problems(standardized_problems, embeddings)
        meta_agent.vector_store.save()

        if meta_agent.retriever_agent:
            meta_agent.retriever_agent.vector_store = meta_agent.vector_store

        return jsonify({
            "success": True,
            "message": f"Successfully indexed {len(standardized_problems)} problems into RAG vector store",
            "count": len(standardized_problems)
        })

    except Exception as e:
        logger.error(f"Error uploading corpus: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/corpus", methods=["GET"])
def get_corpus():
    """Retrieve details and list of active problems in the current corpus."""
    try:
        if not data_processor:
            return jsonify({"success": False, "error": "System not initialized"}), 500
        
        problems = data_processor.get_sample_problems()
        return jsonify({
            "success": True,
            "count": len(problems),
            "problems": problems[:100]
        })
    except Exception as e:
        logger.error(f"Error retrieving corpus: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/problems", methods=["GET"])
def get_sample_problems():
    try:
        if not data_processor:
            return jsonify({"success": False, "error": "Data processor not initialized"}), 500
        problems = data_processor.get_sample_problems()
        return jsonify({"success": True, "problems": problems})
    except Exception as e:
        logger.error(f"Error getting sample problems: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/evaluation/last", methods=["GET"])
def get_last_evaluation():
    """Return the most recent evaluation snapshot for the Evaluation tab."""
    if not last_evaluation:
        return jsonify(
            {"success": True, "evaluation": {}, "message": "No evaluation recorded yet. Run /api/solve first."}
        )
    return jsonify({"success": True, "evaluation": last_evaluation})


# --- Error Handlers ---

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
    return jsonify({"success": False, "error": "An internal server error occurred"}), 500


# --- Main Execution Block ---

if __name__ == "__main__":
    if not initialize_app():
        logger.critical(">>> APPLICATION FAILED TO INITIALIZE. EXITING. <<<")
        sys.exit(1)

    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    flask_env = os.getenv("FLASK_ENV", "development")

    logger.info("=" * 60)
    logger.info(f"🌐 Starting API-Only Flask Backend on http://0.0.0.0:{port}")
    logger.info(f"🔧 Debug Mode: {'On' if debug_mode else 'Off'}")
    logger.info(f"🌍 Environment: {flask_env}")
    logger.info("🚫 This server only provides APIs. Serve the frontend separately.")
    logger.info("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=debug_mode)
