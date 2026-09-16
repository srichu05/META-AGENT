# -*- coding: utf-8 -*-
from __future__ import annotations

"""
[DEPRECATED] Legacy API Client for Meta-Agent Math Debate System.

NOTICE: This module is retained strictly for backward compatibility.
All active Draft 2 agents, solvers, reflection, judge, and retrieval
orchestration authoritatively use `backend.providers.router.ProviderRouter`.
"""

import os
import sys
import time
import json
import logging
import warnings
from typing import Dict, Any, List, Optional, Callable

import requests
from dotenv import load_dotenv

# Load .env early
load_dotenv()

# Add project root to path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from config import API_CONFIG, SYSTEM_CONFIG  # noqa: E402

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    COK = Fore.GREEN + "✓" + Style.RESET_ALL
    CERR = Fore.RED + "✗" + Style.RESET_ALL
    CINFO = Fore.CYAN
    CEND = Style.RESET_ALL
    CYEL = Fore.YELLOW
    CMAG = Fore.MAGENTA
except Exception:
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = Style = _Dummy()
    COK = "✓"; CERR = "✗"; CINFO = ""; CEND = ""; CYEL = ""; CMAG = ""

logger = logging.getLogger(__name__)

# Default model names
GROQ_MAIN = "llama-3.3-70b-versatile"
GROQ_FALLBACK = "llama3-8b-8192"
OPENAI_MAIN = "gpt-4o-mini"
OPENAI_EMBED = "text-embedding-3-small"
GEMINI_MAIN = "gemini-2.5-flash"
GEMINI_FALLBACK = "gemini-1.5-flash"
HF_MAIN = "microsoft/Phi-3.5-mini-instruct"
HF_EMBED = "all-MiniLM-L6-v2"



# ──────────────────────────────────────────────────────────────────────
# Prompt Builder for Local LLM Debate Mode
# ──────────────────────────────────────────────────────────────────────
def build_debate_prompt(problem: str, rag_examples: Optional[List[Dict[str, Any]]] = None) -> str:
    context_section = ""
    if rag_examples:
        try:
            lines = []
            for i, ex in enumerate(rag_examples[:3], 1):
                p = ex.get("problem", "")
                a = ex.get("answer", "")
                lines.append(f"[Example {i}] Problem: {p}\n[Example {i}] Answer: {a}")
            context_section = "Reference similar problems:\n" + "\n\n".join(lines) + "\n\n"
        except Exception:
            context_section = ""

    prompt = (
        "You are a team of three math solvers (Solver_A, Solver_B, Solver_C). "
        "Work independently, then agree on a final answer.\n\n"
        "Rules:\n"
        "- Show brief step-by-step reasoning for each solver (2–5 steps).\n"
        "- If someone disagrees, state why quickly.\n"
        "- End with a single \"FINAL_ANSWER: <value>\" line.\n"
        "- Keep it compact and exam-ready.\n\n"
        f"{context_section}"
        "Current Problem:\n"
        f"{problem}\n\n"
        "Format exactly:\n"
        "[Solver_A]\n"
        "- Step 1: ...\n- Step 2: ...\nConclusion: ...\n\n"
        "[Solver_B]\n"
        "- Step 1: ...\n- Step 2: ...\nConclusion: ...\n\n"
        "[Solver_C]\n"
        "- Step 1: ...\n- Step 2: ...\nConclusion: ...\n\n"
        "[Consensus]\n"
        "- Key check(s): ...\n"
        "FINAL_ANSWER: <only the numeric or short expression>\n"
    )
    return prompt


