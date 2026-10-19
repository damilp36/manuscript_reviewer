"""Loading and validating the YAML configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

# Repo-root-relative default locations.
_PKG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _PKG_DIR.parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_RUBRICS_DIR = PROJECT_ROOT / "config" / "rubrics"

LOCAL_PROVIDERS = {"ollama", "mock"}


@dataclass
class RoleConfig:
    provider: str
    model: str = ""
    temperature: float = 0.2


@dataclass
class AppConfig:
    raw: Dict[str, Any]
    roles: Dict[str, RoleConfig] = field(default_factory=dict)
    providers: Dict[str, Any] = field(default_factory=dict)
    redact_author_identity: bool = True
    local_only: bool = False
    num_reviewers: int = 2
    default_rubric: str = "default"
    rubrics_dir: Path = DEFAULT_RUBRICS_DIR

    def role(self, name: str) -> RoleConfig:
        if name not in self.roles:
            raise KeyError(f"No configuration for role '{name}'")
        return self.roles[name]

    def assert_privacy(self) -> None:
        """Enforce local_only by refusing non-local providers for any role."""
        if not self.local_only:
            return
        offenders = [
            f"{name} -> {rc.provider}"
            for name, rc in self.roles.items()
            if rc.provider not in LOCAL_PROVIDERS
        ]
        if offenders:
            raise ValueError(
                "privacy.local_only is enabled but these roles use non-local "
                f"providers: {', '.join(offenders)}. The manuscript would leave "
                "this machine. Switch them to ollama/mock or disable local_only."
            )


def load_config(path: str | os.PathLike | None = None) -> AppConfig:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    roles: Dict[str, RoleConfig] = {}
    for name, spec in (raw.get("roles") or {}).items():
        spec = spec or {}
        roles[name] = RoleConfig(
            provider=spec.get("provider", "ollama"),
            model=spec.get("model", ""),
            temperature=float(spec.get("temperature", 0.2)),
        )

    privacy = raw.get("privacy") or {}
    review = raw.get("review") or {}

    cfg = AppConfig(
        raw=raw,
        roles=roles,
        providers=raw.get("providers") or {},
        redact_author_identity=bool(privacy.get("redact_author_identity", True)),
        local_only=bool(privacy.get("local_only", False)),
        num_reviewers=int(review.get("num_reviewers", 2)),
        default_rubric=str(review.get("default_rubric", "default")),
    )
    cfg.assert_privacy()
    return cfg
