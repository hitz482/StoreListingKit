"""Mocked-model integration tests for ClaudeGenerator (no network, runs in CI). F5, F6."""

from types import SimpleNamespace

import pytest

from storelistingkit.adapters import extract_profile
from storelistingkit.generator import (
    ClaudeGenerator,
    GenerationError,
    TemplateGenerator,
    fact_guard,
    render_technical_details,
)
from storelistingkit.models import StoreCopyDraft, StoreId
from storelistingkit.stores import field_limits, validate_copy


class FakeMessages:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        if isinstance(out, SimpleNamespace):
            return out
        return SimpleNamespace(stop_reason="end_turn", parsed_output=out)


class FakeClient:
    def __init__(self, outputs):
        self.beta = SimpleNamespace(messages=FakeMessages(outputs))


def good_draft(**over):
    d = dict(title="Quick Outline", short_description="Per-object outlines and highlights for Unreal projects.",
             long_description="Quick Outline draws crisp outlines around selected objects.\n\n" + "Details. " * 30,
             features=["Per-object outline color and width", "X-ray view behind walls"],
             tags=["outline", "highlight", "rendering"])
    d.update(over)
    return StoreCopyDraft(**d)


@pytest.fixture
def profile(fixtures):
    return extract_profile(fixtures / "unreal_basic")


def test_valid_output_first_try(profile):
    client = FakeClient([good_draft()])
    copy = ClaudeGenerator(client=client, model="m", max_attempts=3).generate(profile, StoreId.FAB)
    assert copy.generated_by == "claude:m" and copy.store == StoreId.FAB
    assert "QuickOutlineEditor" in copy.technical_details
    assert len(client.beta.messages.calls) == 1


def test_request_shape(profile):
    client = FakeClient([good_draft()])
    ClaudeGenerator(client=client, model="claude-opus-5-5").generate(profile, StoreId.FAB)
    call = client.beta.messages.calls[0]
    assert call["output_format"] is StoreCopyDraft
    assert call["fallbacks"] == "default"
    user = call["messages"][0]["content"]
    assert "<untrusted_repo_content" in user and "<plugin_profile>" in user
    assert "untrusted_repo_content" in call["system"]  # system explains, but carries no repo text
    assert "Quick Outline adds fast" not in call["system"]


def test_retries_with_feedback_then_succeeds(profile):
    over = good_draft(title="T" * 200)
    client = FakeClient([over, good_draft()])
    copy = ClaudeGenerator(client=client, model="m", max_attempts=3).generate(profile, StoreId.FAB)
    assert copy.title == "Quick Outline"
    second = client.beta.messages.calls[1]["messages"][0]["content"]
    assert "rejected by the validator" in second and "title" in second


def test_schema_invalid_output_retries(profile):
    client = FakeClient([SimpleNamespace(stop_reason="end_turn", parsed_output=None), good_draft()])
    copy = ClaudeGenerator(client=client, model="m", max_attempts=2).generate(profile, StoreId.FAB)
    assert copy.title


def test_hard_failure_after_max_attempts(profile):
    bad = good_draft(long_description="Supports PS5 and Nintendo Switch. " * 10)
    client = FakeClient([bad, bad, bad])
    with pytest.raises(GenerationError) as exc:
        ClaudeGenerator(client=client, model="m", max_attempts=3).generate(profile, StoreId.FAB)
    assert any("PS5" in p or "ps5" in p for p in exc.value.problems)
    assert len(client.beta.messages.calls) == 3


def test_refusal_is_hard_failure(profile):
    client = FakeClient([SimpleNamespace(stop_reason="refusal", parsed_output=None)])
    with pytest.raises(GenerationError, match="declined"):
        ClaudeGenerator(client=client, model="m").generate(profile, StoreId.FAB)


def test_api_errors_become_clean_generation_errors(profile):
    import anthropic
    import httpx

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None)
    with pytest.raises(GenerationError, match="rejected"):
        ClaudeGenerator(client=FakeClient([err]), model="m").generate(profile, StoreId.FAB)


def test_fact_guard_catches_invented_facts(profile):
    d = good_draft(long_description="Built on the FancyRender module for UE 5.1 on Android.")
    problems = " ".join(fact_guard(d, profile))
    assert "FancyRender" in problems and "5.1" in problems and "android" in problems


def test_fact_guard_allows_profile_facts(profile):
    d = good_draft(long_description="Uses the QuickOutline module on Windows, Mac and Linux with UE 5.4.")
    assert fact_guard(d, profile) == []


def test_fact_guard_ignores_plain_word_switch(profile):
    d = good_draft(long_description="Switch outline styles at runtime.")
    assert fact_guard(d, profile) == []


def test_technical_details_rendered_only_from_profile(profile):
    text = render_technical_details(profile, StoreId.FAB)
    assert "5.4" in text and "QuickOutline (Runtime)" in text and "Win64" in text


@pytest.mark.parametrize("store", list(StoreId))
def test_template_generator_is_within_limits(profile, store):
    copy = TemplateGenerator().generate(profile, store)
    assert copy.generated_by == "template"
    assert len(copy.title) <= field_limits(store)["title"]["max_chars"]
    assert not [i for i in validate_copy(copy) if i.severity.value == "error"]


def test_template_on_empty_profile_does_not_crash():
    from storelistingkit.models import PluginProfile

    copy = TemplateGenerator().generate(PluginProfile(), StoreId.FAB)
    assert copy.title == "Untitled plugin"


def test_no_key_raises_clean_error(profile):
    with pytest.raises(GenerationError, match="No Anthropic API key"):
        ClaudeGenerator(model="m").generate(profile, StoreId.FAB)