# ──────────────────────────────────────────────────────────────────────
# Local LLM (HF Transformers Only)
# ──────────────────────────────────────────────────────────────────────
class LocalLLM:
    def __init__(self, session: requests.Session, timeout: int = 45):
        self.session = session
        self.timeout = timeout
        local_cfg = SYSTEM_CONFIG.get("LOCAL_MODEL", {})
        self.enabled = bool(local_cfg.get("enabled", True))

        self.model_name = local_cfg.get("model_name", HF_MAIN)
        self.device = local_cfg.get("device", "cpu")

        # Local model cache directory
        self.model_path = os.path.join(_PROJECT_ROOT, "models", "hf-local")
        os.makedirs(self.model_path, exist_ok=True)

        # ✅ Local load kwargs (Optimized, PL1 placement)
        self._load_kwargs = {
            "low_cpu_mem_usage": True,
            "device_map": "auto",
            "trust_remote_code": True
        }

        self._transformers_ready = False
        self._hf_pipeline = None
        self._hf_tokenizer = None

    def available(self) -> bool:
        return self.enabled

    def _ensure_transformers(self) -> bool:
        if self._transformers_ready and self._hf_pipeline is not None:
            return True
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

            torch.set_grad_enabled(False)

            tok = AutoTokenizer.from_pretrained(self.model_name, cache_dir=self.model_path, trust_remote_code=True)
            mdl = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                cache_dir=self.model_path,
                trust_remote_code=True,
                attn_implementation="eager",
                **self._load_kwargs
            )

            self._hf_tokenizer = tok
            self._hf_pipeline = pipeline(
                "text-generation",
                model=mdl,
                tokenizer=tok,
                device_map="auto"
            )
            self._hf_pipeline.model.config.use_cache = False
            self._transformers_ready = True
            return True
        except Exception as e:
            logger.error("Local Transformers failed: %s", str(e))
            self._transformers_ready = False
            self._hf_pipeline = None
            return False

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.2) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "Local LLM disabled", "engine": None}

        if self._ensure_transformers():
            try:
                t0 = time.time()
                outputs = self._hf_pipeline(
                    prompt,
                    max_new_tokens=max_tokens,
                    do_sample=True if temperature > 0 else False,
                    temperature=temperature if temperature > 0 else 0.0,
                    repetition_penalty=1.05,
                    eos_token_id=self._hf_tokenizer.eos_token_id,
                )
                dt = (time.time() - t0) * 1000.0
                if isinstance(outputs, list) and outputs:
                    text = outputs[0].get("generated_text", "")
                    if text.startswith(prompt):
                        text = text[len(prompt):].lstrip()
                    return {
                        "success": True,
                        "response": text,
                        "engine": "LOCAL",
                        "model": self.model_name,
                        "latency_ms": round(dt, 1)
                    }
            except Exception as e:
                return {"success": False, "error": str(e), "engine": "LOCAL", "model": self.model_name}

        return {"success": False, "error": "Local HF Transformers generation failed", "engine": None}


