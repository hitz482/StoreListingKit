"""Deterministic extraction compared against golden files (tests/fixtures/golden/*.json)."""

import json

import pytest

from storelistingkit.adapters import extract_profile

CASES = ["unreal_basic", "unity_basic", "unity_project_only", "broken_uplugin"]


@pytest.mark.parametrize("case", CASES)
def test_golden(case, fixtures, update_golden):
    golden = fixtures / "golden" / f"{case}.json"
    actual = json.loads(extract_profile(fixtures / case).model_dump_json())
    if update_golden or not golden.exists():
        golden.parent.mkdir(exist_ok=True)
        golden.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not update_golden:
            pytest.fail(f"golden file {golden.name} was missing; created it. Review and commit it.")
    assert actual == json.loads(golden.read_text(encoding="utf-8"))


def test_unreal_ignores_binaries_and_misnamed_build_files(fixtures):
    p = extract_profile(fixtures / "unreal_basic")
    assert p.module_names() == ["QuickOutline", "QuickOutlineEditor"]
    assert "SomethingElse" not in p.module_names()
    assert p.sources["name"] == "QuickOutline/QuickOutline.uplugin"


def test_unreal_tolerates_comments_and_trailing_commas(fixtures):
    p = extract_profile(fixtures / "unreal_basic")
    assert p.display_name == "Quick Outline" and p.engine_versions == ["5.4"]
    assert p.platforms == ["Win64", "Mac", "Linux"]


def test_unity_skips_library_cache_and_test_assemblies(fixtures):
    p = extract_profile(fixtures / "unity_basic")
    assert p.name == "com.example.tweenkit"
    assert p.module_names() == ["Example.TweenKit", "Example.TweenKit.Editor"]
    assert p.engine_versions == ["2022.3"]


def test_unity_project_version_fallback(fixtures):
    p = extract_profile(fixtures / "unity_project_only")
    assert p.engine_versions == ["6000.0"]
    assert p.name == ""  # guardrail 3: never derive a name from a folder


def test_broken_descriptor_becomes_warning(fixtures):
    p = extract_profile(fixtures / "broken_uplugin")
    assert any("could not parse" in w for w in p.warnings)


def test_readme_injection_is_flagged(fixtures):
    p = extract_profile(fixtures / "unreal_basic")
    assert any("untrusted" in w for w in p.warnings)
    assert "ignore all previous" not in p.readme_excerpt.lower()  # hidden HTML comment stripped


def _write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_unreal_platforms_empty_when_a_runtime_module_is_unrestricted(tmp_path):
    """AI_LOG #10: union of editor-only allow-lists must not be reported as plugin platforms."""
    _write(tmp_path, "P/P.uplugin", '{"Modules": [{"Name": "P", "Type": "Runtime"},'
           '{"Name": "PEd", "Type": "UncookedOnly", "PlatformAllowList": ["Win64"]},'
           '{"Name": "PTests", "Type": "Runtime", "PlatformAllowList": ["Win64"]}]}')
    p = extract_profile(tmp_path)
    assert p.platforms == []
    assert p.module_names() == ["P", "PEd"]


def test_unity_ignores_tilde_folders(tmp_path):
    _write(tmp_path, "package.json", '{"name": "com.a.b", "unity": "2021.3"}')
    _write(tmp_path, "Runtime/A.asmdef", '{"name": "A"}')
    _write(tmp_path, "Samples~/Demo/A.Demo.asmdef", '{"name": "A.Demo"}')
    assert extract_profile(tmp_path).module_names() == ["A"]
