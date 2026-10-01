"""Handling of untrusted repo text (prompt-injection defence). HUMAN GATE: see docs/REVIEW_NOTES.md.

Strategy (defence in depth, none of which is relied on alone):
1. Bound the size: only a short excerpt of the README is ever sent to the model.
2. Detect likely injection phrases and surface them to the user as profile warnings.
3. Neutralise our own delimiter so content cannot close the untrusted block early.
4. Wrap in explicit tags; the system prompt says the tag content is data, never instructions.
5. Output-side: the generator's fact guard and schema validation reject anything off-contract,
   so even a successful injection cannot add facts or reach the UI as raw text.
"""

from __future__ import annotations

import re

MAX_EXCERPT_CHARS = 4000
TAG = "untrusted_repo_content"

_INJECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "ignore-instructions": re.compile(
        r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|all|earlier)\b.{0,40}"
        r"\b(instructions?|prompts?|rules?|directions?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "role-override": re.compile(r"\byou are now\b|\bact as\b.{0,30}\b(assistant|ai|model)\b", re.IGNORECASE),
    "system-prompt": re.compile(r"\bsystem\s*prompt\b|<\s*/?\s*system\s*>", re.IGNORECASE),
    "tool-exfiltration": re.compile(r"\b(api[_\s-]?key|secret|password|token)\b.{0,40}\b(print|reveal|send|output)\b",
                                    re.IGNORECASE | re.DOTALL),
}

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_OR_BADGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")


def detect_injection(text: str) -> list[str]:
    return [name for name, pat in _INJECTION_PATTERNS.items() if pat.search(text)]


def clean(text: str) -> str:
    """Strip hidden carriers (HTML comments, bidi/zero-width chars, badges) and collapse whitespace."""
    text = _HTML_COMMENT.sub("", text)
    text = _IMAGE_OR_BADGE.sub("", text)
    text = _CONTROL.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def readme_excerpt(text: str, limit: int = MAX_EXCERPT_CHARS) -> tuple[str, list[str]]:
    """Return a bounded, cleaned excerpt plus the injection flags found in the *full* text."""
    flags = detect_injection(text)
    hidden = " ".join(_HTML_COMMENT.findall(text))
    for f in detect_injection(hidden):
        if f not in flags:
            flags.append(f)
    cleaned = clean(text)
    if len(cleaned) > limit:
        cut = cleaned.rfind("\n", 0, limit)
        cleaned = cleaned[: cut if cut > limit // 2 else limit].rstrip() + "\n[…truncated]"
    return cleaned, flags


def wrap_untrusted(text: str, label: str = "readme") -> str:
    """Wrap repo-derived text for inclusion in a *user* message. Never use in a system prompt."""
    neutral = re.sub(rf"<\s*/?\s*{TAG}[^>]*>", "[removed-tag]", text, flags=re.IGNORECASE)
    return f'<{TAG} source="{label}">\n{neutral}\n</{TAG}>'
