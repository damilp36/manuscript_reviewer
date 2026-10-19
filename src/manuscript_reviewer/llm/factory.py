"""Builds an LLMClient for a given role from configuration."""

from __future__ import annotations

from typing import Any, Dict

from ..config import AppConfig, RoleConfig
from .base import LLMClient


def build_client(role_cfg: RoleConfig, app_cfg: AppConfig) -> LLMClient:
    provider = role_cfg.provider.lower()
    provider_settings: Dict[str, Any] = app_cfg.providers.get(provider) or {}

    if provider == "ollama":
        from .ollama_client import OllamaClient

        import os

        base_url_env = provider_settings.get("base_url_env")
        base_url = os.environ.get(base_url_env) if base_url_env else None
        return OllamaClient(
            model=role_cfg.model,
            temperature=role_cfg.temperature,
            base_url=base_url,
            timeout_seconds=float(provider_settings.get("timeout_seconds", 600)),
        )

    if provider == "openai":
        from .openai_client import OpenAIClient

        return OpenAIClient(
            model=role_cfg.model,
            temperature=role_cfg.temperature,
            api_key_env=provider_settings.get("api_key_env", "OPENAI_API_KEY"),
        )

    if provider == "anthropic":
        from .anthropic_client import AnthropicClient

        return AnthropicClient(
            model=role_cfg.model,
            temperature=role_cfg.temperature,
            api_key_env=provider_settings.get("api_key_env", "ANTHROPIC_API_KEY"),
        )

    if provider == "mock":
        from .mock_client import MockClient

        return MockClient(model=role_cfg.model or "mock", temperature=role_cfg.temperature)

    raise ValueError(
        f"Unknown provider '{provider}'. "
        "Expected one of: ollama, openai, anthropic, mock."
    )
