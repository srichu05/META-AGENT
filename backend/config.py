"""
Configuration file for Meta-Agent Math Debate System
Handles API configs, system paths, RAG settings & Local LLM setup.
"""

import os
import sys
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════
# 📍 Load .env from backend folder (Not root!)
# ═══════════════════════════════════════════════════════════════════════

CONFIG_DIR = Path(__file__).resolve().parent
ENV_PATH = CONFIG_DIR / '.env'

load_dotenv(dotenv_path=ENV_PATH, override=True)

# ═══════════════════════════════════════════════════════════════════════
# 🌍 API PROVIDER CONFIG
# (Order here must match fallback priority in APIClient)
# ═══════════════════════════════════════════════════════════════════════

API_CONFIG: Dict[str, Any] = {
    # Groq – Your first priority (fast + generous free tier)
    "GROQ": {
        "base_url": "https://api.groq.com/openai/v1/",
        "api_key": os.getenv("GROQ_API_KEY"),
        "models": {
            "default": "llama-3.1-8b-instant",
            "fast": "llama-3.1-70b-versatile"
        }
    },

    # OpenAI – Used only if needed (rate-limits, but solid)
    "OPENAI": {
        "base_url": "https://api.openai.com/v1/",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "models": {
            "default": "gpt-4o-mini",
            "embedding": "text-embedding-3-small"
        }
    },

    # Gemini – Backup/Primary fallback (free-tier friendly)
    "GEMINI": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "models": {
            "default": "gemini-2.5-flash",
            "fast": "gemini-1.5-flash"
        }
    },

    # HuggingFace – Backup only (unstable but free)
    "HUGGING_FACE": {
        "base_url": "https://api-inference.huggingface.co/models/",
        "api_key": os.getenv("HUGGING_FACE_API_KEY"),
        "models": {
            "default": "microsoft/Phi-3.5-mini-instruct",
            "embedding": "sentence-transformers/all-MiniLM-L6-v2"
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════
# ⚙️ SYSTEM CONFIG
# ═══════════════════════════════════════════════════════════════════════

SYSTEM_CONFIG = {
    # File Paths (relative to backend)
    "vector_db_path": os.getenv("VECTOR_DB_PATH", "./database/vector_store.db"),
    "problems_db_path": os.getenv("PROBLEMS_DB_PATH", "./data/math_problems.json"),
    "solutions_db_path": os.getenv("SOLUTIONS_DB_PATH", "./database/solutions.csv"),
    "log_file_path": os.getenv("LOG_FILE_PATH", "./logs/app.log"),

    # AI / Debate Settings
    "debate_rounds": int(os.getenv("DEBATE_ROUNDS", "3")),
    "max_tokens_completion": int(os.getenv("MAX_TOKENS_COMPLETION", "2048")),
    "temperature": float(os.getenv("TEMPERATURE", "0.2")),

    # 🧠 Local LLM (used when APIs fail)
    "LOCAL_MODEL": {
        "enabled": os.getenv("LOCAL_MODEL_ENABLED", "True").lower() in ("true", "1", "yes"),
        "model_name": os.getenv("LOCAL_MODEL_NAME", "microsoft/Phi-3.5-mini-instruct"),
        "model_path": os.getenv("LOCAL_MODEL_PATH", "./models/phi"),
        "device": os.getenv("LOCAL_MODEL_DEVICE", "cpu"),
        "max_context_tokens": int(os.getenv("LOCAL_MODEL_MAX_TOKENS", "4096")),
        "response_style": os.getenv("LOCAL_MODEL_STYLE", "multi_agent")
    },

    # App Server
    "PORT": int(os.getenv("PORT", "5000")),
    "DEBUG_MODE": os.getenv("DEBUG", "True").lower() in ("true", "1", "yes"),
    "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "*")
}

# ═══════════════════════════════════════════════════════════════════════
# 🤖 AGENT & RAG CONFIG
# ═══════════════════════════════════════════════════════════════════════

AGENT_ROLES = {
    "solver_1": "Analytical Math Solver - Focuses on step-by-step algebraic solutions",
    "solver_2": "Creative Problem Solver - Looks for alternative approaches and shortcuts",
    "solver_3": "Verification Agent - Double-checks calculations and logic",
    "judge": "Judge Agent - Evaluates solutions and selects the best approach"
}

PROBLEM_TYPES = [
    "arithmetic", "algebra", "geometry", "word_problem", "percentage",
    "fractions", "time_distance", "money", "probability"
]

RAG_CONFIG = {
    "chunk_size": int(os.getenv("CHUNK_SIZE", "500")),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "50")),
    "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.55")),
    "embeddings_cache": "./database/embeddings_cache.pkl"
}

# ═══════════════════════════════════════════════════════════════════════
# ✅ CONFIG VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════

def is_valid_api_key(key_value: str | None) -> bool:
    if not key_value:
        return False
    
    k = key_value.strip()
    if not k or k.lower() in [
        "none", "null", "your_api_key_here", "your-api-key",
        "sk-xxx", "your_groq_key_here", "your_openai_key_here",
        "your_cohere_key_here", "your_hf_key_here"
    ]:
        return False
    
    return True


def get_config_status() -> Dict[str, Any]:
    status = {"providers": {}, "configured_count": 0, "missing_count": 0, "is_usable": False}
    
    for provider in ["GROQ", "OPENAI", "GEMINI", "HUGGING_FACE"]:
        key = API_CONFIG[provider]["api_key"]
        valid = is_valid_api_key(key)
        
        status["providers"][provider] = {
            "configured": valid,
            "key_present": bool(key),
            "key_preview": f"{key[:8]}...{key[-4:]}" if valid and len(key) > 12 else "MISSING"
        }
        
        status["configured_count"] += 1 if valid else 0
    
    status["is_usable"] = status["configured_count"] > 0
    return status


def print_config_status():
    status = get_config_status()
    
    print("=" * 70)
    print("META-AGENT SYSTEM CONFIGURATION")
    print("=" * 70)
    print(f"\nAPI Providers Configured: {status['configured_count']}/4\n")
    
    for provider, info in status["providers"].items():
        icon = "[OK]" if info["configured"] else "[X]"
        label = "CONFIGURED" if info["configured"] else "MISSING"
        print(f"   {icon} {provider:<15} - {label}")
    
    # Local Model
    local_cfg = SYSTEM_CONFIG["LOCAL_MODEL"]
    print(f"\nLocal LLM Enabled: {local_cfg['enabled']}")
    print(f"   Model: {local_cfg['model_name']}  ({local_cfg['device']})")
    print()
    
    if status["is_usable"]:
        print("System is READY to roll!")
    else:
        print("NO APIs configured. Add at least one key in .env")
    
    print("=" * 70)
    print()
    
    return status["is_usable"]


# Print config on import
if __name__ != "__main__":
    print_config_status()


# Test mode
if __name__ == "__main__":
    print("\n🧪 Running Config Diagnostics...\n")
    print_config_status()
    sys.exit(0)
