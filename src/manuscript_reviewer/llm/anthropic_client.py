"""Anthropic (Claude) backend.

Note: using this backend sends the (redacted) manuscript to Anthropic's API.
Only enable it for manuscripts whose venue/policy permits cloud processing.
"""

from __future__ import annotations

import os
from typing import Any

from .base import LLMClient


class AnthropicClient(LLMClient):
    def __init__(
        self,
        model: str,
        temperature: float = 0.2,
        api_key_env: str = "ANTHROPIC_API_KEY",
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, temperature, **kwargs)
        self.api_key_env = api_key_env
        self.max_tokens = max_tokens

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(
                "The Anthropic backend requires the 'anthropic' package. "
                "Install it with: pip install anthropic"
            ) from exc

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env} is not set; "
                "cannot use the Anthropic backend."
            )

        # Claude has no JSON response-format flag; steer it via the system prompt.
        if json_mode:
            system = system + "\n\nRespond with a single valid JSON object and nothing else."

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature if temperature is None else temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
