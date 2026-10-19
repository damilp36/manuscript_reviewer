"""Provider-agnostic LLM layer.

Every agent talks to an ``LLMClient``. Swapping between local Ollama, OpenAI,
Anthropic, or the offline Mock backend is a config change, never a code change.
"""

from .base import LLMClient, LLMMessage, extract_json
from .factory import build_client

__all__ = ["LLMClient", "LLMMessage", "extract_json", "build_client"]
