"""llama.cpp provider. Talks to any OpenAI-compatible API (llama.cpp, vLLM, etc)."""

from __future__ import annotations

import json
import logging

import httpx

from foundry.agents.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class LlamaCppProvider(LLMProvider):
    name = "llama-cpp"

    def __init__(self, base_url: str = "http://localhost:18080", model: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or "default"

    async def analyze(self, content: str, prompt: str) -> str:
        full_prompt = f"{prompt}\n\n---\n{content}\n---"

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                return resp.status_code < 400
        except (httpx.HTTPError, Exception):
            return False
