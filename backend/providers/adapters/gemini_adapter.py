"""Gemini API Provider Adapter for Primary Reasoning and Analytical Solvers."""

import json
import logging
import re
import time
from typing import Any, Dict, Optional

import requests

from providers.adapters.base import BaseProviderAdapter
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


class GeminiAdapter(BaseProviderAdapter):
    """Adapter for Google Gemini API (gemini-2.5-flash)."""

    provider_name = "GEMINI"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_model = self.config.get("models", {}).get("default", "gemini-2.5-flash")

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> ProviderResponse:
        target_model = model or self.default_model
        start_time = time.time()

        if not self.is_configured:
            return ProviderResponse(
                success=False,
                provider=self.provider_name,
                model=target_model,
                error="Gemini API key is missing or unconfigured.",
            )

        # Attempt REST API call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        contents = []
        if system_instruction:
            contents.append({"role": "user", "parts": [{"text": f"System Instruction:\n{system_instruction}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow these system instructions."}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            latency_ms = (time.time() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json()
                text = ""
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    text = str(data)

                # Extract token usage metadata if provided
                usage = data.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", len(prompt) // 4)
                comp_tokens = usage.get("candidatesTokenCount", len(text) // 4)
                total_tokens = usage.get("totalTokenCount", prompt_tokens + comp_tokens)

                # Estimated cost per 1M tokens ($0.075 input, $0.30 output for gemini-2.5-flash)
                cost = (prompt_tokens * 0.075 + comp_tokens * 0.30) / 1000000

                answer, reasoning = self._parse_answer(text)

                return ProviderResponse(
                    success=True,
                    answer=answer,
                    reasoning=reasoning,
                    raw_text=text,
                    confidence=0.9,
                    provider=self.provider_name,
                    model=target_model,
                    latency_ms=latency_ms,
                    token_usage={
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": comp_tokens,
                        "total_tokens": total_tokens,
                    },
                    estimated_cost=cost,
                )
            else:
                err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(f"GeminiAdapter API error: {err_msg}")
                return ProviderResponse(
                    success=False,
                    provider=self.provider_name,
                    model=target_model,
                    latency_ms=latency_ms,
                    error=err_msg,
                )
        except Exception as error:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"GeminiAdapter Exception: {error}", exc_info=True)
            return ProviderResponse(
                success=False,
                provider=self.provider_name,
                model=target_model,
                latency_ms=latency_ms,
                error=str(error),
            )

    def _parse_answer(self, text: str) -> tuple[str, str]:
        ans_m = re.search(r"FINAL_ANSWER:\s*(.+)", text, re.I)
        answer = ans_m.group(1).strip() if ans_m else text.strip()
        reasoning = text.strip()
        return answer, reasoning
