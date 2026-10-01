"""Adapter registry and engine detection."""

from __future__ import annotations

from pathlib import Path

from ..models import Engine, PluginProfile
from .base import EngineAdapter
from .unity import UnityAdapter
from .unreal import UnrealAdapter

ADAPTERS: list[EngineAdapter] = [UnrealAdapter(), UnityAdapter()]


def adapter_for(engine: Engine) -> EngineAdapter:
    for a in ADAPTERS:
        if a.engine == engine:
            return a
    raise KeyError(engine)


def detect_engine(root: Path) -> tuple[Engine, float]:
    scored = sorted(((a.detect(root), a.engine) for a in ADAPTERS), reverse=True)
    score, engine = scored[0]
    return (engine, score) if score > 0 else (Engine.UNKNOWN, 0.0)


def extract_profile(root: Path) -> PluginProfile:
    engine, _ = detect_engine(root)
    if engine == Engine.UNKNOWN:
        return PluginProfile(
            warnings=["Could not detect an Unreal (.uplugin) or Unity (package.json/.asmdef) plugin."]
        )
    return adapter_for(engine).extract(root)


__all__ = ["ADAPTERS", "EngineAdapter", "UnityAdapter", "UnrealAdapter", "adapter_for", "detect_engine",
           "extract_profile"]
