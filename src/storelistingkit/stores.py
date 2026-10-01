"""Store specs (loaded from data/store_specs.json) and validation of copy and images against them."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path

from .models import ImageResult, Severity, StoreCopy, StoreId, ValidationIssue

TEXT_FIELDS = ("title", "short_description", "long_description")
LIST_FIELDS = ("features", "tags")


@lru_cache(maxsize=4)
def _load(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.loads(resources.files("storelistingkit").joinpath("data/store_specs.json").read_text("utf-8"))


def specs() -> dict:
    data = _load(os.environ.get("SLK_STORE_SPECS"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def spec(store: StoreId) -> dict:
    return specs()[store.value]


def field_limits(store: StoreId) -> dict[str, dict]:
    return spec(store)["fields"]


def image_slots(store: StoreId) -> dict[str, dict]:
    return spec(store)["images"]


def full_long_description(copy: StoreCopy) -> str:
    """What actually gets pasted into the store: model copy plus the deterministic technical section."""
    parts = [copy.long_description.strip()]
    if copy.technical_details.strip():
        parts.append(copy.technical_details.strip())
    return "\n\n".join(p for p in parts if p)


def validate_copy(copy: StoreCopy) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    limits = field_limits(copy.store)

    def add(field: str, sev: Severity, msg: str) -> None:
        issues.append(ValidationIssue(store=copy.store, field=field, severity=sev, message=msg))

    for field in TEXT_FIELDS:
        lim = limits.get(field, {})
        value = full_long_description(copy) if field == "long_description" else getattr(copy, field)
        n = len(value)
        if "max_chars" in lim and n > lim["max_chars"]:
            add(field, Severity.ERROR, f"{n}/{lim['max_chars']} characters, over the limit by {n - lim['max_chars']}.")
        if "min_chars" in lim and n < lim["min_chars"]:
            add(field, Severity.WARNING, f"Only {n} characters; at least {lim['min_chars']} recommended.")
    for field in LIST_FIELDS:
        lim = limits.get(field, {})
        items: list[str] = getattr(copy, field)
        if "max_items" in lim and len(items) > lim["max_items"]:
            add(field, Severity.ERROR, f"{len(items)} items; the maximum is {lim['max_items']}.")
        if not items:
            add(field, Severity.WARNING, "Empty.")
        for i, item in enumerate(items):
            if "max_chars" in lim and len(item) > lim["max_chars"]:
                add(field, Severity.ERROR, f"Item {i + 1} is {len(item)}/{lim['max_chars']} characters.")
    return issues


def validate_images(store: StoreId, images: list[ImageResult], screenshot_count: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for slot, s in image_slots(store).items():
        produced = [i for i in images if i.store == store and i.slot == slot]
        for img in produced:
            if (img.width, img.height) != (s["width"], s["height"]):
                issues.append(ValidationIssue(store=store, field=f"image:{slot}", severity=Severity.ERROR,
                                              message=f"{img.filename} is {img.width}x{img.height}, "
                                                      f"expected {s['width']}x{s['height']}."))
        if s.get("required") and not produced:
            msg = "Required image missing." if screenshot_count else "Required image missing: upload screenshots."
            issues.append(ValidationIssue(store=store, field=f"image:{slot}", severity=Severity.ERROR, message=msg))
        if len(produced) > s.get("max_count", 1):
            issues.append(ValidationIssue(store=store, field=f"image:{slot}", severity=Severity.ERROR,
                                          message=f"{len(produced)} images; maximum {s['max_count']}."))
    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.severity == Severity.ERROR for i in issues)
