"""Environment-backed configuration for the Draft 2 backend foundation."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def _path_from_env(name: str, default: Path) -> str:
    value = os.getenv(name)
    if not value:
        return str(default)
    path = Path(value)
    return str(path if path.is_absolute() else BACKEND_DIR / path)


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'database' / 'draft2_bootstrap.db'}"

API_CONFIG: Dict[str, Dict[str, Any]] = {
    "GEMINI": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "models": {"default": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), "fast": os.getenv("GEMINI_FAST_MODEL", "gemini-1.5-flash")},
    },
    "GROQ": {
        "base_url": "https://api.groq.com/openai/v1/",
        "api_key": os.getenv("GROQ_API_KEY"),
        "models": {"default": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), "fast": os.getenv("GROQ_FAST_MODEL", "llama3-8b-8192")},
    },

    "OPENROUTER": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "models": {
            "default": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-distill-llama-70b"),
            "fallback": os.getenv("OPENROUTER_FALLBACK_MODEL", "qwen/qwen-2.5-72b-instruct"),
        },
    },
    "COHERE": {
        "base_url": "https://api.cohere.com/v2/",
        "api_key": os.getenv("COHERE_API_KEY"),
        "models": {"default": os.getenv("COHERE_MODEL", "rerank-v3.5")},
    },
    # DEPRECATED: OpenAI is deprecated from active debate solvers; retained only for optional fallback compatibility.
    "OPENAI": {
        "base_url": "https://api.openai.com/v1/",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "models": {"default": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "embedding": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")},
    },
    "HUGGING_FACE": {
        "base_url": "https://api-inference.huggingface.co/models/",
        "api_key": os.getenv("HUGGING_FACE_API_KEY"),
        "models": {"default": os.getenv("HUGGING_FACE_MODEL", "microsoft/Phi-3.5-mini-instruct")},
    },
}


SYSTEM_CONFIG: Dict[str, Any] = {
    "secret_key": os.getenv("SECRET_KEY", "dev-fallback-key-change-in-production"),
    "database_url": DATABASE_URL,
    "upload_folder": _path_from_env("UPLOAD_FOLDER", BACKEND_DIR / "uploads"),
    "vector_db_path": _path_from_env("VECTOR_DB_PATH", BACKEND_DIR / "database" / "vector_store.db"),
    "problems_db_path": _path_from_env("PROBLEMS_DB_PATH", BACKEND_DIR / "data" / "math_problems.json"),
    "solutions_db_path": _path_from_env("SOLUTIONS_DB_PATH", BACKEND_DIR / "database" / "solutions.csv"),
    "log_file_path": _path_from_env("LOG_FILE_PATH", BACKEND_DIR / "logs" / "app.log"),
    "debate_rounds": int(os.getenv("DEBATE_ROUNDS", "3")),
    "max_tokens_completion": int(os.getenv("MAX_TOKENS_COMPLETION", "2048")),
    "temperature": float(os.getenv("TEMPERATURE", "0.2")),
    "top_k_retrieval": int(os.getenv("TOP_K_RETRIEVAL", "5")),
    "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "384")),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
    "max_upload_file_size_bytes": int(os.getenv("MAX_UPLOAD_FILE_SIZE_BYTES", str(25 * 1024 * 1024))),
    "PORT": int(os.getenv("PORT", "5000")),
    "DEBUG_MODE": _as_bool(os.getenv("DEBUG"), default=True),
    "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "*"),
    "PLANNER_ENABLED": _as_bool(os.getenv("PLANNER_ENABLED"), default=True),
    "REFLECTION_ENABLED": _as_bool(os.getenv("REFLECTION_ENABLED"), default=True),
    # TODO(Draft 2): remove this compatibility block when APIClient is retired.
    "LOCAL_MODEL": {
        "enabled": _as_bool(os.getenv("LOCAL_MODEL_ENABLED"), default=False),
        "model_name": os.getenv("LOCAL_MODEL_NAME", "microsoft/Phi-3.5-mini-instruct"),
        "model_path": os.getenv("LOCAL_MODEL_PATH", "./models/phi"),
        "device": os.getenv("LOCAL_MODEL_DEVICE", "cpu"),
        "max_context_tokens": int(os.getenv("LOCAL_MODEL_MAX_TOKENS", "4096")),
        "response_style": os.getenv("LOCAL_MODEL_STYLE", "multi_agent"),
    },
}


RAG_CONFIG: Dict[str, Any] = {
    "chunk_size": int(os.getenv("CHUNK_SIZE", "500")),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "50")),
    "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.55")),
    "embeddings_cache": _path_from_env("EMBEDDINGS_CACHE", BACKEND_DIR / "database" / "embeddings_cache.pkl"),
    "hybrid_enabled": _as_bool(os.getenv("HYBRID_RETRIEVAL_ENABLED"), default=True),
    "bm25_weight": float(os.getenv("BM25_WEIGHT", "0.3")),
    "faiss_weight": float(os.getenv("FAISS_WEIGHT", "0.7")),
    "cohere_rerank_enabled": _as_bool(os.getenv("COHERE_RERANK_ENABLED"), default=False),
    "cohere_rerank_model": os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5"),
    "max_context_length": int(os.getenv("MAX_CONTEXT_LENGTH", "4000")),
}


INGESTION_CONFIG: Dict[str, Any] = {
    "supported_file_types": {
        ".pdf": "pdf",
        ".docx": "docx",
        ".txt": "txt",
        ".md": "markdown",
        ".markdown": "markdown",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".bmp": "image",
        ".tif": "image",
        ".tiff": "image",
        ".webp": "image",
    },
    "max_file_size_bytes": int(os.getenv("MAX_UPLOAD_FILE_SIZE_BYTES", str(25 * 1024 * 1024))),
    "chunk_size": int(os.getenv("CHUNK_SIZE", "500")),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "50")),
    "embedding_batch_size": int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
    "faiss_index_path": _path_from_env("FAISS_INDEX_PATH", BACKEND_DIR / "database" / "document_vectors.faiss"),
    "document_list_limit": int(os.getenv("DOCUMENT_LIST_LIMIT", "50")),
}

AGENT_ROLES = {
    "solver_1": "Analytical Math Solver - Focuses on step-by-step algebraic solutions",
    "solver_2": "Creative Problem Solver - Looks for alternative approaches and shortcuts",
    "solver_3": "Verification Agent - Double-checks calculations and logic",
    "judge": "Judge Agent - Evaluates solutions and selects the best approach",
}

PROBLEM_TYPES = [
    "arithmetic", "algebra", "geometry", "word_problem", "percentage",
    "fractions", "time_distance", "money", "probability",
]

API_INSTRUCTIONS = "Set GEMINI_API_KEY, GROQ_API_KEY, or COHERE_API_KEY in backend/.env."


def is_valid_api_key(key_value: Optional[str]) -> bool:
    if not key_value:
        return False
    return key_value.strip().lower() not in {"", "none", "null", "your_api_key_here", "your-api-key", "sk-xxx"}


def get_config_status() -> Dict[str, Any]:
    providers = {}
    for provider, config in API_CONFIG.items():
        providers[provider] = {"configured": is_valid_api_key(config.get("api_key"))}
    configured_count = sum(info["configured"] for info in providers.values())
    return {"providers": providers, "configured_count": configured_count, "missing_count": len(providers) - configured_count, "is_usable": configured_count > 0}


def print_config_status() -> bool:
    status = get_config_status()
    print(f"API providers configured: {status['configured_count']}/{len(status['providers'])}")
    return status["is_usable"]
