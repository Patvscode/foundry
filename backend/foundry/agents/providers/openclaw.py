"""OpenClaw gateway provider. Uses the local OpenClaw gateway as an LLM backend."""

from __future__ import annotations

import json
import logging

import httpx

from foundry.agents.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenClawProvider(LLMProvider):
    name = "openclaw"

    def __init__(self, gateway_url: str = "http://localhost:18789", model: str = "") -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.model = model

    async def analyze(self, content: str, prompt: str) -> str:
        full_prompt = f"{prompt}\n\n---\n{content}\n---"

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.gateway_url}/v1/chat/completions",
                json={
                    "model": self.model or "default",
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
                resp = await client.get(f"{self.gateway_url}/v1/models")
                return resp.status_code < 400
        except (httpx.HTTPError, Exception):
            return False