# ──────────────────────────────────────────────────────────────────────
# Hybrid API Client
# ──────────────────────────────────────────────────────────────────────
class APIClient:
    def __init__(self):
        logger.info("%s APIClient.__init__()", CINFO + "🔌" + CEND)
        self.session = requests.Session()
        self.timeout = 45

        self.configured_providers = set()
        self._inspect_providers()

        # Local LLM
        self.local_llm = LocalLLM(self.session, timeout=self.timeout)
        logger.info("Local LLM enabled: %s", str(self.local_llm.available()))

        # Preload Local Embeddings
        self._local_embed_model = None
        self._preload_local_embeddings()

    def _inspect_providers(self) -> None:
        logger.info("%s Checking API provider configuration...", CINFO)
        order = ["GROQ", "OPENAI", "GEMINI", "HUGGING_FACE"]
        for provider in order:
            cfg = API_CONFIG.get(provider, {})
            api_key = (cfg.get("api_key") or "").strip()
            base_url = (cfg.get("base_url") or "").strip()
            default_model = (cfg.get("models", {}).get("default") or "").strip()
            if not api_key or not base_url or not default_model:
                logger.warning("%s %s not configured (key/base_url/model missing)", CYEL + "!" + CEND, provider)
                continue
            self.configured_providers.add(provider)
            logger.info("%s %s configured (model=%s)", COK, provider, default_model)

    def is_configured(self) -> bool:
        return bool(self.configured_providers)

    def get_provider_status(self) -> Dict[str, bool]:
        return {p: (p in self.configured_providers) for p in ["GROQ", "OPENAI", "GEMINI", "HUGGING_FACE"]}

    def _preload_local_embeddings(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            t0 = time.time()
            logger.info("%s Preloading local embeddings: %s", CMAG, HF_EMBED)
            self._local_embed_model = SentenceTransformer(HF_EMBED)
            dt = (time.time() - t0) * 1000.0
            logger.info("%s Local embeddings ready (384d) in %.1f ms", COK, dt)
        except Exception as e:
            logger.error("%s Failed to preload local embeddings: %s", CERR, str(e))
            self._local_embed_model = None

    def _get_gemini_embeddings(self, text: str) -> Optional[List[float]]:
        try:
            cfg = API_CONFIG["GEMINI"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={cfg['api_key']}"
            body = {
                "model": "models/text-embedding-004",
                "content": {
                    "parts": [
                        {"text": text}
                    ]
                }
            }
            r = self.session.post(url, json=body, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            return data["embedding"]["values"]
        except Exception as e:
            logger.warning("Gemini embedding failed: %s", str(e))
            return None

    def get_embeddings(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        if not text or not text.strip():
            logger.warning("get_embeddings called with empty text")
            return None

        if self._local_embed_model is not None:
            try:
                t0 = time.time()
                emb = self._local_embed_model.encode(
                    text, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True
                ).tolist()
                dt = (time.time() - t0) * 1000.0
                logger.info("%s Local embedding OK (len=%d) in %.1f ms", COK, len(emb), dt)
                return emb
            except Exception as e:
                logger.warning("%s Local embeddings failed: %s", CYEL, str(e))

        for prov in ["OPENAI", "GEMINI", "HUGGING_FACE"]:
            if prov not in self.configured_providers:
                continue
            try:
                if prov == "OPENAI":
                    return self._get_openai_embeddings(text)
                elif prov == "GEMINI":
                    return self._get_gemini_embeddings(text)
                else:
                    return self._get_hf_embeddings(text)
            except Exception as e:
                logger.warning("%s %s embeddings failed: %s", CYEL, prov, str(e))
                continue

        logger.error("%s All embedding providers failed", CERR)
        return None


    # ──────────────────────────────────────────────────────────────────
    # LLM Orchestration (GROQ → LOCAL → COHERE → OPENAI → HF)
    # ──────────────────────────────────────────────────────────────────
    def call_best_available_api(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> Dict[str, Any]:
        logger.info("%s call_best_available_api len=%d, T=%.2f", CINFO + "🌐" + CEND, len(prompt), temperature)

        def _try(tag: str, func: Callable[[], Dict[str, Any]]):
            t0 = time.time()
            try:
                res = func()
                dt = (time.time() - t0) * 1000.0
                if res.get("success"):
                    res["api_used"] = tag
                    res["api_latency_ms"] = round(dt, 1)
                    logger.info("%s %s OK in %.1f ms", COK, tag, dt)
                    return res
                else:
                    logger.warning("%s %s failed in %.1f ms: %s", CYEL, tag, dt, str(res.get("error"))[:140])
                    return None
            except Exception as e:
                dt = (time.time() - t0) * 1000.0
                logger.warning("%s %s exception in %.1f ms: %s", CYEL, tag, dt, str(e))
                return None

        local_prompt = build_debate_prompt(prompt)

        if "GROQ" in self.configured_providers:
            res = _try(f"GROQ/{self._groq_model(primary=True)}", lambda: self.call_groq_api(prompt, self._groq_model(primary=True),
                                                                                           max_tokens=max_tokens, temperature=temperature))
            if res: return res
            res = _try(f"GROQ/{self._groq_model(primary=False)}", lambda: self.call_groq_api(prompt, self._groq_model(primary=False),
                                                                                            max_tokens=max_tokens, temperature=temperature))
            if res: return res

        if "GEMINI" in self.configured_providers:
            res = _try(f"GEMINI/{self._gemini_model(primary=True)}", lambda: self.call_gemini_api(prompt, self._gemini_model(primary=True),
                                                                                           max_tokens=max_tokens, temperature=temperature))
            if res: return res
            res = _try(f"GEMINI/{self._gemini_model(primary=False)}", lambda: self.call_gemini_api(prompt, self._gemini_model(primary=False),
                                                                                            max_tokens=max_tokens, temperature=temperature))
            if res: return res

        if "OPENAI" in self.configured_providers:
            res = _try(f"OPENAI/{self._openai_model()}", lambda: self.call_openai_api(prompt, self._openai_model(),
                                                                                      max_tokens=max_tokens, temperature=temperature))
            if res: return res

        if self.local_llm.available():
            res = _try(f"LOCAL/{self.local_llm.model_name}", lambda: self.local_llm.generate(local_prompt, max_tokens=min(1024, max_tokens),
                                                                                            temperature=temperature))
            if res: return res

        if "HUGGING_FACE" in self.configured_providers:
            res = _try(f"HF/{self._hf_model()}", lambda: self.call_hf_api(prompt, self._hf_model(),
                                                                          max_tokens=max_tokens, temperature=temperature))
            if res: return res

        logger.error("%s ALL PROVIDERS FAILED", CERR)
        return {"success": False, "error": "All available providers failed", "response": ""}

    # ──────────────────────────────────────────────────────────────────
    # Provider Calls
    # ──────────────────────────────────────────────────────────────────
    def call_groq_api(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        try:
            cfg = API_CONFIG["GROQ"]
            url = cfg["base_url"] + "chat/completions"
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1500),
                "temperature": kwargs.get("temperature", 0.2),
            }
            r = self.session.post(url,
                                  headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                                  json=body, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return {"success": True, "response": content}
        except requests.HTTPError as e:
            txt = getattr(e.response, "text", "")
            return {"success": False, "error": f"{e} :: {txt[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _groq_model(self, primary: bool = True) -> str:
        models = API_CONFIG.get("GROQ", {}).get("models", {})
        if primary:
            return models.get("default") or GROQ_MAIN
        return models.get("fast") or GROQ_FALLBACK

    def call_openai_api(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        cfg = API_CONFIG["OPENAI"]
        url = cfg["base_url"] + "chat/completions"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 1500),
            "temperature": kwargs.get("temperature", 0.2),
        }
        try:
            r = self.session.post(url,
                                  headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
                                  json=body, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            return {"success": True, "response": data["choices"][0]["message"]["content"]}
        except requests.HTTPError as e:
            txt = getattr(e.response, "text", "")
            return {"success": False, "error": f"{e} :: {txt[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _openai_model(self) -> str:
        return API_CONFIG.get("OPENAI", {}).get("models", {}).get("default") or OPENAI_MAIN

    def call_gemini_api(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        try:
            cfg = API_CONFIG["GEMINI"]
            url = f"{cfg['base_url']}{model}:generateContent?key={cfg['api_key']}"
            body = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", 0.2),
                    "maxOutputTokens": kwargs.get("max_tokens", 2048)
                }
            }
            r = self.session.post(url, json=body, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "response": content}
        except requests.HTTPError as e:
            txt = getattr(e.response, "text", "")
            return {"success": False, "error": f"{e} :: {txt[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _gemini_model(self, primary: bool = True) -> str:
        models = API_CONFIG.get("GEMINI", {}).get("models", {})
        if primary:
            return models.get("default") or GEMINI_MAIN
        return models.get("fast") or GEMINI_FALLBACK

    def call_hf_api(self, prompt: Any, model: str, **kwargs) -> Dict[str, Any]:
        try:
            cfg = API_CONFIG["HUGGING_FACE"]
            url = cfg["base_url"] + model
            r = self.session.post(url,
                                  headers={"Authorization": f"Bearer {cfg['api_key']}"},
                                  json={"inputs": prompt, "options": {"wait_for_model": True}},
                                  timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
                return {"success": True, "response": data[0]["generated_text"]}
            return {"success": True, "response": data}
        except requests.HTTPError as e:
            txt = getattr(e.response, "text", "")
            return {"success": False, "error": f"{e} :: {txt[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _hf_model(self) -> str:
        return API_CONFIG.get("HUGGING_FACE", {}).get("models", {}).get("default") or HF_MAIN
