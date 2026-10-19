"""OpenAI backend.

Note: using this backend sends the (redacted) manuscript to OpenAI's API.
Only enable it for manuscripts whose venue/policy permits cloud processing,
and prefer accounts with training/retention disabled.
"""

from __future__ import annotations

import os
from typing import Any

from .base import LLMClient


class OpenAIClient(LLMClient):
    def __init__(
        self,
        model: str,
        temperature: float = 0.2,
        api_key_env: str = "OPENAI_API_KEY",
        **kwargs: Any,
    ) -> None:
        super().__init__(model, temperature, **kwargs)
        self.api_key_env = api_key_env

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(
                "The OpenAI backend requires the 'openai' package. "
                "Install it with: pip install openai"
            ) from exc

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env} is not set; "
                "cannot use the OpenAI backend."
            )

        client = OpenAI(api_key=api_key)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature if temperature is None else temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
