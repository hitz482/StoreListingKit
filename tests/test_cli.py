import json

from storelistingkit.cli import main


def test_selftest(capsys):
    assert main(["selftest"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["engine"] == "unreal" and out["files"] >= 5
    assert out["errors"] == []


def test_extract_folder(capsys, fixtures):
    assert main(["extract", str(fixtures / "unity_basic")]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == "com.example.tweenkit"
