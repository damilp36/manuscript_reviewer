"""Local Ollama backend. The manuscript never leaves the machine."""

from __future__ import annotations

import os
from typing import Any

from .base import LLMClient


class OllamaClient(LLMClient):
    """Calls a local Ollama server over HTTP (default http://localhost:11434)."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.2,
        base_url: str | None = None,
        timeout_seconds: float = 600.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, temperature, **kwargs)
        self.base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def is_local(self) -> bool:
        return True

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        import httpx

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
            },
        }
        if json_mode:
            payload["format"] = "json"

        resp = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
