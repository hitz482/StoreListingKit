"""F7: store-constraint validation. Limits are read from the spec file, never duplicated here."""

import json

from storelistingkit.images import compose
from storelistingkit.models import ImageResult, Severity, StoreCopy, StoreId
from storelistingkit.stores import field_limits, image_slots, specs, validate_copy, validate_images


def copy_for(store, **over):
    base = dict(store=store, title="Quick Outline", short_description="Fast outlines for any mesh in your project.",
                long_description="x" * 300, features=["Per-object colors"], tags=["outline"])
    base.update(over)
    return StoreCopy(**base)


def test_both_stores_have_specs():
    assert {"fab", "unity_asset_store"} <= set(specs())


def test_valid_copy_has_no_errors():
    for store in StoreId:
        assert not [i for i in validate_copy(copy_for(store)) if i.severity == Severity.ERROR]


def test_title_over_limit_is_error():
    for store in StoreId:
        lim = field_limits(store)["title"]["max_chars"]
        issues = validate_copy(copy_for(store, title="T" * (lim + 1)))
        assert any(i.field == "title" and i.severity == Severity.ERROR for i in issues)


def test_too_many_tags_is_error():
    store = StoreId.FAB
    n = field_limits(store)["tags"]["max_items"] + 1
    issues = validate_copy(copy_for(store, tags=[f"t{i}" for i in range(n)]))
    assert any(i.field == "tags" and i.severity == Severity.ERROR for i in issues)


def test_technical_details_count_toward_long_description():
    store = StoreId.FAB
    lim = field_limits(store)["long_description"]["max_chars"]
    issues = validate_copy(copy_for(store, long_description="x" * (lim - 10), technical_details="y" * 50))
    assert any(i.field == "long_description" for i in issues)


def test_missing_required_images_flagged():
    issues = validate_images(StoreId.UNITY_ASSET_STORE, [], 0)
    required = [k for k, v in image_slots(StoreId.UNITY_ASSET_STORE).items() if v["required"]]
    assert {i.field for i in issues} == {f"image:{k}" for k in required}


def test_wrong_image_size_flagged():
    bad = ImageResult(store=StoreId.FAB, slot="thumbnail", filename="t.png", width=100, height=100, source="s")
    issues = validate_images(StoreId.FAB, [bad], 1)
    assert any("expected" in i.message for i in issues)


def test_spec_override_via_env(tmp_path, monkeypatch):
    data = json.loads(json.dumps(specs()))
    data["fab"]["fields"]["title"]["max_chars"] = 5
    path = tmp_path / "specs.json"
    path.write_text(json.dumps(data))
    monkeypatch.setenv("SLK_STORE_SPECS", str(path))
    assert field_limits(StoreId.FAB)["title"]["max_chars"] == 5


def test_compose_hits_exact_size():
    from PIL import Image

    src = Image.new("RGB", (333, 777), (200, 10, 10))
    for store in StoreId:
        for slot in image_slots(store).values():
            out = compose(src, slot["width"], slot["height"], caption="Quick Outline" if slot.get("caption") else None)
            assert out.size == (slot["width"], slot["height"])
