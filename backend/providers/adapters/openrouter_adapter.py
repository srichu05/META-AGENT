"""OpenRouter API Provider Adapter for Alternative Reasoning Solvers."""

import json
import logging
import re
import time
from typing import Any, Dict, Optional

import requests

from providers.adapters.base import BaseProviderAdapter
from providers.types import ProviderResponse

logger = logging.getLogger(__name__)


class OpenRouterAdapter(BaseProviderAdapter):
    """Adapter for OpenRouter API providing access to DeepSeek, Qwen, Llama models."""

    provider_name = "OPENROUTER"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_model = self.config.get("models", {}).get(
            "default", "deepseek/deepseek-r1-distill-llama-70b"
        )
        self.base_url = self.config.get("base_url") or "https://openrouter.ai/api/v1/chat/completions"

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
                error="OpenRouter API key is missing or unconfigured.",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/srichu05/META-AGENT",
            "X-Title": "Meta-Agent Math Debate System",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            resp = requests.post(self.base_url, headers=headers, json=payload, timeout=35)
            latency_ms = (time.time() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
                comp_tokens = usage.get("completion_tokens", len(text) // 4)
                total_tokens = usage.get("total_tokens", prompt_tokens + comp_tokens)

                # OpenRouter average cost estimate (~$0.14 / 1M prompt, $0.28 / 1M comp)
                cost = (prompt_tokens * 0.14 + comp_tokens * 0.28) / 1000000

                answer, reasoning = self._parse_answer(text)

                return ProviderResponse(
                    success=True,
                    answer=answer,
                    reasoning=reasoning,
                    raw_text=text,
                    confidence=0.87,
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
                logger.warning(f"OpenRouterAdapter API error: {err_msg}")
                return ProviderResponse(
                    success=False,
                    provider=self.provider_name,
                    model=target_model,
                    latency_ms=latency_ms,
                    error=err_msg,
                )
        except Exception as error:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"OpenRouterAdapter Exception: {error}", exc_info=True)
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
