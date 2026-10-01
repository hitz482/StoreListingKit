"""Settings from environment. HUMAN GATE: the API key path lives here (docs/REVIEW_NOTES.md)."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

DEFAULT_MODEL = "claude-opus-5-5"


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class Limits:
    max_upload_bytes: int = field(default_factory=lambda: _int("SLK_MAX_UPLOAD_MB", 100) * 1024 * 1024)
    max_unpacked_bytes: int = field(default_factory=lambda: _int("SLK_MAX_UNPACKED_MB", 500) * 1024 * 1024)
    max_files: int = field(default_factory=lambda: _int("SLK_MAX_FILES", 20_000))
    max_ratio: int = 200  # per-entry compression ratio above which we assume a zip bomb
    max_image_bytes: int = 20 * 1024 * 1024
    max_images: int = 20
    max_image_pixels: int = 40_000_000
    generate_per_minute: int = field(default_factory=lambda: _int("SLK_RATE_PER_MIN", 6))


class _KeyStore:
    """Holds the API key in memory only. Never logged, never persisted, never returned by the API."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session_key: str | None = None

    def set_session_key(self, key: str | None) -> None:
        with self._lock:
            self._session_key = (key or "").strip() or None

    def get(self) -> str | None:
        with self._lock:
            return self._session_key or os.environ.get("ANTHROPIC_API_KEY") or None

    def source(self) -> str:
        with self._lock:
            if self._session_key:
                return "session"
        return "env" if os.environ.get("ANTHROPIC_API_KEY") else "none"


KEYS = _KeyStore()
LIMITS = Limits()


def model() -> str:
    return os.environ.get("SLK_MODEL", DEFAULT_MODEL)


def max_attempts() -> int:
    return max(1, _int("SLK_MAX_ATTEMPTS", 3))
