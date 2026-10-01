"""EngineAdapter contract. Every adapter must pass tests/test_adapter_contract.py."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from ..models import Engine, PluginProfile
from ..untrusted import readme_excerpt

IGNORED_DIRS = {
    ".git", "Binaries", "Intermediate", "Saved", "DerivedDataCache", "Library", "Temp", "Logs",
    "obj", "node_modules", "__MACOSX", ".vs", ".idea",
}
MAX_TEXT_BYTES = 1_000_000


class EngineAdapter(ABC):
    engine: Engine

    @abstractmethod
    def detect(self, root: Path) -> float:
        """Return a confidence in [0, 1] that ``root`` holds a plugin for this engine. Must not raise."""

    @abstractmethod
    def extract(self, root: Path) -> PluginProfile:
        """Extract a profile. Must not raise on malformed files; record ``warnings`` instead.

        Every populated field must name its source file in ``profile.sources``.
        """


def walk(root: Path, max_depth: int = 8) -> Iterator[Path]:
    """Yield files under ``root``, skipping build output and VCS dirs, without following symlinks."""
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in IGNORED_DIRS and depth < max_depth:
                    stack.append((entry, depth + 1))
            elif entry.is_file():
                yield entry


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


_LINE_COMMENT = re.compile(r"^\s*//.*?$", re.MULTILINE)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def loads_lenient(text: str) -> dict:
    """Parse JSON tolerating a BOM, // and /* */ comments, and trailing commas (seen in real .uplugin files)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        cleaned = _BLOCK_COMMENT.sub("", _LINE_COMMENT.sub("", text.lstrip("﻿")))
        data = json.loads(_TRAILING_COMMA.sub(r"\1", cleaned))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON is not an object")
    return data


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def find_readme(root: Path, near: Path | None = None) -> Path | None:
    """Prefer a README next to the plugin descriptor, then the shallowest README in the tree."""
    candidates = []
    for p in walk(root, max_depth=4):
        if p.stem.lower() == "readme" and p.suffix.lower() in {".md", ".txt", ".rst", ""}:
            candidates.append(p)
    if not candidates:
        return None
    if near is not None:
        for c in candidates:
            if c.parent == near:
                return c
    return min(candidates, key=lambda p: (len(p.relative_to(root).parts), str(p)))


def apply_readme(root: Path, profile: PluginProfile, near: Path | None = None) -> None:
    readme = find_readme(root, near)
    if readme is None:
        return
    text = read_text(readme)
    if not text:
        return
    excerpt, flags = readme_excerpt(text)
    profile.readme_excerpt = excerpt
    profile.sources["readme_excerpt"] = rel(root, readme)
    if flags:
        profile.warnings.append(
            f"README contains text that looks like instructions to an AI ({', '.join(flags)}); "
            "it is treated as untrusted data."
        )
    if not profile.features:
        feats = readme_features(text)
        if feats:
            profile.features = feats
            profile.sources["features"] = rel(root, readme)
    if not profile.description:
        para = first_paragraph(text)
        if para:
            profile.description = para
            profile.sources["description"] = rel(root, readme)


_HEADING_FEATURES = re.compile(r"^#{1,4}\s*(key\s+)?features?\b.*$", re.IGNORECASE | re.MULTILINE)
_BULLET = re.compile(r"^\s{0,3}[-*+]\s+(.+?)\s*$")


def readme_features(text: str, limit: int = 12) -> list[str]:
    """Bullets under a 'Features' heading. Pure text extraction, no inference."""
    m = _HEADING_FEATURES.search(text)
    if not m:
        return []
    out: list[str] = []
    for line in text[m.end():].splitlines():
        if line.startswith("#"):
            break
        b = _BULLET.match(line)
        if b:
            item = re.sub(r"[*_`]|\[([^\]]*)\]\([^)]*\)", lambda mm: mm.group(1) or "", b.group(1)).strip()
            if 3 <= len(item) <= 200:
                out.append(item)
        if len(out) >= limit:
            break
    return out


def first_paragraph(text: str) -> str:
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b or b.startswith(("#", "!", "[", "<", "|", "```", "---", "===")):
            continue
        b = re.sub(r"\s+", " ", re.sub(r"[*_`]", "", b))
        if len(b) >= 20:
            return b[:500]
    return ""
