"""Contract every EngineAdapter must satisfy (ARCHITECTURE: adapters/base.py). Written from the spec."""

import pytest

from storelistingkit.adapters import ADAPTERS, detect_engine
from storelistingkit.models import Engine, PluginProfile

ALL_FIXTURES = ["unreal_basic", "unity_basic", "unity_project_only", "empty_repo", "broken_uplugin"]


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda a: a.engine.value)
@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_detect_returns_confidence_and_never_raises(adapter, fixture, fixtures):
    score = adapter.detect(fixtures / fixture)
    assert 0.0 <= score <= 1.0


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda a: a.engine.value)
@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_extract_never_raises_and_returns_profile(adapter, fixture, fixtures):
    profile = adapter.extract(fixtures / fixture)
    assert isinstance(profile, PluginProfile)
    assert profile.engine == adapter.engine


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda a: a.engine.value)
@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_every_populated_field_has_a_source(adapter, fixture, fixtures):
    """extraction-guardrails rule 1: only emit values you can point to in a file."""
    profile = adapter.extract(fixtures / fixture)
    for name, value in profile.model_dump(exclude={"engine", "sources", "warnings"}).items():
        if value not in ("", [], None):
            assert name in profile.sources, f"{name} populated without a source"


@pytest.mark.parametrize("adapter", ADAPTERS, ids=lambda a: a.engine.value)
def test_empty_repo_yields_no_invented_facts(adapter, fixtures):
    """Guardrail 2: unknown is a valid answer; no default engine versions or platforms."""
    p = adapter.extract(fixtures / "empty_repo")
    assert p.engine_versions == [] and p.platforms == [] and p.modules == []


@pytest.mark.parametrize(
    ("fixture", "engine"),
    [("unreal_basic", Engine.UNREAL), ("unity_basic", Engine.UNITY),
     ("unity_project_only", Engine.UNITY), ("empty_repo", Engine.UNKNOWN)],
)
def test_detection_picks_the_right_engine(fixture, engine, fixtures):
    assert detect_engine(fixtures / fixture)[0] == engine


def test_detect_on_missing_dir_is_zero(tmp_path):
    for a in ADAPTERS:
        assert a.detect(tmp_path / "nope") == 0.0
