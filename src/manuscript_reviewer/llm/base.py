"""The abstract LLM interface plus a robust JSON extractor."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(ABC):
    """Minimal chat interface implemented by every backend."""

    def __init__(self, model: str, temperature: float = 0.2, **kwargs: Any) -> None:
        self.model = model
        self.temperature = temperature
        self.options = kwargs

    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        """Return the assistant's text response for a single-turn prompt."""

    @property
    def is_local(self) -> bool:
        return False


def extract_json(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response.

    Handles fenced code blocks and leading/trailing prose that models often add
    even when asked for pure JSON.
    """
    if not text:
        raise ValueError("Empty response; no JSON to parse.")

    # 1. Try the whole thing.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try a fenced ```json ... ``` block.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Fall back to the first balanced {...} span.
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not parse JSON from response:\n{text[:500]}")
