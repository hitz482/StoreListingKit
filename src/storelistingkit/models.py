"""Pydantic schemas shared by every layer. This file is the contract (see docs/ARCHITECTURE.md)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Engine(StrEnum):
    UNREAL = "unreal"
    UNITY = "unity"
    UNKNOWN = "unknown"


class StoreId(StrEnum):
    FAB = "fab"
    UNITY_ASSET_STORE = "unity_asset_store"


ENGINE_STORES: dict[Engine, list[StoreId]] = {
    Engine.UNREAL: [StoreId.FAB],
    Engine.UNITY: [StoreId.UNITY_ASSET_STORE],
    Engine.UNKNOWN: [StoreId.FAB, StoreId.UNITY_ASSET_STORE],
}


class Module(BaseModel):
    """An Unreal module or a Unity assembly definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    kind: str = ""  # Unreal: Runtime/Editor/...; Unity: "runtime" or "editor"
    platforms: list[str] = Field(default_factory=list)


class PluginProfile(BaseModel):
    """Facts extracted from a repo. Every populated field must be traceable via ``sources``."""

    model_config = ConfigDict(extra="forbid")

    engine: Engine = Engine.UNKNOWN
    name: str = ""
    display_name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""
    category: str = ""
    engine_versions: list[str] = Field(default_factory=list)
    modules: list[Module] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    license: str = ""
    docs_url: str = ""
    support_url: str = ""
    readme_excerpt: str = ""
    sources: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    @property
    def title(self) -> str:
        return self.display_name or self.name

    def module_names(self) -> list[str]:
        return [m.name for m in self.modules]


class StoreCopyDraft(BaseModel):
    """What the model is asked to produce for one store. Kept small and flat for structured output."""

    title: str = Field(description="Product title for the store page.")
    short_description: str = Field(description="One or two sentence summary shown on store cards.")
    long_description: str = Field(
        description="Full description in plain text with blank-line separated paragraphs. "
        "No technical-details section; that is added automatically from the profile."
    )
    features: list[str] = Field(description="Feature bullets, each one concrete and factual.")
    tags: list[str] = Field(description="Search tags or keywords, lowercase, no '#'.")


class StoreCopy(StoreCopyDraft):
    """Validated copy for one store plus deterministic sections rendered from the profile."""

    store: StoreId
    technical_details: str = ""
    generated_by: str = "template"  # "claude:<model>" or "template"

    @field_validator("tags")
    @classmethod
    def _normalise_tags(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for t in v:
            t = t.strip().lstrip("#").lower()
            if t and t not in seen:
                seen.append(t)
        return seen


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    store: StoreId
    field: str
    severity: Severity
    message: str


class ImageResult(BaseModel):
    store: StoreId
    slot: str
    filename: str
    width: int
    height: int
    source: str


class ListingKit(BaseModel):
    profile: PluginProfile
    copies: dict[StoreId, StoreCopy] = Field(default_factory=dict)
    images: list[ImageResult] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
