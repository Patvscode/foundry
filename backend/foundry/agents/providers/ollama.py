"""Ollama LLM provider. Calls the local Ollama API for text generation."""

from __future__ import annotations

import json
import logging

import httpx

from foundry.agents.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def _detect_model(self) -> str:
        """If no model configured, pick the first available one."""
        if self.model:
            return self.model
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            if not models:
                raise RuntimeError("Ollama has no models installed")
            self.model = models[0]["name"]
            logger.info("Auto-detected Ollama model: %s", self.model)
            return self.model

    async def analyze(self, content: str, prompt: str) -> str:
        model = await self._detect_model()
        full_prompt = f"{prompt}\n\n---\n{content}\n---"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code < 400
        except (httpx.HTTPError, Exception):
            return False
